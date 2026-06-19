# gh-radar

**A daily email of the GitHub tools people are actually sharing — without touching the X API.**

You saw `mempalace` on X and thought *"how did I not know about this?"*. gh-radar
is the cron job that makes sure you find the next one. Every morning it pulls
the tools that are trending and being discussed, dedupes them, drops the ones
you've already seen, and emails you a ranked digest.

It reads the places tools surface, across many angles. The first four sources
are free and need no keys; the last two are optional and self-disable until you
add a key:

| Source | Signal | How | Key |
|---|---|---|---|
| GitHub Trending | star velocity — daily + **weekly** + per-language | public HTML | — |
| Hacker News | what devs are discussing now | Algolia API | — |
| GitHub Search | brand-new repos gaining stars | official API | — |
| Lobsters | curated programming community | hottest.json | — |
| Reddit | r/commandline, r/selfhosted, … | OAuth API | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` |
| X / Twitter | tools shared by curated accounts | [twitterapi.io](https://twitterapi.io) | `TWITTERAPI_IO_KEY` |

The X layer is the only one that catches an *already-popular* tool being
**re-shared** (the "I saw it on X" case). The weekly Trending window catches
tools that stay hot all week, not just a one-day spike.

Each repo is scored (HN/X discussion weighted highest, novelty bonus, multi-source
bonus), and a 14-day memory stops the same repo showing up every day. Any single
source can fail or be disabled without affecting the rest.

## Run it on GitHub Actions (recommended — laptop can be off)

The included workflow (`.github/workflows/radar.yml`) runs daily at 08:00 Taipei
on GitHub's servers, emails you the digest, commits a browsable copy to
`digests/`, and persists the de-dup memory in `state/`.

Setup — **Repo → Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `GMAIL_USER` | your gmail address |
| `GMAIL_APP_PASSWORD` | a [Gmail App Password](https://myaccount.google.com/apppasswords) (needs 2FA) |

`GITHUB_TOKEN` is injected automatically (lifts the API limit to 5000/hr). Trigger
a run any time from the **Actions** tab → *gh-radar* → *Run workflow*.

## Run it locally instead

```bash
cd gh-radar
cp config.example.env config.env   # then fill in SMTP_PASS (Gmail App Password)
./run.sh                           # run once, prints to stdout if SMTP unset
./install.sh 8                     # schedule daily at 08:00 via cron
```

Zero pip dependencies — Python 3.9+ standard library only.

## Sample output

```
gh-radar: collecting…
  trending: 16 repos
  hacker news: 95 repos
  new repos: 30 repos
  ✓ emailed digest to waynehacking8@users.noreply.github.com
```

```markdown
# GitHub Radar — 2026-06-19

### 1. [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)
⭐ 7,449 · 🔥 2322/day · 💬 HN 2 · C
> High-performance code intelligence MCP server. Indexes codebases into a
> persistent knowledge graph. 158 languages, sub-ms queries, 99% fewer tokens.
[HN discussion](https://news.ycombinator.com/item?id=48596084)

### 2. [obra/superpowers](https://github.com/obra/superpowers)
⭐ 232,851 · 🔥 1429/day · Shell
> An agentic skills framework & software development methodology that works.
```

## Config

All via `config.env` (see `config.example.env`):

- `GITHUB_TOKEN` — optional read-only token; lifts API limit 60→5000/hr.
- `SMTP_*` / `EMAIL_TO` — Gmail App Password delivery.
- `MIN_STARS` (30), `SEEN_TTL_DAYS` (14) — tuning.
- `GH_RADAR_VAULT` — optional: also save each digest as an Obsidian note.

## Honest limitations

- **Not X.** If a tool is shared on X but never hits Trending, HN, or gains
  stars quickly, gh-radar won't see it. In practice the overlap is high — most
  genuinely useful tools surface in at least one of these. X can be bolted on
  later as an optional source if you decide it's worth the cost/fragility.
- **GitHub Trending has no official API**, so that one source is an HTML scrape
  and can break if GitHub redesigns the page. The other two sources are real
  APIs and will keep the digest alive if it does.
- **Heuristic "tool" filter.** It skips obvious non-tools (awesome-lists,
  tutorials, books) by name, but a course or spec repo can still slip through.
- **English/global HN bias.** HN skews to English-speaking dev discussion.

## How scoring works

```
score = stars_today
      + 2 × hn_points         # discussion is the strongest "people care" signal
      + 40 if brand-new repo  # novelty — the whole point is finding new things
      + 0.01 × min(stars, 5000)
      + 15 × (number of sources it appeared in)
```

Top 20 by score go in the digest.
