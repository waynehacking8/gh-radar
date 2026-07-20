import unittest

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from gh_radar.sources import (_parse_trending, _recent_iso, _recent_unix,
                              _recent_x_status, SOURCES, src_github_new,
                              src_github_trending)


def article(owner, repo, stars, velocity):
    return f"""
    <article class="Box-row">
      <a href="/{owner}/{repo}/stargazers"> {stars:,} </a>
      <p class="col-9 color-fg-muted my-1 pr-4">Useful repo</p>
      <span>{velocity:,} stars today</span>
    </article>
    """


class TrendingParserTests(unittest.TestCase):
    def test_global_daily_page_records_rank_and_velocity(self):
        out = {}
        html = article("one", "first", 1200, 80) + article("two", "second", 900, 60)
        _parse_trending(html, out, global_scope=True)
        self.assertEqual(out["one/first"]["trending_rank"], 1)
        self.assertEqual(out["two/second"]["trending_rank"], 2)
        self.assertEqual(out["one/first"]["stars_today"], 80)

    def test_language_page_does_not_claim_global_rank(self):
        out = {}
        _parse_trending(article("one", "first", 1200, 80), out, global_scope=False)
        self.assertEqual(out["one/first"]["trending_rank"], 0)

    @patch("gh_radar.sources.TREND_LANGS", ["python"])
    @patch("gh_radar.sources.http_get", return_value="")
    def test_collector_fetches_daily_pages_only(self, get):
        src_github_trending()
        urls = [call.args[0] for call in get.call_args_list]
        self.assertEqual(urls, [
            "https://github.com/trending?since=daily",
            "https://github.com/trending/python?since=daily",
        ])
        self.assertFalse(any("weekly" in url for url in urls))

    def test_undated_web_listicle_source_is_removed(self):
        self.assertNotIn("web", [label for label, _fn in SOURCES])

    @patch("gh_radar.sources.gh_api")
    def test_new_repo_search_reuses_api_enrichment(self, api):
        api.return_value = {"items": [{
            "full_name": "new/breakout",
            "stargazers_count": 1234,
            "description": "Fresh tool",
            "language": "Rust",
            "html_url": "https://github.com/new/breakout",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }]}
        item = src_github_new()["new/breakout"]
        self.assertEqual(item["stars"], 1234)
        self.assertEqual(item["desc"], "Fresh tool")
        self.assertTrue(item["new_repo"])


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 21, 0, 0, tzinfo=timezone.utc)

    def x_url(self, created):
        epoch_ms = 1_288_834_974_657
        snowflake = (int(created.timestamp() * 1000) - epoch_ms) << 22
        return f"https://x.com/person/status/{snowflake}"

    def test_iso_freshness_rejects_old_or_unknown_items(self):
        recent = (self.now - timedelta(hours=2)).isoformat()
        old = (self.now - timedelta(days=4)).isoformat()
        self.assertTrue(_recent_iso(recent, max_age_hours=48, now=self.now))
        self.assertFalse(_recent_iso(old, max_age_hours=48, now=self.now))
        self.assertFalse(_recent_iso("", max_age_hours=48, now=self.now))

    def test_unix_freshness_rejects_old_or_missing_items(self):
        recent = (self.now - timedelta(hours=2)).timestamp()
        old = (self.now - timedelta(days=4)).timestamp()
        self.assertTrue(_recent_unix(recent, max_age_hours=48, now=self.now))
        self.assertFalse(_recent_unix(old, max_age_hours=48, now=self.now))
        self.assertFalse(_recent_unix(None, max_age_hours=48, now=self.now))

    def test_x_snowflake_freshness_rejects_pinned_old_posts(self):
        recent = self.x_url(self.now - timedelta(hours=2))
        old = self.x_url(self.now - timedelta(days=4))
        self.assertTrue(_recent_x_status(recent, max_age_hours=48, now=self.now))
        self.assertFalse(_recent_x_status(old, max_age_hours=48, now=self.now))


if __name__ == "__main__":
    unittest.main()
