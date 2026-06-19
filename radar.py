#!/usr/bin/env python3
"""gh-radar — a daily digest of GitHub tools that are trending or being shared.

Stable, free sources only. No X/Twitter API, no logged-in scraping, no paid keys:
  1. GitHub Trending (HTML)     -> star velocity: "what's hot today"
  2. Hacker News (Algolia API)  -> what developers are actually discussing
  3. GitHub Search API          -> brand-new repos already gaining stars

It dedupes across sources, scores each repo, remembers what it already sent
(so you don't see the same repo every day), renders a Markdown digest, and
emails it via SMTP. Standard library only.

Config via environment (see config.example.env):
  GITHUB_TOKEN   optional, raises API rate limit 60/hr -> 5000/hr
  SMTP_HOST      e.g. smtp.gmail.com
  SMTP_PORT      e.g. 587
  SMTP_USER      your gmail address
  SMTP_PASS      a Gmail App Password (NOT your login password)
  EMAIL_TO       where to send the digest (defaults to SMTP_USER)
  MIN_STARS      ignore repos below this many total stars (default 30)
  SEEN_TTL_DAYS  don't re-show a repo seen within this many days (default 14)
"""

import json
import os
import re
import shutil
import smtplib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from html import escape as html_escape, unescape
from pathlib import Path

UA = "gh-radar/1.0 (+https://github.com/)"
STATE_DIR = Path(os.environ.get("GH_RADAR_HOME", Path.home() / ".gh-radar"))
SEEN_PATH = STATE_DIR / "seen.json"
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
MIN_STARS = int(os.environ.get("MIN_STARS", "30"))
SEEN_TTL_DAYS = int(os.environ.get("SEEN_TTL_DAYS", "14"))

# Repos that are not really "tools you'd install" — owners/names we skip.
SKIP_NAME_RE = re.compile(
    r"(awesome-|/awesome$|interview|roadmap|tutorial|free-?programming|"
    r"build-your-own|coding-interview|system-design|the-book|-book$|cheatsheet)",
    re.I,
)


