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

GH_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
MIN_STARS = int(os.environ.get("MIN_STARS", "30"))
SEEN_TTL_DAYS = int(os.environ.get("SEEN_TTL_DAYS", "14"))
MAX_ITEMS = int(os.environ.get("GH_RADAR_MAX_ITEMS", "50"))
# A repo that ONLY appears in a "best tools" web article and is already this
# popular is evergreen, not news — filter it out (the article just re-listed it).
EVERGREEN_STARS = int(os.environ.get("GH_RADAR_EVERGREEN_STARS", "50000"))
# A repo this big (golang/go, tensorflow, kubernetes) sits on Trending every day
# from sheer mass, not news. Treat it as evergreen noise UNLESS it's genuinely
# spiking (>= this many stars/day) or being discussed on HN/X.
EVERGREEN_VELOCITY = int(os.environ.get("GH_RADAR_EVERGREEN_VELOCITY", "250"))

# Text-length caps (chars) for the digest blurbs — kept here so the email's
# verbosity is tunable in one place.
X_PROSE_MAX = int(os.environ.get("GH_RADAR_X_PROSE_MAX", "300"))      # tweet text fed to the LLM
X_CONTEXT_MAX = int(os.environ.get("GH_RADAR_X_CONTEXT_MAX", "280"))  # post text retained as scene
QUOTE_MAX = int(os.environ.get("GH_RADAR_QUOTE_MAX", "160"))          # verbatim quote in the email
ZH_MAX = int(os.environ.get("GH_RADAR_ZH_MAX", "400"))               # generated zh blurb
# zh summaries are generated in small batches so one slow/failed LLM call can't
# time out and drop *every* summary (the richer 2-3 sentence blurbs made a single
# all-repos call exceed claude's timeout).
SUMMARY_BATCH = int(os.environ.get("GH_RADAR_SUMMARY_BATCH", "12"))

# Scoring weights — hoisted here so ranking is tunable without touching logic.
W = {
    "stars_today": 1.0,        # trending velocity
    "hn_points": 2.0,          # HN discussion (weighted higher)
    "x_flat": 120,             # a human you follow sharing it — strongest signal
    "x_mention": 15, "x_mention_cap": 5,
    "reddit": 0.02, "reddit_cap": 1000,
    "lobsters": 0.3, "lobsters_cap": 200,
    "web_flat": 25,            # surfaced in a tool round-up article
    "new_repo": 40,            # novelty bonus
    "stars_tiebreak": 0.01, "stars_cap": 5000,
    "per_source": 15,          # multi-source = stronger signal
}


def split_env(name, default):
    """Comma- (or |-) separated env list, trimmed and empty-filtered."""
    raw = os.environ.get(name, default)
    sep = "|" if "|" in raw else ","
    return [x.strip() for x in raw.split(sep) if x.strip()]
