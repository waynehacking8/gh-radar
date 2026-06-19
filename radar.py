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


X_TOOL_RE = re.compile(r"github|开源|開源|\bstar\b|星标|星標|⭐|repo|工具|神器|项目|項目", re.I)
FC_SCRAPE = "https://api.firecrawl.dev/v2/scrape"
FC_SEARCH = "https://api.firecrawl.dev/v2/search"


def _firecrawl(endpoint, payload, retries=3):
    """Call Firecrawl (free + keyless; uses FIRECRAWL_API_KEY if set for far higher
    limits). Retries on 429 with backoff (honouring Retry-After). -> data dict / None.
    Any failure returns None so a Firecrawl outage never breaks the digest."""
    headers = {"User-Agent": UA, "Content-Type": "application/json"}
    fkey = os.environ.get("FIRECRAWL_API_KEY")
    if fkey:
        headers["Authorization"] = f"Bearer {fkey}"
    body = json.dumps(payload).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(endpoint, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            return data.get("data") if data.get("success") else None
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = min(int(e.headers.get("Retry-After") or 0) or 5 * (attempt + 1), 30)
                print(f"  i firecrawl 429 — backing off {wait}s "
                      f"(set FIRECRAWL_API_KEY to raise limits)", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  ! firecrawl {endpoint.rsplit('/', 1)[-1]}: {e}", file=sys.stderr)
            return None
        except Exception as e:  # noqa: BLE001
            print(f"  ! firecrawl {endpoint.rsplit('/', 1)[-1]}: {e}", file=sys.stderr)
            return None
    return None


def _scrape_md(url):
    """Scrape one URL to markdown via Firecrawl. '' on failure. maxAge lets Firecrawl
    return a recent cached scrape (faster + far cheaper than a fresh crawl)."""
    data = _firecrawl(FC_SCRAPE, {"url": url, "formats": ["markdown"],
                                  "maxAge": 14_400_000})   # accept ≤4h-old cache
    if isinstance(data, dict):
        return (data.get("markdown") or "").replace("\\", "")
    return ""


def _parse_x_posts(md):
    """Parse Firecrawl's X-profile markdown into [{text, url, likes}]."""
    posts = []
    for block in re.split(r"\n#{2,3}\s+\d+\.\s+Post", md)[1:]:
        um = re.search(r"\]\((https?://[^)]+/status/\d+)\)", block)
        text = " ".join(re.findall(r"^>\s?(.*)$", block, re.M)).strip()
        lm = re.search(r"Likes:\s*([\d,]+)", block)
        if text:
            posts.append({"text": text, "url": um.group(1) if um else "",
                          "likes": int(lm.group(1).replace(",", "")) if lm else 0})
    return posts


def _resolve_repo(query, claim_stars):
    """Resolve a tool name to its real repo via GitHub search, disambiguated by the
    star count claimed in the post. This beats asking the LLM to recall owner/repo
    (which hallucinates owners). Returns the repo info dict, or None."""
    data = gh_api(f"/search/repositories?q={urllib.parse.quote(query)}&sort=stars&per_page=5")
    items = (data or {}).get("items", [])
    if not items:
        return None
    if claim_stars:                       # pick the candidate whose stars match the claim
        in_range = [it for it in items
                    if claim_stars * 0.4 <= it["stargazers_count"] <= claim_stars * 2.5]
        return min(in_range, key=lambda it: abs(it["stargazers_count"] - claim_stars),
                   default=None)
    top = items[0]                        # no claim: trust the top hit if it's popular
    return top if top["stargazers_count"] >= MIN_STARS else None


def _x_identify(prose, add):
    """For each link-less tool tweet: the LLM extracts just the tool NAME / search
    keywords (easy + reliable), then GitHub search + star-count match resolves the
    real repo. No-op (keeps only directly-linked repos) if the LLM is unavailable."""
    if not prose:
        return
    prompt = (
        "Each item is a tweet (often Chinese) about ONE open-source GitHub tool. "
        "Extract the tool's NAME or the best GitHub search keywords (prefer the "
        "literal project name in latin letters if present, e.g. 'mempalace', "
        "'ai-hedge-fund'). Do NOT guess the owner. null if it is not a specific tool. "
        'Return ONLY JSON: [{"i":int,"query":"...","confidence":0-1}].\n\n'
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
        query, p = g.get("query"), prose[i]
        if not isinstance(query, str) or len(query) < 2:
            continue
        info = _resolve_repo(query, p["claim_stars"])
        if not info or info.get("archived") or info.get("fork"):
            continue
        add(info["full_name"], p["user"], p["url"], p["likes"])
        found += 1
    print(f"  ✓ X: {found} repo(s) resolved from prose tweets", file=sys.stderr)


def src_x():
    """GitHub repos shared by curated X accounts, scraped via Firecrawl (free, no
    key, no login wall). The only source that catches an already-popular tool being
    *re-shared* (the 'mempalace' case): Chinese accounts describe a tool in prose;
    the LLM extracts its name and GitHub search + star-count resolves the real repo."""
    accounts = _split_env(
        "GH_RADAR_X_ACCOUNTS",                       # zh tool-discovery accounts
        "axichuhai,dotey,op7418")
    if not accounts:
        print("  i X disabled (GH_RADAR_X_ACCOUNTS empty)", file=sys.stderr)
        return {}
    max_llm = int(os.environ.get("GH_RADAR_X_MAX_LLM", "30"))

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
            time.sleep(1.0)                          # be polite to the free tier
        for post in _parse_x_posts(_scrape_md(f"https://x.com/{user}")):
            text, url, likes = post["text"], post["url"], post["likes"]
            links = list(repos_in(text))
            if links:
                for full in links:
                    add(full, user, url, likes)
            elif X_TOOL_RE.search(text):
                prose.append({"user": user, "url": url, "likes": likes,
                              "text": text[:300], "claim_stars": parse_star_count(text)})

    prose.sort(key=lambda p: p["likes"], reverse=True)
    _x_identify(prose[:max_llm], add)
    return out


def src_fc_articles():
    """Discovery beyond any single account: Firecrawl-search a few 'best tools'
    queries, scrape the listicle articles, and harvest the GitHub repos they link.
    Free/keyless. Disabled by setting GH_RADAR_FC_QUERIES to an empty string."""
    queries = _split_env(
        "GH_RADAR_FC_QUERIES",
        "trending open source AI developer tools 2026|"
        "underrated useful github repos people are sharing")
    if not queries:
        return {}
    out = {}
    per_q = int(os.environ.get("GH_RADAR_FC_PER_QUERY", "2"))
    for qi, query in enumerate(queries):
        if qi:
            time.sleep(1.0)
        data = _firecrawl(FC_SEARCH, {"query": query, "limit": per_q})
        results = (data or {}).get("web", []) if isinstance(data, dict) else []
        for r in results[:per_q]:
            url = r.get("url") or ""
            if not url or "github.com" in url:       # the trending page itself adds noise
                continue
            for full in repos_in(_scrape_md(url)):
                out.setdefault(full, {"fc_url": url})
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
    # A human you follow choosing to share a tool is the strongest signal here, so
    # X gets a big flat bonus (it must not be drowned out by high-velocity trending).
    s += 120 if "x" in agg.get("sources", []) else 0
    s += min(agg.get("x_mentions", 0), 5) * 15
    s += min(agg.get("reddit_points", 0), 1000) * 0.02
    s += min(agg.get("lobsters_score", 0), 200) * 0.3
    s += 25 if "web" in agg.get("sources", []) else 0   # surfaced in a tool article
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
def _provenance(r):
    """Human-readable source attribution for one repo. Firecrawl-derived sources
    (X, web) are explicitly marked as such so the origin is always clear."""
    src, parts = r["sources"], []
    if "trending" in src:
        parts.append("GitHub Trending")
    if "hn" in src:
        parts.append("Hacker News")
    if "new" in src:
        parts.append("GitHub new-repo search")
    if "lobsters" in src:
        parts.append("Lobsters")
    if "reddit" in src:
        parts.append(f"Reddit r/{r.get('reddit_sub', '')}".rstrip("/ "))
    if "x" in src:
        who = ", ".join("@" + h for h in r.get("x_by", [])[:2])
        parts.append(f"Firecrawl → X {who}".strip())
    if "web" in src:
        host = re.sub(r"^https?://(www\.)?", "", r.get("fc_url", "")).split("/")[0]
        parts.append(f"Firecrawl → {host}" if host else "Firecrawl (web article)")
    return " · ".join(parts) or "unknown"


def render_md(repos, when):
    used = sorted({s for r in repos for s in r["sources"]})
    names = {"trending": "Trending", "hn": "Hacker News", "new": "new repos",
             "lobsters": "Lobsters", "reddit": "Reddit", "x": "X", "web": "web articles"}
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
        if "web" in src:
            tags.append("📰 web")
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
        if r.get("fc_url"):
            refs.append(f"[article]({r['fc_url']})")
        lines.append("")
        lines.append(f"📍 出處 / via: {_provenance(r)}")
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
        ("web", src_fc_articles),
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
    top = candidates[:int(os.environ.get("GH_RADAR_MAX_ITEMS", "50"))]

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
