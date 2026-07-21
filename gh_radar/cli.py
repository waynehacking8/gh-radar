"""Pipeline: collect from every source -> merge into Repos -> select/rank -> render
-> email -> remember. Each stage is a small function so the flow reads top-down."""
import os
import sys
import time
from datetime import datetime, timezone
from operator import attrgetter
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config
from .email_out import send_email
from .models import Repo
from .render import render_md, summarize_zh
from .scoring import classify_importance, is_evergreen_noise, score
from .sources import SKIP_NAME_RE, SOURCES, enrich
from .state import already_ran_today, load_seen, mark_ran_today, save_seen


def collect():
    """Run every source (isolated) and merge contributions into Repo objects.
    Returns (repos, errors) — errors is how many sources raised, so the caller can
    tell a genuinely quiet day from a total outage."""
    repos = {}
    errors = 0
    for label, fn in SOURCES:
        try:
            result = fn() or {}
        except Exception as e:  # noqa: BLE001 — one bad source must not sink the rest
            print(f"  ! source {label} crashed: {e}", file=sys.stderr)
            result = {}
            errors += 1
        print(f"  {label}: {len(result)} repos", file=sys.stderr)
        for full, attrs in result.items():
            r = repos.get(full) or repos.setdefault(full, Repo(full_name=full))
            r.sources.append(label)
            r.merge(attrs)
    return repos, errors


def qualify(repos, seen):
    """Filter, enrich, classify, and rank all repos worthy of delivery.

    This intentionally does not truncate. Separating qualification from delivery
    policy makes it possible to audit how many important items a cap would omit.
    """
    cutoff = time.time() - config.SEEN_TTL_DAYS * 86400
    out = []
    for full, r in repos.items():
        if SKIP_NAME_RE.search(full) or seen.get(full, 0) > cutoff:
            continue
        # Most of the broad candidate pool can be rejected from source signals
        # alone (GitHub's new-repo search already supplies total stars). This
        # turns ~200 serial GitHub lookups into only the handful that can pass
        # and avoids spending rate limit or runtime on items that can never be
        # delivered.
        pre_decision = classify_importance(r)
        if not pre_decision:
            continue
        if not enrich(r) or r.stars < config.MIN_STARS or is_evergreen_noise(r):
            continue
        if not r.url:
            r.url = f"https://github.com/{full}"
        decision = classify_importance(r)
        if not decision:
            continue
        r.importance_tier = decision.tier
        r.important_because = list(decision.reasons)
        r.score = score(r)
        out.append(r)
    out.sort(key=lambda r: r.score, reverse=True)
    return out


def choose(qualified):
    """Adaptive delivery policy: Tier A expands; Tier B only fills to target."""
    tier_a = sorted((r for r in qualified if r.importance_tier == "A"),
                    key=attrgetter("score"), reverse=True)
    tier_b = sorted((r for r in qualified if r.importance_tier == "B"),
                    key=attrgetter("score"), reverse=True)
    selected = tier_a[:config.SAFETY_CAP]
    if len(selected) < config.TARGET_ITEMS:
        room = min(config.TARGET_ITEMS - len(selected),
                   config.SAFETY_CAP - len(selected))
        selected.extend(tier_b[:room])
    return selected


def select(repos, seen):
    """Compatibility wrapper for the full qualification + delivery policy."""
    return choose(qualify(repos, seen))


def radar_day(now=None):
    """Calendar day for the reader, independent of the CI runner's UTC clock."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(ZoneInfo(config.TIMEZONE)).strftime("%Y-%m-%d")


def main():
    when = radar_day()
    # Multi-window cron fires several times a day so a dropped/delayed fire still
    # lands one run. Only the first fire of the day does the work; the rest no-op.
    if already_ran_today(when):
        print(f"gh-radar: already ran today ({when}) — skipping this window.",
              file=sys.stderr)
        return
    print("gh-radar: collecting…", file=sys.stderr)
    repos, errors = collect()
    seen = load_seen()
    qualified = qualify(repos, seen)
    top = choose(qualified)
    qa = sum(r.importance_tier == "A" for r in qualified)
    qb = sum(r.importance_tier == "B" for r in qualified)
    sa = sum(r.importance_tier == "A" for r in top)
    sb = sum(r.importance_tier == "B" for r in top)
    print(f"  important: {qa} Tier A + {qb} Tier B qualified; "
          f"selected {sa} Tier A + {sb} Tier B from {len(repos)} repos",
          file=sys.stderr)
    if not top:
        # No NEW repos. Two very different reasons look identical here, so split them:
        if not repos:
            # Nothing collected from ANY source — an outage, not a quiet day. Fail
            # loudly (red job -> real failure alert) rather than reassure with a
            # false heartbeat.
            raise RuntimeError(
                f"no repos collected from any source ({errors}/{len(SOURCES)} "
                f"crashed) — aborting instead of sending a false 'nothing new'")
        # A quiet day must stay quiet. "Nothing new" heartbeat emails were still
        # pushes and undermined the promise that every notification is important.
        print("  no important new repos today — no email sent.", file=sys.stderr)
        mark_ran_today(when)
        return

    summarize_zh(top)                                  # best-effort zh blurbs
    md = render_md(top, when)

    out_dir = os.environ.get("GH_RADAR_DIGEST_DIR") or os.environ.get("GH_RADAR_VAULT")
    if out_dir:
        path = Path(out_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / f"github-radar-{when}.md").write_text(md)
        print(f"  ✓ wrote {path / f'github-radar-{when}.md'}", file=sys.stderr)

    subject_mix = []
    if sa:
        subject_mix.append(f"{sa} must-see")
    if sb:
        subject_mix.append(f"{sb} notable")
    send_email(f"GitHub Radar — {when} ({' + '.join(subject_mix)})", md)

    now = time.time()
    for r in top:
        seen[r.full_name] = now
    save_seen(seen)
    mark_ran_today(when)                   # later windows today will no-op
