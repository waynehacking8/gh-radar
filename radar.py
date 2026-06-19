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
import urllib.parse
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

# github.com paths that are not user/repo (avoid treating /features/x as a repo).
SKIP_OWNERS = {
    "features", "about", "topics", "marketplace", "sponsors", "orgs", "blog",
    "collections", "login", "join", "settings", "notifications", "search",
    "pulls", "issues", "explore", "trending", "apps", "customer-stories",
    "readme", "site", "enterprise", "pricing", "security", "contact",
}
SKIP_REPO_SECONDS = {
    "blob", "tree", "releases", "issues", "pull", "pulls", "wiki", "actions",
    "commits", "compare", "tags", "branches", "discussions",
}

GITHUB_RE = re.compile(r"(?<!gist\.)github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


def repos_in(text):
    """Yield clean 'owner/repo' full names found anywhere in a blob of text."""
    seen = set()
    for owner, repo in GITHUB_RE.findall(text or ""):
        repo = repo.removesuffix(".git")
        if owner.lower() in SKIP_OWNERS or repo.lower() in SKIP_REPO_SECONDS:
            continue
        full = f"{owner}/{repo}"
        if full not in seen:
            seen.add(full)
            yield full


def _split_env(name, default):
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


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
# Trending pages to scrape: global daily + global weekly + a few languages.
# Weekly catches tools that stay hot all week (not just a one-day spike).
TREND_LANGS = _split_env("GH_RADAR_TREND_LANGS", "python,rust,go,typescript,c++,javascript")


def _parse_trending(html, out):
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
        velocity = 0
        # "N stars today" (daily) or "N stars this week" (weekly view)
        tm = re.search(r"([\d,]+)\s+stars (?:today|this week|this month)", block)
        if tm:
            velocity = int(tm.group(1).replace(",", ""))
        prev = out.get(full, {})
        out[full] = {
            "stars_today": max(velocity, prev.get("stars_today", 0)),
            "desc": prev.get("desc") or desc,
            "stars": max(stars, prev.get("stars", 0)),
        }


def src_github_trending():
    """Scrape github.com/trending across windows + languages -> {full_name: {...}}."""
    out = {}
    pages = [
        "https://github.com/trending?since=daily",
        "https://github.com/trending?since=weekly",
    ]
    pages += [f"https://github.com/trending/{lang}?since=daily" for lang in TREND_LANGS]
    for url in pages:
        try:
            _parse_trending(http_get(url), out)
        except Exception as e:  # noqa: BLE001
            print(f"  ! trending fetch failed ({url}): {e}", file=sys.stderr)
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
        points = h.get("points") or 0
        hn_url = f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        for full in repos_in(link):
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


def src_lobsters():
    """Github repos linked from the Lobsters hottest feed. {full_name: {lobsters_*}}."""
    out = {}
    try:
        data = json.loads(http_get("https://lobste.rs/hottest.json"))
    except Exception as e:  # noqa: BLE001
        print(f"  ! lobsters fetch failed: {e}", file=sys.stderr)
        return out
    for s in data:
        link = s.get("url") or ""
        c_url = s.get("comments_url") or s.get("short_id_url") or link
        pts = s.get("score") or 0
        for full in repos_in(link):
            if full not in out or pts > out[full]["lobsters_score"]:
                out[full] = {"lobsters_score": pts, "lobsters_url": c_url}
    return out


def src_reddit():
    """Github repos surfaced in tool-discovery subreddits. Optional: needs a Reddit
    app (REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET) since anonymous JSON is now blocked.
    Returns {full_name: {reddit_points, reddit_url, reddit_sub}}; {} if not configured."""
    cid = os.environ.get("REDDIT_CLIENT_ID")
    secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        print("  i reddit disabled (set REDDIT_CLIENT_ID/SECRET to enable)", file=sys.stderr)
        return {}
    subs = _split_env(
        "GH_RADAR_SUBREDDITS",
        "commandline,selfhosted,opensource,coolgithubprojects,golang,rust,programming",
    )
    out = {}
    try:  # app-only OAuth (client_credentials)
        import base64
        auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
        body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
        req = urllib.request.Request(
            "https://www.reddit.com/api/v1/access_token", data=body,
            headers={"Authorization": f"Basic {auth}", "User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            token = json.loads(r.read().decode())["access_token"]
    except Exception as e:  # noqa: BLE001
        print(f"  ! reddit auth failed: {e}", file=sys.stderr)
        return out
    for sub in subs:
        try:
            url = f"https://oauth.reddit.com/r/{sub}/top?t=day&limit=25"
            data = json.loads(http_get(
                url, headers={"Authorization": f"Bearer {token}"}))
        except Exception as e:  # noqa: BLE001
            print(f"  ! reddit r/{sub} failed: {e}", file=sys.stderr)
            continue
        for child in data.get("data", {}).get("children", []):
            p = child.get("data", {})
            pts = p.get("ups") or p.get("score") or 0
            permalink = "https://reddit.com" + p.get("permalink", "")
            blob = f"{p.get('url','')} {p.get('selftext','')} {p.get('title','')}"
            for full in repos_in(blob):
                if full not in out or pts > out[full]["reddit_points"]:
                    out[full] = {"reddit_points": pts, "reddit_url": permalink,
                                 "reddit_sub": sub}
    return out


X_API = "https://api.twitterapi.io/twitter/user/last_tweets"
X_TOOL_RE = re.compile(r"github|开源|開源|\bstar\b|⭐|repo|工具|神器|项目", re.I)


def _x_tweets(user, key, pages):
    """Recent tweets for one user, paginated to widen the window. [] on error."""
    tweets, cursor = [], None
    for _ in range(pages):
        params = {"userName": user, "includeReplies": "false"}
        if cursor:
            params["cursor"] = cursor
        try:
            data = json.loads(http_get(
                f"{X_API}?{urllib.parse.urlencode(params)}", headers={"X-API-Key": key}))
        except Exception as e:  # noqa: BLE001
            print(f"  ! X @{user}: {e}", file=sys.stderr)
            break
        batch = data.get("tweets") or data.get("data") or []
        if isinstance(batch, dict):
            batch = batch.get("tweets", [])
        tweets += batch
        cursor = data.get("next_cursor")
        if not (data.get("has_next_page") and cursor):
            break
    return tweets


def _x_typed_links(tw):
    """Typed text + EXPANDED entity urls only (incl. quoted/retweeted). Never the
    raw JSON, whose truncated display_urls (…) and media links yield junk repos."""
    parts = [tw.get("text") or ""]
    for c in (tw, tw.get("quoted_tweet"), tw.get("retweeted_tweet")):
        if isinstance(c, dict):
            parts.append(c.get("text") or "")
            parts += [u.get("expanded_url") or ""
                      for u in (c.get("entities") or {}).get("urls") or []]
    return " ".join(filter(None, parts))


def _x_identify(prose, add):
    """Name the repo behind each link-less tweet via the LLM, then verify every
    guess against the GitHub API + a star-count check so a hallucination can't pass.
    No-op (keeps only directly-linked repos) if the LLM is unavailable."""
    if not prose:
        return
    prompt = (
        "Each item is a tweet (often Chinese) describing ONE open-source GitHub tool. "
        "Identify the exact repository. Answer immediately from memory; do NOT "
        "deliberate. Use null if you are not sure. "
        'Return ONLY JSON: [{"i":int,"repo":"owner/repo","confidence":0-1}].\n\n'
        + json.dumps([{"i": i, "text": p["text"]} for i, p in enumerate(prose)],
                     ensure_ascii=False)
    )
    guesses = _claude_json(prompt, want="array", model="haiku", timeout=120)
    if not isinstance(guesses, list):
        print("  i X: LLM unavailable — keeping only directly-linked repos", file=sys.stderr)
        return
    found = 0
    for g in guesses:
        i = g.get("i") if isinstance(g, dict) else None
        if not (isinstance(i, int) and 0 <= i < len(prose) and g.get("confidence", 0) >= 0.5):
            continue
        repo, p = g.get("repo"), prose[i]
        if not (isinstance(repo, str) and "/" in repo):
            continue
        info = gh_api(f"/repos/{repo}")
        if not info or info.get("archived") or info.get("fork"):
            continue
        claim, actual = p["claim_stars"], info.get("stargazers_count", 0)
        if claim and not (claim * 0.3 <= actual <= claim * 3):     # star count way off
            print(f"  ! X: rejected {repo} (claim ~{claim}, actual {actual})", file=sys.stderr)
            continue
        add(info["full_name"], p["user"], p["url"], p["likes"])
        found += 1
    print(f"  ✓ X: {found} repo(s) identified from prose tweets", file=sys.stderr)


def src_x():
    """GitHub repos shared by curated X accounts (twitterapi.io). Optional — needs
    TWITTERAPI_IO_KEY. The only source that catches an already-popular tool being
    *re-shared* (the 'mempalace' case): English accounts link the repo directly;
    Chinese accounts describe it in prose, which the LLM resolves and verifies."""
    key = os.environ.get("TWITTERAPI_IO_KEY")
    if not key:
        print("  i X disabled (set TWITTERAPI_IO_KEY to enable)", file=sys.stderr)
        return {}
    accounts = _split_env(
        "GH_RADAR_X_ACCOUNTS",                       # zh discovery accounts first
        "axichuhai,karpathy,swyx,simonw,_philschmid,reach_vb,omarsar0,"
        "clementdelangue,vllm_project,ggerganov")
    pages = int(os.environ.get("GH_RADAR_X_PAGES", "1"))
    max_llm = int(os.environ.get("GH_RADAR_X_MAX_LLM", "25"))

    out, prose = {}, []

    def add(full, user, url, likes):
        e = out.setdefault(full, {"x_mentions": 0, "x_by": [], "x_url": url, "x_likes": 0})
        e["x_mentions"] += 1
        if user not in e["x_by"]:
            e["x_by"].append(user)
        if likes >= e["x_likes"]:
            e["x_likes"], e["x_url"] = likes, (url or e["x_url"])

    for idx, user in enumerate(accounts):
        if idx:
            time.sleep(2.0)                          # twitterapi.io rate-limits bursts
        for tw in _x_tweets(user, key, pages):
            likes = int(tw.get("likeCount") or tw.get("favorite_count") or 0)
            url, text = tw.get("url") or "", tw.get("text") or ""
            links = list(repos_in(_x_typed_links(tw)))
            if links:
                for full in links:                   # repo linked directly in the tweet
                    add(full, user, url, likes)
            elif X_TOOL_RE.search(text):             # repo only named in prose
                prose.append({"user": user, "url": url, "likes": likes,
                              "text": text[:240], "claim_stars": parse_star_count(text)})

    prose.sort(key=lambda p: p["likes"], reverse=True)   # resolve the loudest first
    _x_identify(prose[:max_llm], add)
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


def _claude_json(prompt, want="object", model="sonnet", timeout=240):
    """Run `claude -p` and parse a JSON object/array out of its reply. Returns the
    parsed value, or None if claude is absent/unauthenticated/times out/malformed.
    `want` is "object" -> {...} or "array" -> [...]."""
    cli = shutil.which("claude")
    if not cli:
        return None
    try:
        proc = subprocess.run(
            [cli, "-p", "--output-format", "json", "--model", model],
            input=prompt, capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"claude exited {proc.returncode}: {proc.stderr.strip()[:200]}")
        text = json.loads(proc.stdout).get("result", "") or ""
        pat = r"\{.*\}" if want == "object" else r"\[.*\]"
        m = re.search(pat, text, re.S)        # tolerate preamble / ```json fences
        if not m:
            raise ValueError("no JSON in model output")
        return json.loads(m.group(0))
    except Exception as e:  # noqa: BLE001
        print(f"  ! claude call failed ({e})", file=sys.stderr)
        return None


def parse_star_count(text):
    """Pull a star-ish magnitude from '17w star' / '170k' / '1.7万' -> int, else None."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*([wWkK万萬])", text or "")
    if not m:
        return None
    n = float(m.group(1))
    return int(n * (10000 if m.group(2).lower() in ("w", "万", "萬") else 1000))


def summarize_zh(repos):
    """Best-effort: add a Traditional-Chinese one-liner to each repo via the
    `claude` CLI (local login, or CI with CLAUDE_CODE_OAUTH_TOKEN). One batched
    call for all repos. Silently falls back to English-only if claude is absent."""
    items = [{"name": r["full_name"], "en": r.get("desc", "")} for r in repos]
    prompt = (
        "Below is a JSON array of GitHub repos. For EACH repo write a concise "
        "Traditional Chinese (繁體中文，台灣用語) description of what the tool DOES — "
        "its function in practice, not marketing fluff. Keep each to 15–40 字. "
        "Return ONLY a JSON object mapping each exact `name` to its Chinese string. "
        "No markdown fences, no commentary.\n\nRepos:\n"
        + json.dumps(items, ensure_ascii=False)
    )
    mapping = _claude_json(prompt, want="object")
    if not isinstance(mapping, dict):
        print("  i Chinese summaries unavailable — using English only", file=sys.stderr)
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
    s += min(agg.get("x_mentions", 0), 5) * 8   # shared by curated X accounts
    s += min(agg.get("reddit_points", 0), 1000) * 0.02
    s += min(agg.get("lobsters_score", 0), 200) * 0.3
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
    used = sorted({s for r in repos for s in r["sources"]})
    names = {"trending": "Trending", "hn": "Hacker News", "new": "new repos",
             "lobsters": "Lobsters", "reddit": "Reddit", "x": "X"}
    pretty = ", ".join(names.get(s, s) for s in used)
    lines = [f"# GitHub Radar — {when}", ""]
    lines.append(f"_{len(repos)} new tools surfaced from {pretty}._")
    lines.append("")
    for i, r in enumerate(repos, 1):
        src = r["sources"]
        tags = []
        if "trending" in src:
            tags.append(f"🔥 {r.get('stars_today', 0)}/day")
        if "x" in src:
            by = ", ".join("@" + h for h in r.get("x_by", [])[:2])
            tags.append(f"𝕏 {by}" if by else "𝕏 shared")
        if "hn" in src:
            tags.append(f"💬 HN {r.get('hn_points', 0)}")
        if "reddit" in src:
            tags.append(f"👽 r/{r.get('reddit_sub', '')} {r.get('reddit_points', 0)}")
        if "lobsters" in src:
            tags.append(f"🦞 {r.get('lobsters_score', 0)}")
        if "new" in src:
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
        refs = []
        if r.get("x_url"):
            refs.append(f"[X post]({r['x_url']})")
        if r.get("hn_url"):
            refs.append(f"[HN]({r['hn_url']})")
        if r.get("reddit_url"):
            refs.append(f"[Reddit]({r['reddit_url']})")
        if r.get("lobsters_url"):
            refs.append(f"[Lobsters]({r['lobsters_url']})")
        if refs:
            lines.append("")
            lines.append(" · ".join(refs))
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
    # (label, collector) — optional sources self-disable when their key is absent.
    sources = [
        ("trending", src_github_trending),
        ("hn", src_hacker_news),
        ("new", src_github_new),
        ("lobsters", src_lobsters),
        ("reddit", src_reddit),
        ("x", src_x),
    ]
    agg = {}
    for label, fn in sources:
        try:
            result = fn() or {}
        except Exception as e:  # noqa: BLE001 — one bad source must not sink the rest
            print(f"  ! source {label} crashed: {e}", file=sys.stderr)
            result = {}
        print(f"  {label}: {len(result)} repos", file=sys.stderr)
        for full, d in result.items():
            agg.setdefault(full, {"sources": []})["sources"].append(label)
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
    top = candidates[:int(os.environ.get("GH_RADAR_MAX_ITEMS", "25"))]

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
