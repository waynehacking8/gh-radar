"""Configuration: constants, scoring weights, env helpers. All tunables live here."""
import os
from pathlib import Path

UA = "gh-radar/1.0 (+https://github.com/)"

STATE_DIR = Path(os.environ.get("GH_RADAR_HOME", Path.home() / ".gh-radar"))
SEEN_PATH = STATE_DIR / "seen.json"
# Daily run sentinel: holds the date string of the last completed run. Lets the
# multi-window fallback cron fire many times a day (drop-resistant) while only the
# first fire of the day actually collects + emails; later fires no-op.
LAST_RUN_PATH = STATE_DIR / "last-run"
TIMEZONE = os.environ.get("GH_RADAR_TIMEZONE", "Asia/Taipei")

GH_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
MIN_STARS = int(os.environ.get("MIN_STARS", "30"))
SEEN_TTL_DAYS = int(os.environ.get("SEEN_TTL_DAYS", "90"))
MAX_ITEMS = int(os.environ.get("GH_RADAR_MAX_ITEMS", "5"))
EVERGREEN_STARS = int(os.environ.get("GH_RADAR_EVERGREEN_STARS", "50000"))
# A repo this big (golang/go, tensorflow, kubernetes) sits on Trending every day
# from sheer mass, not news. Treat it as evergreen noise UNLESS it's genuinely
# spiking (>= this many stars/day) or being discussed on HN/X.
EVERGREEN_VELOCITY = 250

# Importance gate. Discovery stays broad, but delivery is deliberately sparse:
# a repo must clear at least one of these decisive signals (or be independently
# corroborated; see scoring.importance_reasons) before it can enter the email.
# The defaults are intentionally conservative so "Trending #1"-calibre projects
# stand out instead of being buried in a 50-link daily catalogue.
TOP_TRENDING_RANK = int(os.environ.get("GH_RADAR_TOP_TRENDING_RANK", "3"))
MOMENTUM_STARS_PER_DAY = int(os.environ.get("GH_RADAR_MOMENTUM_STARS_PER_DAY", "250"))
STRONG_HN_POINTS = int(os.environ.get("GH_RADAR_STRONG_HN_POINTS", "100"))
STRONG_X_LIKES = int(os.environ.get("GH_RADAR_STRONG_X_LIKES", "100"))
STRONG_REDDIT_POINTS = int(os.environ.get("GH_RADAR_STRONG_REDDIT_POINTS", "300"))
STRONG_LOBSTERS_SCORE = int(os.environ.get("GH_RADAR_STRONG_LOBSTERS_SCORE", "50"))
BREAKOUT_NEW_REPO_STARS = int(os.environ.get("GH_RADAR_BREAKOUT_NEW_REPO_STARS", "1000"))

# A second, independent community seeing the same repo can promote a moderate
# signal. "new" and "trending" are one GitHub family.
MODERATE_STARS_PER_DAY = 50
MODERATE_HN_POINTS = 30
MODERATE_X_LIKES = 25
MODERATE_REDDIT_POINTS = 100
MODERATE_LOBSTERS_SCORE = 20

# Every source must represent activity in a bounded current window. GitHub
# Trending and Reddit are already daily feeds; this cap is applied explicitly to
# sources whose payload can contain pinned or lingering items (X and Lobsters).
SOURCE_MAX_AGE_HOURS = int(os.environ.get("GH_RADAR_SOURCE_MAX_AGE_HOURS", "48"))
NEW_REPO_MAX_AGE_DAYS = int(os.environ.get("GH_RADAR_NEW_REPO_MAX_AGE_DAYS", "7"))

# Text-length caps (chars) for the digest blurbs — kept here so the email's
# verbosity is tunable in one place.
X_PROSE_MAX = 300      # tweet text fed to the LLM
X_CONTEXT_MAX = 280    # post text retained as scene
QUOTE_MAX = 160        # verbatim quote in the email
ZH_MAX = 400           # generated zh blurb
# zh summaries are generated in small batches so one slow/failed LLM call can't
# time out and drop *every* summary (the richer 2-3 sentence blurbs made a single
# all-repos call exceed claude's timeout).
SUMMARY_BATCH = 12

# Scoring weights — hoisted here so ranking is tunable without touching logic.
W = {
    "stars_today": 1.0,        # trending velocity
    "hn_points": 2.0,          # HN discussion (weighted higher)
    "x_flat": 120,             # a human you follow sharing it — strongest signal
    "x_mention": 15, "x_mention_cap": 5,
    "reddit": 0.02, "reddit_cap": 1000,
    "lobsters": 0.3, "lobsters_cap": 200,
    "new_repo": 40,            # novelty bonus
    "stars_tiebreak": 0.01, "stars_cap": 5000,
    "per_source": 15,          # multi-source = stronger signal
    "top_rank": 100,           # global daily Trending rank (3rd=1x, 1st=3x)
}


def split_env(name, default):
    """Comma- (or |-) separated env list, trimmed and empty-filtered."""
    raw = os.environ.get(name, default)
    sep = "|" if "|" in raw else ","
    return [x.strip() for x in raw.split(sep) if x.strip()]
