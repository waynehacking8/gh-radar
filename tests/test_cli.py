import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from gh_radar.cli import main, radar_day, select
from gh_radar.models import Repo


class SelectionTests(unittest.TestCase):
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
        self.assertEqual(strong.important_because, ["GitHub Trending #1"])
        _enrich.assert_called_once_with(strong)

    @patch("gh_radar.cli.config.MAX_ITEMS", 5)
    @patch("gh_radar.cli.enrich", return_value=True)
    def test_alert_has_a_hard_five_repo_cap(self, _enrich):
        repos = {}
        for i in range(8):
            r = Repo(f"owner/repo-{i}", sources=["trending"], stars=1000,
                     stars_today=1000 - i)
            repos[r.full_name] = r
        selected = select(repos, {})
        self.assertEqual(len(selected), 5)

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
    @patch("gh_radar.cli.select", return_value=[])
    @patch("gh_radar.cli.load_seen", return_value={})
    @patch("gh_radar.cli.collect")
    @patch("gh_radar.cli.already_ran_today", return_value=False)
    def test_quiet_day_sends_no_email(self, _ran, collect, _seen, _select,
                                      send_email, mark_ran):
        collect.return_value = ({"owner/weak": Repo("owner/weak")}, 0)
        main()
        send_email.assert_not_called()
        mark_ran.assert_called_once()


if __name__ == "__main__":
    unittest.main()
