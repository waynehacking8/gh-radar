"""Presentation: derive the Chinese summaries, build the Markdown digest (with a
per-repo provenance line), and convert it to email-safe HTML."""
import json
import re
import sys
from html import escape as html_escape

from . import config
from .clients import claude_json

SOURCE_NAMES = {"trending": "Trending", "hn": "Hacker News", "new": "new repos",
                "lobsters": "Lobsters", "reddit": "Reddit", "x": "X", "web": "web articles"}


_ZH_PROMPT = (
    "You are writing a daily digest of trending GitHub tools for a developer. "
    "Each item has the repo `name`, its official GitHub description `en`, and "
    "`context` — the words a real person used when sharing it (an X post or a "
    "forum title; may be empty). For EACH repo, write a Traditional Chinese "
    "(繁體中文，台灣用語) blurb of 2–3 sentences (約 60–110 字) that sets the scene: "
    "what the tool is, the concrete problem or scenario it fits, and why it is "
    "drawing attention. When `context` is present, take your angle and tone from "
    "it (echo the situation the sharer described). Ground every claim in "
    "name/en/context — do NOT invent features, numbers, or benchmarks that aren't "
    "supported. No marketing fluff, no emoji, no hashtags. "
    "Return ONLY a JSON object mapping each exact `name` to its Chinese string. "
    "No markdown fences, no commentary.\n\nRepos:\n")


def summarize_zh(repos):
    """Best-effort: add a vivid Traditional-Chinese blurb to each repo via claude,
    grounded in how a human framed it when sharing (X post / forum title) plus the
    official GitHub description. Done in small batches so one slow/failed call can't
    time out and drop every summary; each failed batch just falls back to English."""
    n = 0
    batch = max(1, config.SUMMARY_BATCH)
    for start in range(0, len(repos), batch):
        chunk = repos[start:start + batch]
        items = [{"name": r.full_name, "en": r.desc, "context": r.context} for r in chunk]
        mapping = claude_json(_ZH_PROMPT + json.dumps(items, ensure_ascii=False), want="object")
        if not isinstance(mapping, dict):
            continue                                      # this batch -> English; others still try
        for r in chunk:
            zh = mapping.get(r.full_name)
            if isinstance(zh, str) and zh.strip():
                r.zh = " ".join(zh.split())[:config.ZH_MAX]
                n += 1
    if n:
        print(f"  ✓ Chinese summaries: {n}/{len(repos)}", file=sys.stderr)
    else:
        print("  i Chinese summaries unavailable — using English only", file=sys.stderr)


def provenance(r):
    """Human-readable source attribution. Firecrawl-derived sources (X, web) are
    explicitly marked so the origin is always clear."""
    parts = []
    if "trending" in r.sources:
        parts.append("GitHub Trending")
    if "hn" in r.sources:
        parts.append("Hacker News")
    if "new" in r.sources:
        parts.append("GitHub new-repo search")
    if "lobsters" in r.sources:
        parts.append("Lobsters")
    if "reddit" in r.sources:
        parts.append(f"Reddit r/{r.reddit_sub}".rstrip("/ "))
    if "x" in r.sources:
        who = ", ".join("@" + h for h in r.x_by[:2])
        parts.append(f"Firecrawl → X {who}".strip())
    if "web" in r.sources:
        host = re.sub(r"^https?://(www\.)?", "", r.fc_url).split("/")[0]
        parts.append(f"Firecrawl → {host}" if host else "Firecrawl (web article)")
    return " · ".join(parts) or "unknown"


def _tags(r):
    tags = []
    if "trending" in r.sources:
        tags.append(f"🔥 {r.stars_today}/day")
    if "x" in r.sources:
        by = ", ".join("@" + h for h in r.x_by[:2])
        tags.append(f"𝕏 {by}" if by else "𝕏 shared")
    if "hn" in r.sources:
        tags.append(f"💬 HN {r.hn_points}")
    if "reddit" in r.sources:
        tags.append(f"👽 r/{r.reddit_sub} {r.reddit_points}")
    if "lobsters" in r.sources:
        tags.append(f"🦞 {r.lobsters_score}")
    if "web" in r.sources:
        tags.append("📰 web")
    if r.new_repo:
        tags.append("🆕 new")
    return " · ".join(tags)


def _refs(r):
    refs = []
    if r.x_url:
        refs.append(f"[X post]({r.x_url})")
    if r.hn_url:
        refs.append(f"[HN]({r.hn_url})")
    if r.reddit_url:
        refs.append(f"[Reddit]({r.reddit_url})")
    if r.lobsters_url:
        refs.append(f"[Lobsters]({r.lobsters_url})")
    if r.fc_url:
        refs.append(f"[article]({r.fc_url})")
    return refs


def render_md(repos, when):
    used = sorted({s for r in repos for s in r.sources})
    pretty = ", ".join(SOURCE_NAMES.get(s, s) for s in used)
    lines = [f"# GitHub Radar — {when}", "",
             f"_{len(repos)} new tools surfaced from {pretty}._", ""]
    for i, r in enumerate(repos, 1):
        lang = f" · {r.lang}" if r.lang else ""
        lines.append(f"### {i}. [{r.full_name}]({r.url})")
        lines.append(f"⭐ {r.stars:,} · {_tags(r)}{lang}")
        if r.zh:
            lines.append("")
            lines.append(f"> {r.zh}")
            if r.desc:
                lines.append(f"> _{r.desc}_")
        elif r.desc:
            lines.append("")
            lines.append(f"> {r.desc}")
        if r.context and "x" in r.sources:            # the sharer's own words — the scene
            q = r.context if len(r.context) <= config.QUOTE_MAX else r.context[:config.QUOTE_MAX - 1] + "…"
            who = ("@" + r.x_by[0]) if r.x_by else "X"
            lines.append("")
            lines.append(f"> 💬 {who}：「{q}」")
        lines.append("")
        lines.append(f"📍 出處 / via: {provenance(r)}")
        refs = _refs(r)
        if refs:
            lines.append("")
            lines.append(" · ".join(refs))
        lines.append("")
    return "\n".join(lines)


def _inline(s):
    """HTML-escape text, THEN convert our markdown links/italics, so a repo
    description containing <, >, & or quotes can't break the email."""
    s = html_escape(s, quote=True)
    s = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', s)
    # Italic only at word boundaries, so underscores *inside* a token — an @handle
    # like @unalome_sol or a snake_case name quoted from a tweet — are left intact.
    s = re.sub(r"(?<![A-Za-z0-9])_(\S(?:.*?\S)?)_(?![A-Za-z0-9])", r"<em>\1</em>", s)
    return s


def md_to_html(md):
    """Minimal Markdown -> HTML good enough for email clients."""
    out = []
    for line in md.split("\n"):
        if line.startswith("### "):
            out.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("# "):
            out.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("> "):
            out.append(f"<blockquote style='margin:4px 0;padding-left:10px;"
                       f"border-left:3px solid #ddd;color:#333'>{_inline(line[2:])}</blockquote>")
        elif line.strip() == "":
            out.append("<br>")
        else:
            out.append(f"<p style='margin:2px 0'>{_inline(line)}</p>")
    return ("<div style=\"font-family:-apple-system,Segoe UI,Roboto,sans-serif;"
            "max-width:680px;margin:auto;line-height:1.45\">" + "\n".join(out) + "</div>")
