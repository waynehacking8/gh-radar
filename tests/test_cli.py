import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from gh_radar.cli import choose, main, radar_day, select
from gh_radar.models import Repo


class SelectionTests(unittest.TestCase):
    def ranked(self, tier, count, start=1000):
        return [Repo(f"owner/{tier.lower()}-{i}", importance_tier=tier,
                     score=start - i) for i in range(count)]

    def test_radar_day_uses_reader_timezone_not_runner_utc(self):
        before_midnight_utc = datetime(2026, 7, 20, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(radar_day(before_midnight_utc), "2026-07-21")

    @patch("gh_radar.cli.enrich", return_value=True)
    def test_select_drops_weak_repo_and_keeps_important_repo(self, _enrich):
        weak = Repo("owner/weak", sources=["trending"], stars=500, stars_today=20)
        strong = Repo("owner/strong", sources=["trending"], stars=500,
                      trending_rank=1, stars_today=20)
        selected = select({weak.full_name: weak, strong.full_name: strong}, {})
        self.assertEqual([r.full_name for r in selected], ["owner/strong"])
        self.assertEqual(strong.importance_tier, "A")
        self.assertEqual(strong.important_because, ["GitHub Trending #1"])
        _enrich.assert_called_once_with(strong)

    @patch("gh_radar.cli.config.TARGET_ITEMS", 5)
    @patch("gh_radar.cli.config.SAFETY_CAP", 10)
    def test_all_tier_a_expand_beyond_normal_target(self):
        selected = choose(self.ranked("A", 8))
        self.assertEqual(len(selected), 8)
        self.assertTrue(all(r.importance_tier == "A" for r in selected))

    @patch("gh_radar.cli.config.TARGET_ITEMS", 5)
    @patch("gh_radar.cli.config.SAFETY_CAP", 10)
    def test_tier_a_has_a_ten_item_safety_cap(self):
        selected = choose(self.ranked("A", 12))
        self.assertEqual(len(selected), 10)

    @patch("gh_radar.cli.config.TARGET_ITEMS", 5)
    @patch("gh_radar.cli.config.SAFETY_CAP", 10)
    def test_tier_b_only_fills_empty_target_slots(self):
        qualified = self.ranked("A", 3, 2000) + self.ranked("B", 8, 1000)
        selected = choose(qualified)
        self.assertEqual([r.importance_tier for r in selected], ["A", "A", "A", "B", "B"])

    @patch("gh_radar.cli.config.TARGET_ITEMS", 5)
    @patch("gh_radar.cli.config.SAFETY_CAP", 10)
    def test_tier_b_never_pads_a_six_item_tier_a_alert(self):
        qualified = self.ranked("A", 6, 2000) + self.ranked("B", 8, 1000)
        selected = choose(qualified)
        self.assertEqual(len(selected), 6)
        self.assertTrue(all(r.importance_tier == "A" for r in selected))

    @patch("gh_radar.cli.config.TARGET_ITEMS", 5)
    @patch("gh_radar.cli.config.SAFETY_CAP", 10)
    def test_tier_b_is_capped_at_normal_target_without_tier_a(self):
        selected = choose(self.ranked("B", 8))
        self.assertEqual(len(selected), 5)

    @patch("gh_radar.cli.config.TARGET_ITEMS", 2)
    @patch("gh_radar.cli.config.SAFETY_CAP", 10)
    def test_each_tier_is_sorted_by_score_before_selection(self):
        low = Repo("owner/low", importance_tier="B", score=1)
        high = Repo("owner/high", importance_tier="B", score=10)
        middle = Repo("owner/middle", importance_tier="B", score=5)
        selected = choose([low, high, middle])
        self.assertEqual([r.full_name for r in selected], ["owner/high", "owner/middle"])

    @patch("gh_radar.cli.enrich", return_value=True)
    @patch("gh_radar.cli.time.time", return_value=10_000_000)
    def test_recently_sent_repo_is_not_recycled(self, _time, _enrich):
        repo = Repo("owner/repeat", sources=["trending"], stars=1000,
                    trending_rank=1)
        selected = select({repo.full_name: repo}, {repo.full_name: 9_999_999})
        self.assertEqual(selected, [])
        _enrich.assert_not_called()

    @patch("gh_radar.cli.mark_ran_today")
    @patch("gh_radar.cli.send_email")
    @patch("gh_radar.cli.qualify", return_value=[])
    @patch("gh_radar.cli.load_seen", return_value={})
    @patch("gh_radar.cli.collect")
    @patch("gh_radar.cli.already_ran_today", return_value=False)
    def test_quiet_day_sends_no_email(self, _ran, collect, _seen, _qualify,
                                      send_email, mark_ran):
        collect.return_value = ({"owner/weak": Repo("owner/weak")}, 0)
        main()
        send_email.assert_not_called()
        mark_ran.assert_called_once()


if __name__ == "__main__":
    unittest.main()
