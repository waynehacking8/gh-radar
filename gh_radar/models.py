"""The core data model. One typed Repo replaces the old untyped dict bag, so a
mistyped field fails loudly and the available signals are self-documenting."""
from dataclasses import dataclass, field


@dataclass
class Repo:
    full_name: str
    sources: list = field(default_factory=list)        # e.g. ["trending", "hn"]

    # --- per-source signals ---
    stars_today: int = 0                               # trending velocity
    trending_rank: int = 0                             # global daily page only
    hn_points: int = 0
    hn_url: str = ""
    new_repo: bool = False
    lobsters_score: int = 0
    lobsters_url: str = ""
    reddit_points: int = 0
    reddit_url: str = ""
    reddit_sub: str = ""
    x_mentions: int = 0
    x_by: list = field(default_factory=list)
    x_url: str = ""
    x_likes: int = 0
    context: str = ""                                  # sharer's own framing (X post / title)

    # --- enriched from the GitHub repo API ---
    stars: int = 0
    desc: str = ""
    lang: str = ""
    url: str = ""

    # --- derived ---
    zh: str = ""                                       # Traditional-Chinese summary
    score: float = 0.0
    important_because: list = field(default_factory=list)

    def merge(self, attrs):
        """Apply a source's contribution (its dict of field -> value)."""
        for k, v in attrs.items():
            setattr(self, k, v)
