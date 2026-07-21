import unittest

from gh_radar.models import Repo
from gh_radar.render import render_md


class RenderTests(unittest.TestCase):
    def test_alert_explains_why_each_repo_was_sent(self):
        repo = Repo(
            "owner/project",
            sources=["trending"],
            stars=1234,
            stars_today=400,
            trending_rank=1,
            url="https://github.com/owner/project",
            importance_tier="A",
            important_because=["GitHub Trending #1", "400 stars/day"],
        )
        md = render_md([repo], "2026-07-21")
        self.assertIn("_1 important repo: 1 must-see", md)
        self.assertIn("🎯 Tier A · Must-see: GitHub Trending #1 · 400 stars/day", md)

    def test_tier_b_only_alert_does_not_claim_zero_must_see(self):
        repo = Repo(
            "owner/notable",
            sources=["hn"],
            stars=500,
            hn_points=120,
            url="https://github.com/owner/notable",
            importance_tier="B",
            important_because=["120 HN points"],
        )
        md = render_md([repo], "2026-07-21")
        self.assertIn("_1 important repo: 1 notable", md)
        self.assertNotIn("0 must-see", md)
        self.assertIn("🎯 Tier B · Notable: 120 HN points", md)


if __name__ == "__main__":
    unittest.main()
