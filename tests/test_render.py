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
            important_because=["GitHub Trending #1", "400 stars/day"],
        )
        md = render_md([repo], "2026-07-21")
        self.assertIn("_1 important repo surfaced", md)
        self.assertIn("🎯 Why now: GitHub Trending #1 · 400 stars/day", md)


if __name__ == "__main__":
    unittest.main()