# ----------------------------------------------------------------------------- http
def http_get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def gh_api(path):
    """Call api.github.com with token if available. Returns parsed JSON or None."""
    headers = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    try:
        return json.loads(http_get(f"https://api.github.com{path}", headers))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("  ! github api rate-limited (set GITHUB_TOKEN to fix)", file=sys.stderr)
        else:
            print(f"  ! github api {e.code} on {path}", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001
        print(f"  ! github api error on {path}: {e}", file=sys.stderr)
        return None


# --------------------------------------------------------------------------- sources
def src_github_trending():
    """Scrape github.com/trending. Returns {full_name: {stars_today, desc, stars}}."""
    out = {}
    try:
        html = http_get("https://github.com/trending")
    except Exception as e:  # noqa: BLE001
        print(f"  ! trending fetch failed: {e}", file=sys.stderr)
        return out
    for block in html.split('<article class="Box-row">')[1:]:
        m = re.search(r'href="/([^"/]+)/([^"/]+)/stargazers"', block)
        if not m:
            continue
        full = f"{m.group(1)}/{m.group(2)}"
        desc = ""
        dm = re.search(r'<p class="col-9[^"]*">(.*?)</p>', block, re.S)
        if dm:
            desc = unescape(re.sub(r"<[^>]+>", "", dm.group(1))).strip()
        stars = 0
        sm = re.search(r'/stargazers"[^>]*>\s*([\d,]+)', block)
        if sm:
            stars = int(sm.group(1).replace(",", ""))
        today = 0
        tm = re.search(r"([\d,]+)\s+stars today", block)
        if tm:
            today = int(tm.group(1).replace(",", ""))
        out[full] = {"stars_today": today, "desc": desc, "stars": stars}
    return out


def src_hacker_news():
    """Github repos mentioned on HN in the last 24h. {full_name: {hn_points, hn_url}}."""
    out = {}
    since = int(time.time()) - 86400
    url = (
        "https://hn.algolia.com/api/v1/search_by_date?query=github.com&tags=story"
        f"&numericFilters=created_at_i>{since}&hitsPerPage=100"
    )
    try:
        data = json.loads(http_get(url))
    except Exception as e:  # noqa: BLE001
        print(f"  ! hacker news fetch failed: {e}", file=sys.stderr)
        return out
    for h in data.get("hits", []):
        link = h.get("url") or ""
        if "gist.github.com" in link:        # gists are not repos
            continue
        m = re.search(r"(?<!gist\.)github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", link)
        if not m:
            continue
        owner, repo = m.group(1), m.group(2).removesuffix(".git")
        if owner in ("features", "about", "topics", "marketplace", "sponsors"):
            continue
        full = f"{owner}/{repo}"
        points = h.get("points") or 0
        hn_url = f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        if full not in out or points > out[full]["hn_points"]:
            out[full] = {"hn_points": points, "hn_url": hn_url}
    return out


def src_github_new():
    """Brand-new repos (created <=10 days ago) already gaining stars."""
    out = {}
    cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # created in the last 10 days; pushed recently; popular relative to age
    since = (datetime.now(timezone.utc).timestamp()) - 10 * 86400
    since_d = datetime.fromtimestamp(since, timezone.utc).strftime("%Y-%m-%d")
    q = f"created:>={since_d}+stars:>={max(MIN_STARS, 50)}"
    data = gh_api(f"/search/repositories?q={q}&sort=stars&order=desc&per_page=30")
    if not data:
        return out
    for it in data.get("items", []):
        out[it["full_name"]] = {"new_repo": True, "created": it.get("created_at", cutoff)}
    return out


# ------------------------------------------------------------------------- enrich/score
def enrich(full, agg):
    """Fill missing description/stars/topics from the repo API. Mutates agg in place."""
    if agg.get("stars") and agg.get("desc"):
        return True
    info = gh_api(f"/repos/{full}")
    if not info or info.get("archived") or info.get("fork"):
        return False
    agg["stars"] = info.get("stargazers_count", agg.get("stars", 0))
    agg["desc"] = (info.get("description") or agg.get("desc") or "").strip()
    agg["lang"] = info.get("language") or ""
    agg["url"] = info.get("html_url") or f"https://github.com/{full}"
    return True


def summarize_zh(repos):
    """Best-effort: add a Traditional-Chinese one-liner to each repo via the
    `claude` CLI (local login, or CI with CLAUDE_CODE_OAUTH_TOKEN). One batched
    call for all repos. Silently falls back to English-only if claude is absent."""
    cli = shutil.which("claude")
    if not cli:
        print("  i no claude CLI — skipping Chinese summaries", file=sys.stderr)
        return
    items = [{"name": r["full_name"], "en": r.get("desc", "")} for r in repos]
    prompt = (
        "Below is a JSON array of GitHub repos. For EACH repo write a concise "
        "Traditional Chinese (繁體中文，台灣用語) description of what the tool DOES — "
        "its function in practice, not marketing fluff. Keep each to 15–40 字. "
        "Return ONLY a JSON object mapping each exact `name` to its Chinese string. "
        "No markdown fences, no commentary.\n\nRepos:\n"
        + json.dumps(items, ensure_ascii=False)
    )
    try:
        proc = subprocess.run(
            [cli, "-p", "--output-format", "json", "--model", "sonnet"],
            input=prompt, capture_output=True, text=True, timeout=240,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"claude exited {proc.returncode}: {proc.stderr.strip()[:200]}")
        text = json.loads(proc.stdout).get("result", "") or ""
        m = re.search(r"\{.*\}", text, re.S)   # tolerate preamble / ```json fences
        if not m:
            raise ValueError("no JSON object in model output")
        mapping = json.loads(m.group(0))
        if not isinstance(mapping, dict):
            raise ValueError(f"expected JSON object, got {type(mapping).__name__}")
    except Exception as e:  # noqa: BLE001
        print(f"  ! Chinese summary failed ({e}); using English only", file=sys.stderr)
        return
    n = 0
    for r in repos:
        zh = mapping.get(r["full_name"])
        if isinstance(zh, str) and zh.strip():
            zh = " ".join(zh.split())          # collapse stray newlines/whitespace
            r["zh"] = zh[:120]                  # defensive cap; model is asked for ~40
            n += 1
    print(f"  ✓ Chinese summaries: {n}/{len(repos)}", file=sys.stderr)


def score(agg):
    s = 0.0
    s += agg.get("stars_today", 0) * 1.0
    s += agg.get("hn_points", 0) * 2.0          # HN discussion weighted higher
    s += 40 if agg.get("new_repo") else 0       # novelty bonus
    s += min(agg.get("stars", 0), 5000) * 0.01  # mild popularity tiebreak
    s += 15 * len(agg.get("sources", []))       # multi-source = stronger signal
    return s


# ------------------------------------------------------------------------------ state
def load_seen():
    try:
        data = json.loads(SEEN_PATH.read_text())
        if not isinstance(data, dict):
            return {}
        # keep only numeric timestamps — tolerate a hand-edited/corrupt file
        return {k: v for k, v in data.items() if isinstance(v, (int, float))}
    except Exception:  # noqa: BLE001
        return {}


def save_seen(seen):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - SEEN_TTL_DAYS * 86400
    seen = {k: v for k, v in seen.items() if isinstance(v, (int, float)) and v > cutoff}
    tmp = SEEN_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(seen))
    tmp.replace(SEEN_PATH)        # atomic — never leaves a half-written file


