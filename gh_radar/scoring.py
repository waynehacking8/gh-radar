"""Importance classification, ranking, and evergreen-noise filtering."""
from dataclasses import dataclass

from . import config

W = config.W


@dataclass(frozen=True)
class ImportanceDecision:
    """Auditable delivery decision made before score-based ordering."""

    tier: str
    reasons: tuple[str, ...]


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


def _active_families(r):
    """Independently active source families at their moderate thresholds.

    Merely appearing in two feeds is not corroboration: each family must carry
    its own measurable activity. GitHub Trending and new-repo search intentionally
    collapse into one family.
    """
    families = {}
    github_signals = []
    if r.stars_today >= config.MODERATE_STARS_PER_DAY:
        github_signals.append(f"{r.stars_today:,} stars/day")
    if r.new_repo and r.stars >= config.MODERATE_NEW_REPO_STARS:
        github_signals.append(f"new repo at {r.stars:,} stars")
    if github_signals:
        families["GitHub"] = ", ".join(github_signals)
    if r.hn_points >= config.MODERATE_HN_POINTS:
        families["Hacker News"] = f"{r.hn_points:,} points"
    if r.x_likes >= config.MODERATE_X_LIKES:
        families["X"] = f"{r.x_likes:,} likes"
    if r.reddit_points >= config.MODERATE_REDDIT_POINTS:
        families["Reddit"] = f"{r.reddit_points:,} points"
    if r.lobsters_score >= config.MODERATE_LOBSTERS_SCORE:
        families["Lobsters"] = f"{r.lobsters_score:,} points"
    return families


def classify_importance(r):
    """Classify a repo as Tier A (must-send), Tier B (notable), or unqualified.

    Tier A is exceptional single-source activity or genuine independent
    corroboration and may expand the digest beyond five items. Tier B is a strong
    single-source signal and only fills the normal five-item target.
    """
    tier_a = []
    if r.trending_rank and r.trending_rank <= config.TOP_TRENDING_RANK:
        tier_a.append(f"GitHub Trending #{r.trending_rank}")
    if r.stars_today >= config.MUST_SEND_STARS_PER_DAY:
        tier_a.append(f"{r.stars_today:,} stars/day")
    if r.hn_points >= config.MUST_SEND_HN_POINTS:
        tier_a.append(f"{r.hn_points:,} HN points")
    if r.x_likes >= config.MUST_SEND_X_LIKES:
        tier_a.append(f"{r.x_likes:,} likes on a curated X post")
    if r.reddit_points >= config.MUST_SEND_REDDIT_POINTS:
        tier_a.append(f"{r.reddit_points:,} Reddit points")
    if r.lobsters_score >= config.MUST_SEND_LOBSTERS_SCORE:
        tier_a.append(f"{r.lobsters_score:,} Lobsters points")
    if r.new_repo and r.stars >= config.MUST_SEND_NEW_REPO_STARS:
        tier_a.append(f"new repo already at {r.stars:,} stars")

    active = _active_families(r)
    if len(active) >= 2:
        detail = " + ".join(
            f"{name} ({signal})" for name, signal in sorted(active.items()))
        tier_a.append(f"independently corroborated by {detail}")
    if tier_a:
        return ImportanceDecision("A", tuple(tier_a))

    tier_b = []
    if r.stars_today >= config.MOMENTUM_STARS_PER_DAY:
        tier_b.append(f"{r.stars_today:,} stars/day")
    if r.hn_points >= config.STRONG_HN_POINTS:
        tier_b.append(f"{r.hn_points:,} HN points")
    if r.x_likes >= config.STRONG_X_LIKES:
        tier_b.append(f"{r.x_likes:,} likes on a curated X post")
    if r.reddit_points >= config.STRONG_REDDIT_POINTS:
        tier_b.append(f"{r.reddit_points:,} Reddit points")
    if r.lobsters_score >= config.STRONG_LOBSTERS_SCORE:
        tier_b.append(f"{r.lobsters_score:,} Lobsters points")
    if r.new_repo and r.stars >= config.BREAKOUT_NEW_REPO_STARS:
        tier_b.append(f"new repo already at {r.stars:,} stars")
    if tier_b:
        return ImportanceDecision("B", tuple(tier_b))
    return None


def importance_reasons(r):
    """Compatibility helper for callers that only need the explanation."""
    decision = classify_importance(r)
    return list(decision.reasons) if decision else []


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
