"""Signal sources. Each `src_*()` returns {full_name: {attrs}} and self-isolates
(returns {} on any failure). Attribute keys match Repo fields; the pipeline merges
them. Helpers are defined before the sources that use them."""
import base64
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape

from . import config
from .clients import FC_SEARCH, claude_json, firecrawl, gh_api, http_get, scrape_md

# ----------------------------------------------------------------- repo extraction
SKIP_NAME_RE = re.compile(
    r"(awesome-|/awesome$|interview|roadmap|tutorial|free-?programming|"
    r"build-your-own|coding-interview|system-design|the-book|-book$|cheatsheet)",
    re.I,
)
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


def parse_star_count(text):
    """Pull a star count from '17w star' / '55K 星标' / '6万+ star' -> int, else None.
    Only counts a magnitude NEXT TO a star keyword, so '4K video' / '10k users'
    aren't misread as stars (which would mis-resolve the repo)."""
    text = text or ""
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([wWkK万萬])", text):
        window = text[max(0, m.start() - 8):m.end() + 8].lower()
        if "star" in window or "星" in window or "⭐" in window:
            n = float(m.group(1))
            return int(n * (10000 if m.group(2).lower() in ("w", "万", "萬") else 1000))
    return None


# ------------------------------------------------------------------ GitHub Trending
TREND_LANGS = config.split_env("GH_RADAR_TREND_LANGS", "python,rust,go,typescript,c++,javascript")


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
        sm = re.search(r'/stargazers"[^>]*>\s*([\d,]+)', block)
        stars = int(sm.group(1).replace(",", "")) if sm else 0
        tm = re.search(r"([\d,]+)\s+stars (?:today|this week|this month)", block)
        velocity = int(tm.group(1).replace(",", "")) if tm else 0
        prev = out.get(full, {})
        out[full] = {
            "stars_today": max(velocity, prev.get("stars_today", 0)),
            "desc": prev.get("desc") or desc,
            "stars": max(stars, prev.get("stars", 0)),
        }


def src_github_trending():
    """Scrape github.com/trending across windows + languages -> {full: {...}}."""
    out = {}
    pages = ["https://github.com/trending?since=daily",
             "https://github.com/trending?since=weekly"]
    pages += [f"https://github.com/trending/{lang}?since=daily" for lang in TREND_LANGS]
    for url in pages:
        try:
            _parse_trending(http_get(url), out)
        except Exception as e:  # noqa: BLE001
            print(f"  ! trending fetch failed ({url}): {e}", file=sys.stderr)
    return out


# --------------------------------------------------------------------- Hacker News
def src_hacker_news():
    """Github repos mentioned on HN in the last 24h -> {full: {hn_points, hn_url}}."""
    out = {}
    since = int(time.time()) - 86400
    url = ("https://hn.algolia.com/api/v1/search_by_date?query=github.com&tags=story"
           f"&numericFilters=created_at_i>{since}&hitsPerPage=100")
    try:
        data = json.loads(http_get(url))
    except Exception as e:  # noqa: BLE001
        print(f"  ! hacker news fetch failed: {e}", file=sys.stderr)
        return out
    for h in data.get("hits", []):
        points = h.get("points") or 0
        hn_url = f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        title = (h.get("title") or "").strip()
        for full in repos_in(h.get("url") or ""):
            if full not in out or points > out[full]["hn_points"]:
                out[full] = {"hn_points": points, "hn_url": hn_url, "context": title}
    return out


# ------------------------------------------------------------------- GitHub Search
def src_github_new():
    """Brand-new repos (created <=10 days ago) already gaining stars."""
    out = {}
    since = datetime.now(timezone.utc).timestamp() - 10 * 86400
    since_d = datetime.fromtimestamp(since, timezone.utc).strftime("%Y-%m-%d")
    q = f"created:>={since_d}+stars:>={max(config.MIN_STARS, 50)}"
    data = gh_api(f"/search/repositories?q={q}&sort=stars&order=desc&per_page=30")
    for it in (data or {}).get("items", []):
        out[it["full_name"]] = {"new_repo": True}
    return out


