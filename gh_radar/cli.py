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
from .state import load_seen, save_seen


def collect():
    """Run every source (isolated) and merge contributions into Repo objects."""
    repos = {}
    for label, fn in SOURCES:
        try:
            result = fn() or {}
        except Exception as e:  # noqa: BLE001 — one bad source must not sink the rest
            print(f"  ! source {label} crashed: {e}", file=sys.stderr)
            result = {}
        print(f"  {label}: {len(result)} repos", file=sys.stderr)
        for full, attrs in result.items():
            r = repos.get(full) or repos.setdefault(full, Repo(full_name=full))
            r.sources.append(label)
            r.merge(attrs)
    return repos


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
    print("gh-radar: collecting…", file=sys.stderr)
    repos = collect()
    seen = load_seen()
    top = select(repos, seen)
    if not top:
        print("  nothing new today.", file=sys.stderr)
        return

    summarize_zh(top)                                  # best-effort zh one-liners
    when = datetime.now().strftime("%Y-%m-%d")
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