# ----------------------------------------------------------------------------- render
def render_md(repos, when):
    lines = [f"# GitHub Radar — {when}", ""]
    lines.append(f"_{len(repos)} new tools surfaced from GitHub Trending, Hacker News, and new-repo search._")
    lines.append("")
    for i, r in enumerate(repos, 1):
        tags = []
        if "trending" in r["sources"]:
            tags.append(f"🔥 {r.get('stars_today', 0)}/day")
        if "hn" in r["sources"]:
            tags.append(f"💬 HN {r.get('hn_points', 0)}")
        if "new" in r["sources"]:
            tags.append("🆕 new")
        meta = " · ".join(tags)
        star = f"⭐ {r.get('stars', 0):,}"
        lang = f" · {r['lang']}" if r.get("lang") else ""
        lines.append(f"### {i}. [{r['full_name']}]({r['url']})")
        lines.append(f"{star} · {meta}{lang}")
        if r.get("zh"):
            lines.append("")
            lines.append(f"> {r['zh']}")
            if r.get("desc"):
                lines.append(f"> _{r['desc']}_")
        elif r.get("desc"):
            lines.append("")
            lines.append(f"> {r['desc']}")
        if r.get("hn_url"):
            lines.append("")
            lines.append(f"[HN discussion]({r['hn_url']})")
        lines.append("")
    return "\n".join(lines)


def _inline(s):
    """HTML-escape text, THEN convert our markdown links/italics. Escaping first
    means a repo description containing <, >, & or quotes can't break the email."""
    s = html_escape(s, quote=True)
    s = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"_(.+?)_", r"<em>\1</em>", s)
    return s


def md_to_html(md):
    """Minimal Markdown -> HTML good enough for email clients."""
    html = []
    for line in md.split("\n"):
        if line.startswith("### "):
            html.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("# "):
            html.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("> "):
            html.append(
                f"<blockquote style='margin:4px 0;padding-left:10px;"
                f"border-left:3px solid #ddd;color:#333'>{_inline(line[2:])}</blockquote>"
            )
        elif line.strip() == "":
            html.append("<br>")
        else:
            html.append(f"<p style='margin:2px 0'>{_inline(line)}</p>")
    return (
        "<div style=\"font-family:-apple-system,Segoe UI,Roboto,sans-serif;"
        "max-width:680px;margin:auto;line-height:1.45\">" + "\n".join(html) + "</div>"
    )


def send_email(subject, md):
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    to = os.environ.get("EMAIL_TO", user)
    if not (host and user and pw and to):
        print("  i SMTP not configured — printing digest instead.\n", file=sys.stderr)
        print(md)
        return False
    msg = MIMEText(md_to_html(md), "html", "utf-8")
    msg["Subject"] = str(Header(subject, "utf-8"))     # safe for em dash / Chinese
    msg["From"] = formataddr(("GitHub Radar", user))
    msg["To"] = to
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        port = 587
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.ehlo()
        s.starttls()
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())
    print(f"  ✓ emailed digest to {to}")
    return True


# ------------------------------------------------------------------------------- main
def main():
    print("gh-radar: collecting…", file=sys.stderr)
    trending = src_github_trending()
    print(f"  trending: {len(trending)} repos", file=sys.stderr)
    hn = src_hacker_news()
    print(f"  hacker news: {len(hn)} repos", file=sys.stderr)
    new = src_github_new()
    print(f"  new repos: {len(new)} repos", file=sys.stderr)

    # Merge all sources keyed by full_name.
    agg = {}
    for full, d in trending.items():
        agg.setdefault(full, {"sources": []})["sources"].append("trending")
        agg[full].update(d)
    for full, d in hn.items():
        agg.setdefault(full, {"sources": []})["sources"].append("hn")
        agg[full].update(d)
    for full, d in new.items():
        agg.setdefault(full, {"sources": []})["sources"].append("new")
        agg[full].update(d)

    seen = load_seen()
    now = time.time()
    cutoff = now - SEEN_TTL_DAYS * 86400

    candidates = []
    for full, a in agg.items():
        if SKIP_NAME_RE.search(full):
            continue
        if seen.get(full, 0) > cutoff:        # already shown recently
            continue
        if not enrich(full, a):               # dead/fork/archived -> drop
            continue
        if a.get("stars", 0) < MIN_STARS:
            continue
        a["full_name"] = full
        a["url"] = a.get("url") or f"https://github.com/{full}"
        a["_score"] = score(a)
        candidates.append(a)

    candidates.sort(key=lambda x: x["_score"], reverse=True)
    top = candidates[:20]

    if not top:
        print("  nothing new today.", file=sys.stderr)
        return

    summarize_zh(top)            # add Traditional-Chinese one-liners (best-effort)

    when = datetime.now().strftime("%Y-%m-%d")
    md = render_md(top, when)

    # Optional: also save a copy as a Markdown file (Obsidian vault, or the
    # repo's digests/ dir in CI so you get a browsable history from your phone).
    out_dir = os.environ.get("GH_RADAR_DIGEST_DIR") or os.environ.get("GH_RADAR_VAULT")
    if out_dir:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"github-radar-{when}.md"
        p.write_text(md)
        print(f"  ✓ wrote {p}", file=sys.stderr)

    send_email(f"GitHub Radar — {when} ({len(top)} tools)", md)

    for r in top:
        seen[r["full_name"]] = now
    save_seen(seen)


if __name__ == "__main__":
    main()