# ------------------------------------------------------------------------ Lobsters
def src_lobsters():
    """Github repos linked from the Lobsters hottest feed."""
    out = {}
    try:
        data = json.loads(http_get("https://lobste.rs/hottest.json"))
    except Exception as e:  # noqa: BLE001
        print(f"  ! lobsters fetch failed: {e}", file=sys.stderr)
        return out
    for s in data:
        c_url = s.get("comments_url") or s.get("short_id_url") or s.get("url") or ""
        pts = s.get("score") or 0
        for full in repos_in(s.get("url") or ""):
            if full not in out or pts > out[full]["lobsters_score"]:
                out[full] = {"lobsters_score": pts, "lobsters_url": c_url}
    return out


# -------------------------------------------------------------------------- Reddit
def src_reddit():
    """Tool-discovery subreddits. Optional: REDDIT_CLIENT_ID/SECRET (anonymous JSON
    is blocked). {} if not configured."""
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        print("  i reddit disabled (set REDDIT_CLIENT_ID/SECRET to enable)", file=sys.stderr)
        return {}
    subs = config.split_env(
        "GH_RADAR_SUBREDDITS",
        "commandline,selfhosted,opensource,coolgithubprojects,golang,rust,programming")
    out = {}
    try:
        auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
        req = urllib.request.Request(
            "https://www.reddit.com/api/v1/access_token",
            data=b"grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth}", "User-Agent": config.UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            token = json.loads(r.read().decode())["access_token"]
    except Exception as e:  # noqa: BLE001
        print(f"  ! reddit auth failed: {e}", file=sys.stderr)
        return out
    for sub in subs:
        try:
            data = json.loads(http_get(f"https://oauth.reddit.com/r/{sub}/top?t=day&limit=25",
                                       headers={"Authorization": f"Bearer {token}"}))
        except Exception as e:  # noqa: BLE001
            print(f"  ! reddit r/{sub} failed: {e}", file=sys.stderr)
            continue
        for child in data.get("data", {}).get("children", []):
            p = child.get("data", {})
            pts = p.get("ups") or p.get("score") or 0
            permalink = "https://reddit.com" + p.get("permalink", "")
            title = (p.get("title") or "").strip()
            blob = f"{p.get('url','')} {p.get('selftext','')} {title}"
            for full in repos_in(blob):
                if full not in out or pts > out[full]["reddit_points"]:
                    out[full] = {"reddit_points": pts, "reddit_url": permalink,
                                 "reddit_sub": sub, "context": title}
    return out


# ------------------------------------------------------------- X / Twitter (Firecrawl)
X_TOOL_RE = re.compile(r"github|开源|開源|\bstar\b|星标|星標|⭐|repo|工具|神器|项目|項目", re.I)


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
    star count claimed in the post (beats LLM recall, which hallucinates owners).
    Returns the full repo-API info dict (reused downstream to skip a re-fetch)."""
    data = gh_api(f"/search/repositories?q={urllib.parse.quote(query)}&sort=stars&per_page=5")
    items = (data or {}).get("items", [])
    if not items:
        return None
    if claim_stars:
        in_range = [it for it in items
                    if claim_stars * 0.4 <= it["stargazers_count"] <= claim_stars * 2.5]
        return min(in_range, key=lambda it: abs(it["stargazers_count"] - claim_stars), default=None)
    top = items[0]
    return top if top["stargazers_count"] >= config.MIN_STARS else None


def _x_identify(prose, add):
    """LLM extracts the tool NAME (reliable), then GitHub search + star-count match
    resolves the real repo. No-op (keeps only directly-linked repos) if LLM is down."""
    if not prose:
        return
    prompt = (
        "Each item is a tweet (often Chinese) about ONE open-source GitHub tool. "
        "Extract the tool's NAME or best GitHub search keywords (prefer the literal "
        "project name in latin letters, e.g. 'mempalace', 'ai-hedge-fund'). Do NOT "
        "guess the owner. null if not a specific tool. Answer immediately. "
        'Return ONLY JSON: [{"i":int,"query":"...","confidence":0-1}].\n\n'
        + json.dumps([{"i": i, "text": p["text"]} for i, p in enumerate(prose)], ensure_ascii=False))
    guesses = claude_json(prompt, want="array", model="haiku", timeout=120)
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
        add(info["full_name"], p["user"], p["url"], p["likes"], info=info, context=p["text"])
        found += 1
    print(f"  ✓ X: {found} repo(s) resolved from prose tweets", file=sys.stderr)


def src_x():
    """GitHub repos shared by curated X accounts, scraped via Firecrawl (free, no
    login wall). English accounts link the repo; Chinese accounts describe it in
    prose, resolved by LLM name-extract + GitHub star match."""
    accounts = config.split_env("GH_RADAR_X_ACCOUNTS", "axichuhai,dotey,op7418,precisox")
    if not accounts:
        print("  i X disabled (GH_RADAR_X_ACCOUNTS empty)", file=sys.stderr)
        return {}
    max_llm = int(os.environ.get("GH_RADAR_X_MAX_LLM", "30"))
    out, prose = {}, []

    def add(full, user, url, likes, info=None, context=""):
        e = out.setdefault(full, {"x_mentions": 0, "x_by": [], "x_url": url, "x_likes": 0})
        e["x_mentions"] += 1
        if user not in e["x_by"]:
            e["x_by"].append(user)
        if likes >= e["x_likes"]:                 # keep the most-liked post's text + link
            e["x_likes"], e["x_url"] = likes, (url or e["x_url"])
            if context:
                e["context"] = " ".join(context.split())[:280]
        if info:                              # pre-enrich from the resolve fetch (saves an API call)
            e["stars"] = info.get("stargazers_count", e.get("stars", 0))
            e["desc"] = (info.get("description") or e.get("desc", "")).strip()
            e["lang"] = info.get("language") or e.get("lang", "")
            e["url"] = info.get("html_url") or e.get("url", "")

    for idx, user in enumerate(accounts):
        if idx:
            time.sleep(1.0)                   # be polite to the free tier
        for post in _parse_x_posts(scrape_md(f"https://x.com/{user}")):
            text, url, likes = post["text"], post["url"], post["likes"]
            links = list(repos_in(text))
            if links:
                for full in links:
                    add(full, user, url, likes, context=text)
            elif X_TOOL_RE.search(text):
                prose.append({"user": user, "url": url, "likes": likes,
                              "text": text[:300], "claim_stars": parse_star_count(text)})

    prose.sort(key=lambda p: p["likes"], reverse=True)
    _x_identify(prose[:max_llm], add)
    return out


# ----------------------------------------------------------- web articles (Firecrawl)
def src_fc_articles():
    """Discovery beyond any single account: Firecrawl-search 'best tools' queries,
    scrape the listicles, harvest the GitHub repos. Disabled if GH_RADAR_FC_QUERIES
    is empty."""
    queries = config.split_env(
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
        data = firecrawl(FC_SEARCH, {"query": query, "limit": per_q})
        results = (data or {}).get("web", []) if isinstance(data, dict) else []
        for r in results[:per_q]:
            url = r.get("url") or ""
            if not url or "github.com" in url:       # the trending page itself adds noise
                continue
            for full in repos_in(scrape_md(url)):
                out.setdefault(full, {"fc_url": url})
    return out


# ---------------------------------------------------------------------- enrichment
def enrich(repo):
    """Fill missing stars/desc/lang/url from the repo API. Returns False (drop) for
    dead/fork/archived repos. Skips the fetch if already enriched (e.g. X-resolved)."""
    if repo.stars and repo.desc:
        return True
    info = gh_api(f"/repos/{repo.full_name}")
    if not info or info.get("archived") or info.get("fork"):
        return False
    repo.stars = info.get("stargazers_count", repo.stars)
    repo.desc = (info.get("description") or repo.desc or "").strip()
    repo.lang = info.get("language") or ""
    repo.url = info.get("html_url") or f"https://github.com/{repo.full_name}"
    return True


SOURCES = [
    ("trending", src_github_trending),
    ("hn", src_hacker_news),
    ("new", src_github_new),
    ("lobsters", src_lobsters),
    ("reddit", src_reddit),
    ("x", src_x),
    ("web", src_fc_articles),
]
