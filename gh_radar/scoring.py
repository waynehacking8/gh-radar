"""Ranking: score a Repo from its signals, and decide which repos to keep."""
from . import config

W = config.W


def score(r):
    """Higher = more worth surfacing. Weights live in config.W."""
    s = 0.0
    s += r.stars_today * W["stars_today"]
    s += r.hn_points * W["hn_points"]
    if "x" in r.sources:                       # a human you follow shared it — strongest
        s += W["x_flat"]
    s += min(r.x_mentions, W["x_mention_cap"]) * W["x_mention"]
    s += min(r.reddit_points, W["reddit_cap"]) * W["reddit"]
    s += min(r.lobsters_score, W["lobsters_cap"]) * W["lobsters"]
    if "web" in r.sources:
        s += W["web_flat"]
    if r.new_repo:
        s += W["new_repo"]
    s += min(r.stars, W["stars_cap"]) * W["stars_tiebreak"]
    s += W["per_source"] * len(r.sources)
    return s


def is_evergreen_noise(r):
    """A repo that ONLY surfaced in a 'best tools' web article and is already very
    popular is evergreen, not news — the article just re-listed a famous project.
    (Trending/HN/X imply current activity, so they're never treated as noise.)"""
    return set(r.sources) == {"web"} and r.stars >= config.EVERGREEN_STARS and not r.new_repo
