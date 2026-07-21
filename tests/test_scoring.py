import unittest

from gh_radar.models import Repo
from gh_radar.scoring import (
    classify_importance,
    importance_reasons,
    is_evergreen_noise,
    score,
)


class ImportanceGateTests(unittest.TestCase):
    def repo(self, **attrs):
        r = Repo("owner/repo")
        for name, value in attrs.items():
            setattr(r, name, value)
        return r

    def test_global_trending_leader_is_important(self):
        r = self.repo(sources=["trending"], trending_rank=1, stars_today=12)
        decision = classify_importance(r)
        self.assertEqual(decision.tier, "A")
        self.assertIn("GitHub Trending #1", decision.reasons)

    def test_strong_velocity_is_tier_b(self):
        r = self.repo(sources=["trending"], stars_today=250)
        decision = classify_importance(r)
        self.assertEqual(decision.tier, "B")
        self.assertIn("250 stars/day", decision.reasons)

    def test_exceptional_velocity_is_tier_a(self):
        r = self.repo(sources=["trending"], stars_today=500)
        decision = classify_importance(r)
        self.assertEqual(decision.tier, "A")
        self.assertIn("500 stars/day", decision.reasons)

    def test_strong_discussion_is_tier_b(self):
        r = self.repo(sources=["hn"], hn_points=100)
        self.assertEqual(classify_importance(r).tier, "B")

    def test_exceptional_discussion_is_tier_a(self):
        r = self.repo(sources=["hn"], hn_points=200)
        self.assertEqual(classify_importance(r).tier, "A")

    def test_breakout_new_repo_is_tier_b(self):
        r = self.repo(sources=["new"], new_repo=True, stars=1000)
        self.assertEqual(classify_importance(r).tier, "B")

    def test_exceptional_new_repo_is_tier_a(self):
        r = self.repo(sources=["new"], new_repo=True, stars=2000)
        self.assertEqual(classify_importance(r).tier, "A")

    def test_two_independent_sources_promote_moderate_signal(self):
        r = self.repo(sources=["trending", "hn"], stars_today=50, hn_points=30)
        decision = classify_importance(r)
        self.assertEqual(decision.tier, "A")
        self.assertIn("GitHub (50 stars/day)", decision.reasons[0])
        self.assertIn("Hacker News (30 points)", decision.reasons[0])

    def test_second_source_must_have_its_own_moderate_signal(self):
        r = self.repo(sources=["trending", "hn"], stars_today=50, hn_points=2)
        self.assertIsNone(classify_importance(r))

    def test_github_search_and_trending_are_not_independent(self):
        r = self.repo(sources=["trending", "new"], stars_today=50,
                      new_repo=True, stars=500)
        self.assertIsNone(classify_importance(r))

    def test_weak_single_source_and_web_listicle_are_not_important(self):
        weak = self.repo(sources=["trending"], stars_today=49)
        web = self.repo(sources=["web"], stars=5000)
        self.assertIsNone(classify_importance(weak))
        self.assertIsNone(classify_importance(web))

    def test_compatibility_reason_helper_matches_decision(self):
        r = self.repo(sources=["trending"], stars_today=250)
        self.assertEqual(importance_reasons(r), ["250 stars/day"])

    def test_other_single_source_tier_boundaries(self):
        cases = [
            ("x_likes", 100, 300),
            ("reddit_points", 300, 750),
            ("lobsters_score", 50, 100),
        ]
        for field, notable, must_send in cases:
            with self.subTest(field=field, tier="B"):
                self.assertEqual(classify_importance(self.repo(**{field: notable})).tier, "B")
            with self.subTest(field=field, tier="A"):
                self.assertEqual(classify_importance(self.repo(**{field: must_send})).tier, "A")

    def test_old_large_repo_requires_a_strong_current_signal(self):
        passive = self.repo(sources=["trending"], stars=231_555,
                            stars_today=249)
        surging = self.repo(sources=["trending"], stars=231_555,
                            stars_today=250)
        self.assertTrue(is_evergreen_noise(passive))
        self.assertFalse(is_evergreen_noise(surging))
        self.assertIsNone(classify_importance(passive))
        self.assertEqual(classify_importance(surging).tier, "B")

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
