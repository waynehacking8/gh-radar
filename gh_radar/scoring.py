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
    if r.new_repo:
        s += W["new_repo"]
    s += min(r.stars, W["stars_cap"]) * W["stars_tiebreak"]
    s += W["per_source"] * len(r.sources)
    if r.trending_rank and r.trending_rank <= config.TOP_TRENDING_RANK:
        # Preserve global Trending leaders near the top after they pass the
        # importance gate. Rank #1 gets 3x, #2 2x, #3 1x with the default gate.
        s += max(1, config.TOP_TRENDING_RANK + 1 - r.trending_rank) * W["top_rank"]
    return s


def _source_families(r):
    """Independent discovery families; two GitHub endpoints are one family."""
    families = set()
    if {"trending", "new"} & set(r.sources):
        families.add("GitHub")
    if "hn" in r.sources:
        families.add("Hacker News")
    if "x" in r.sources:
        families.add("X")
    if "reddit" in r.sources:
        families.add("Reddit")
    if "lobsters" in r.sources:
        families.add("Lobsters")
    return families


def importance_reasons(r):
    """Return concrete reasons this repo is important enough to push.

    Ranking answers "which first"; this gate answers the more important
    question: "should this interrupt the reader at all?" Ordinary language-page
    Trending entries and weak single-source activity do
    not qualify. The gate is deterministic so quiet days remain genuinely quiet.
    """
    reasons = []
    if r.trending_rank and r.trending_rank <= config.TOP_TRENDING_RANK:
        reasons.append(f"GitHub Trending #{r.trending_rank}")
    if r.stars_today >= config.MOMENTUM_STARS_PER_DAY:
        reasons.append(f"{r.stars_today:,} stars/day")
    if r.hn_points >= config.STRONG_HN_POINTS:
        reasons.append(f"{r.hn_points:,} HN points")
    if r.x_likes >= config.STRONG_X_LIKES:
        reasons.append(f"{r.x_likes:,} likes on a curated X post")
    if r.reddit_points >= config.STRONG_REDDIT_POINTS:
        reasons.append(f"{r.reddit_points:,} Reddit points")
    if r.lobsters_score >= config.STRONG_LOBSTERS_SCORE:
        reasons.append(f"{r.lobsters_score:,} Lobsters points")
    if r.new_repo and r.stars >= config.BREAKOUT_NEW_REPO_STARS:
        reasons.append(f"new repo already at {r.stars:,} stars")

    families = _source_families(r)
    moderate = (
        r.stars_today >= config.MODERATE_STARS_PER_DAY
        or r.hn_points >= config.MODERATE_HN_POINTS
        or r.x_likes >= config.MODERATE_X_LIKES
        or r.reddit_points >= config.MODERATE_REDDIT_POINTS
        or r.lobsters_score >= config.MODERATE_LOBSTERS_SCORE
    )
    if not reasons and len(families) >= 2 and moderate:
        reasons.append("corroborated by " + " + ".join(sorted(families)))
    return reasons


def is_evergreen_noise(r):
    """Filter famous, already-huge projects that aren't actually news today. A repo
    such as golang/go, tensorflow, or kubernetes can sit on a niche Trending page
    from sheer size rather than current news. It is kept only if it is a global
    leader, brand-new, genuinely spiking, or actively discussed by a current
    community source."""
    if r.new_repo:
        return False
    if r.trending_rank and r.trending_rank <= config.TOP_TRENDING_RANK:
        return False                                      # current global leader, even if already huge
    if r.stars < config.EVERGREEN_STARS:
        return False
    spiking = r.stars_today >= config.EVERGREEN_VELOCITY  # genuinely surging, not passive
    discussed = bool({"hn", "x", "reddit", "lobsters"} & set(r.sources))
    return not (spiking or discussed)
