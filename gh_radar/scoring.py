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
    """Filter famous, already-huge projects that aren't actually news today. A repo
    only re-listed in a 'best tools' web article is noise; so is a mega-popular
    project (golang/go, tensorflow, kubernetes) that just sits on Trending from its
    sheer size. Either is kept only if it's genuinely current: a brand-new repo, a
    real star spike today, or active HN discussion / an X share."""
    if r.new_repo:
        return False
    if r.stars < config.EVERGREEN_STARS:
        return False
    if set(r.sources) == {"web"}:
        return True                                       # web-only re-list of a famous repo
    spiking = r.stars_today >= config.EVERGREEN_VELOCITY  # genuinely surging, not passive
    discussed = bool({"hn", "x"} & set(r.sources))        # a current conversation worth surfacing
    return not (spiking or discussed)
