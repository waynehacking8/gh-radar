# gh-radar

**A daily email of the GitHub tools people are actually sharing — without touching the X API.**

You saw `mempalace` on X and thought *"how did I not know about this?"*. gh-radar
is the cron job that makes sure you find the next one. Every morning it pulls
the tools that are trending and being discussed, dedupes them, drops the ones
you've already seen, and emails you a ranked digest.

It reads the places tools surface, across many angles. Six of the seven sources
need **no API key at all**; only Reddit is opt-in. A Claude subscription (CLI or
token) adds the Chinese summaries and resolves Chinese-prose tweets — without it
the digest still ships in English.

| Source | Signal | How | Key |
|---|---|---|---|
| GitHub Trending | star velocity — daily + **weekly** + per-language | public HTML | — |
| Hacker News | what devs are discussing now | Algolia API | — |
| GitHub Search | brand-new repos gaining stars | official API | — |
| Lobsters | curated programming community | hottest.json | — |
| X / Twitter | tools shared by curated accounts | [Firecrawl](https://firecrawl.dev) scrape (free, keyless) | — |
| web articles | tool round-up listicles | Firecrawl search + scrape | — |
| Reddit | r/commandline, r/selfhosted, … | OAuth API | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` |

The X layer is the one that catches an *already-popular* tool being **re-shared**
(the "I saw it on X" case). Chinese tool accounts rarely link GitHub directly —
they describe the tool in prose — so the LLM extracts the tool name and a GitHub
search, disambiguated by the star count mentioned in the post, resolves the real
repo (e.g. "记忆宫殿 55K star" → `MemPalace/mempalace`). A free `FIRECRAWL_API_KEY`
raises rate limits if the keyless tier starts returning 429s.

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
  trending: 120 repos
  hn: 91 repos
  new: 30 repos
  lobsters: 1 repos
  x: 3 repos
  ✓ X: 3 repo(s) resolved from prose tweets
  web: 12 repos
  ✓ Chinese summaries: 50/50
  ✓ emailed digest to you@example.com
```

```markdown
### 1. [MemPalace/mempalace](https://github.com/MemPalace/mempalace)
⭐ 55,992 · 𝕏 @axichuhai

> 將 AI 長期記憶從摘要快取改造成可翻閱的檔案空間，本地運行、近乎零成本。
> _A memory palace for AI agents — a browsable archive replacing summary caches._

📍 出處 / via: Firecrawl → X @axichuhai

[X post](https://x.com/axichuhai/status/...)
```

## Config

All via env (see `config.example.env`):

- `GITHUB_TOKEN` — recommended: lifts API limit 60→5000/hr. Without it, enrich
  rate-limits and only the Trending source survives.
- `FIRECRAWL_API_KEY` — optional: lifts Firecrawl's keyless 429 cap (X + web).
- `CLAUDE_CODE_OAUTH_TOKEN` — optional: enables Chinese summaries + X-prose resolution.
- `SMTP_*` / `EMAIL_TO` — Gmail App Password delivery (EMAIL_TO falls back to SMTP_USER).
- `MIN_STARS` (30), `SEEN_TTL_DAYS` (14), `GH_RADAR_MAX_ITEMS` (50),
  `GH_RADAR_EVERGREEN_STARS` (50000) — tuning.
- `GH_RADAR_X_ACCOUNTS`, `GH_RADAR_SUBREDDITS`, `GH_RADAR_TREND_LANGS`,
  `GH_RADAR_FC_QUERIES` — what each source watches.
- `GH_RADAR_VAULT` / `GH_RADAR_DIGEST_DIR` — also save each digest as Markdown.

## Project layout

A single `radar.py` shim (keeps `python radar.py` working) over the `gh_radar/`
package:

```
gh_radar/
  config.py     constants, scoring weights (config.W), env helpers
  models.py     the Repo dataclass — typed core model (merge() rejects unknown keys)
  clients.py    github / firecrawl / claude / http — every call degrades to None
  sources.py    one src_*() per signal; SOURCES table; enrich()
  scoring.py    score() + evergreen-noise filter
  state.py      de-dup memory (seen.json), atomic writes
  render.py     zh summaries, Markdown digest, HTML
  email_out.py  SMTP delivery
  cli.py        collect → select → render → email → remember
```

Standard library only — zero pip dependencies.

## Honest limitations

- **GitHub Trending has no official API**, so that source is an HTML scrape that
  can break on a redesign. The other six keep the digest alive if it does.
- **No `GITHUB_TOKEN` = trending-only.** Without a token the GitHub API rate-limits
  and every non-trending repo is dropped at the enrich step. CI injects one.
- **X prose resolution needs Claude.** Without the CLI/token, X keeps only tweets
  that link a repo directly; Chinese-prose tools are skipped (graceful).
- **Web articles can over-list.** A "best tools" listicle may surface a famous
  giant; the evergreen filter drops web-only repos ≥50k stars, but precision here
  is lower than the velocity sources.

## How scoring works (`config.W`)

```
score = stars_today                       # trending velocity
      + 2 × hn_points                     # discussion = strong "people care" signal
      + 120 if shared on a curated X acct # a human you follow chose it — strongest
      + 15 × min(x_mentions, 5)
      + 0.02 × min(reddit_points, 1000)
      + 0.3 × min(lobsters_score, 200)
      + 25 if surfaced in a web article
      + 40 if brand-new repo              # novelty
      + 0.01 × min(stars, 5000)           # mild popularity tiebreak
      + 15 × (number of sources)          # multi-source = stronger signal
```

Top 50 by score go in the digest; a 14-day memory stops repeats.
