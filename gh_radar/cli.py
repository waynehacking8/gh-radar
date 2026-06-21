"""Pipeline: collect from every source -> merge into Repos -> select/rank -> render
-> email -> remember. Each stage is a small function so the flow reads top-down."""
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from . import config
from .email_out import send_email
from .models import Repo
from .render import render_md, summarize_zh
from .scoring import is_evergreen_noise, score
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


def select(repos, seen):
    """Filter (skip-list, already-seen, dead/fork, too-small, evergreen noise),
    enrich, score, and return the top N."""
    cutoff = time.time() - config.SEEN_TTL_DAYS * 86400
    out = []
    for full, r in repos.items():
        if SKIP_NAME_RE.search(full) or seen.get(full, 0) > cutoff:
            continue
        if not enrich(r) or r.stars < config.MIN_STARS or is_evergreen_noise(r):
            continue
        if not r.url:
            r.url = f"https://github.com/{full}"
        r.score = score(r)
        out.append(r)
    out.sort(key=lambda r: r.score, reverse=True)
    return out[:config.MAX_ITEMS]


def main():
    when = datetime.now().strftime("%Y-%m-%d")
    # Multi-window cron fires several times a day so a dropped/delayed fire still
    # lands one run. Only the first fire of the day does the work; the rest no-op.
    if already_ran_today(when):
        print(f"gh-radar: already ran today ({when}) — skipping this window.",
              file=sys.stderr)
        return
    print("gh-radar: collecting…", file=sys.stderr)
    repos, errors = collect()
    seen = load_seen()
    top = select(repos, seen)
    if not top:
        # No NEW repos. Two very different reasons look identical here, so split them:
        if not repos:
            # Nothing collected from ANY source — an outage, not a quiet day. Fail
            # loudly (red job -> real failure alert) rather than reassure with a
            # false heartbeat.
            raise RuntimeError(
                f"no repos collected from any source ({errors}/{len(SOURCES)} "
                f"crashed) — aborting instead of sending a false 'nothing new'")
        # Genuinely nothing new (all already seen / below threshold). Heartbeat so a
        # quiet day is visibly "ran, nothing new" and not mistaken for a broken run.
        print("  nothing new today.", file=sys.stderr)
        send_email(f"GitHub Radar — {when}（今天沒有新工具）",
                   f"# GitHub Radar — {when}\n\n"
                   "_雷達今天掃過所有來源，沒有發現新的 repo——可能都看過了，或都未達門檻。"
                   "系統運作正常，明天見。_\n")
        mark_ran_today(when)               # quiet day still counts as "ran today"
        return

    summarize_zh(top)                                  # best-effort zh blurbs
    md = render_md(top, when)

    out_dir = os.environ.get("GH_RADAR_DIGEST_DIR") or os.environ.get("GH_RADAR_VAULT")
    if out_dir:
        path = Path(out_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / f"github-radar-{when}.md").write_text(md)
        print(f"  ✓ wrote {path / f'github-radar-{when}.md'}", file=sys.stderr)

    send_email(f"GitHub Radar — {when} ({len(top)} tools)", md)

    now = time.time()
    for r in top:
        seen[r.full_name] = now
    save_seen(seen)
    mark_ran_today(when)                   # later windows today will no-op
