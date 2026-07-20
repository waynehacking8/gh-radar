import unittest

from gh_radar.models import Repo
from gh_radar.scoring import importance_reasons, score


class ImportanceGateTests(unittest.TestCase):
    def repo(self, **attrs):
        r = Repo("owner/repo")
        for name, value in attrs.items():
            setattr(r, name, value)
        return r

    def test_global_trending_leader_is_important(self):
        r = self.repo(sources=["trending"], trending_rank=1, stars_today=12)
        self.assertIn("GitHub Trending #1", importance_reasons(r))

    def test_exceptional_velocity_is_important_without_global_rank(self):
        r = self.repo(sources=["trending"], stars_today=250)
        self.assertIn("250 stars/day", importance_reasons(r))

    def test_strong_discussion_is_important(self):
        r = self.repo(sources=["hn"], hn_points=100)
        self.assertIn("100 HN points", importance_reasons(r))

    def test_breakout_new_repo_is_important(self):
        r = self.repo(sources=["new"], new_repo=True, stars=1000)
        self.assertIn("new repo already at 1,000 stars", importance_reasons(r))

    def test_two_independent_sources_promote_moderate_signal(self):
        r = self.repo(sources=["trending", "hn"], stars_today=50, hn_points=2)
        self.assertEqual(
            importance_reasons(r),
            ["corroborated by GitHub + Hacker News"],
        )

    def test_github_search_and_trending_are_not_independent(self):
        r = self.repo(sources=["trending", "new"], stars_today=50)
        self.assertEqual(importance_reasons(r), [])

    def test_weak_single_source_and_web_listicle_are_not_important(self):
        weak = self.repo(sources=["trending"], stars_today=49)
        web = self.repo(sources=["web"], stars=5000)
        self.assertEqual(importance_reasons(weak), [])
        self.assertEqual(importance_reasons(web), [])

    def test_global_rank_affects_order_after_gate(self):
        first = self.repo(sources=["trending"], trending_rank=1, stars=100)
        third = self.repo(sources=["trending"], trending_rank=3, stars=100)
        self.assertGreater(score(first), score(third))

    def test_rank_outside_global_gate_gets_no_rank_bonus(self):
        unranked = self.repo(sources=["trending"], stars=100)
        fourth = self.repo(sources=["trending"], trending_rank=4, stars=100)
        self.assertEqual(score(unranked), score(fourth))


if __name__ == "__main__":
    unittest.main()
