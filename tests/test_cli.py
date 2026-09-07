import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from gh_radar import config
from gh_radar.cli import choose, main, radar_day, select
from gh_radar.email_out import send_email as actual_send_email
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


class MainFlowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        state_dir = Path(self.tempdir.name)
        self.seen_path = state_dir / "seen.json"
        self.last_run_path = state_dir / "last-run"
        self.summary_path = state_dir / "summary.md"
        self.seen_path.write_text('{"owner/old": 1}')
        self.last_run_path.write_text("2026-09-06")
        self.state_patch = patch.multiple(
            config,
            STATE_DIR=state_dir,
            SEEN_PATH=self.seen_path,
            LAST_RUN_PATH=self.last_run_path,
        )
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)
        self.env_patch = patch.dict(
            os.environ,
            {"GITHUB_STEP_SUMMARY": str(self.summary_path)},
            clear=True,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def flow_patches(self, qualified=None):
        repo = Repo("owner/new", importance_tier="A", score=10)
        return (
            patch("gh_radar.cli.radar_day", return_value="2026-09-07"),
            patch("gh_radar.cli.collect", return_value=({repo.full_name: repo}, 0)),
            patch("gh_radar.cli.qualify", return_value=[repo] if qualified is None else qualified),
            patch("gh_radar.cli.summarize_zh"),
            patch("gh_radar.cli.render_md", return_value="English digest"),
        )

    def test_missing_smtp_prints_english_fallback_but_does_not_update_state(self):
        with self.assertRaises(RuntimeError), \
             patch("gh_radar.cli.send_email", wraps=actual_send_email), \
             patch("sys.stdout") as stdout, \
             patch("sys.stderr") as stderr:
            patches = self.flow_patches()
            for item in patches:
                item.start()
            self.addCleanup(lambda: [item.stop() for item in patches])
            main()

        self.assertEqual(self.seen_path.read_text(), '{"owner/old": 1}')
        self.assertEqual(self.last_run_path.read_text(), "2026-09-06")
        self.assertIn("English digest", "".join(call.args[0] for call in stdout.write.call_args_list))
        self.assertIn("status=failure", "".join(call.args[0] for call in stderr.write.call_args_list))
        summary = self.summary_path.read_text()
        self.assertIn("`failure`", summary)
        self.assertNotIn("SMTP_PASS", summary)
        self.assertNotIn("@", summary)

    def test_smtp_exception_reports_failure_without_state_updates(self):
        smtp_env = {
            "SMTP_HOST": "smtp.example.invalid",
            "SMTP_USER": "user@example.com",
            "SMTP_PASS": "secret",
            "EMAIL_TO": "to@example.com",
        }
        with self.assertRaises(RuntimeError), \
             patch.dict(os.environ, smtp_env), \
             patch("gh_radar.cli.send_email", wraps=actual_send_email), \
             patch("gh_radar.email_out.smtplib.SMTP", side_effect=OSError("SMTP secret")), \
             patch("gh_radar.email_out.time.sleep"), \
             patch("sys.stderr"):
            patches = self.flow_patches()
            for item in patches:
                item.start()
            self.addCleanup(lambda: [item.stop() for item in patches])
            main()

        self.assertEqual(self.seen_path.read_text(), '{"owner/old": 1}')
        self.assertEqual(self.last_run_path.read_text(), "2026-09-06")
        summary = self.summary_path.read_text()
        self.assertIn("`failure`", summary)
        self.assertNotIn("SMTP secret", summary)

    def test_success_writes_seen_and_last_run_after_delivery(self):
        patches = self.flow_patches()
        for item in patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in patches])
        with patch("gh_radar.cli.send_email", return_value=True) as send_email:
            main()

        self.assertIn("owner/new", self.seen_path.read_text())
        self.assertEqual(self.last_run_path.read_text(), "2026-09-07")
        send_email.assert_called_once()
        self.assertIn("`sent`", self.summary_path.read_text())

    def test_already_completed_skips_collection_and_state(self):
        with patch("gh_radar.cli.radar_day", return_value="2026-09-06"), \
             patch("gh_radar.cli.already_ran_today", return_value=True), \
             patch("gh_radar.cli.collect") as collect, \
             patch("gh_radar.cli.send_email") as send_email, \
             patch("gh_radar.cli.save_seen") as save_seen, \
             patch("gh_radar.cli.mark_ran_today") as mark_ran:
            main()

        collect.assert_not_called()
        send_email.assert_not_called()
        save_seen.assert_not_called()
        mark_ran.assert_not_called()
        self.assertIn("`already_completed`", self.summary_path.read_text())

    def test_quiet_day_reports_no_new_without_sending(self):
        patches = self.flow_patches(qualified=[])
        for item in patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in patches])
        with patch("gh_radar.cli.send_email") as send_email:
            main()
        send_email.assert_not_called()
        self.assertEqual(self.seen_path.read_text(), '{"owner/old": 1}')
        self.assertEqual(self.last_run_path.read_text(), "2026-09-07")
        self.assertIn("`no_new`", self.summary_path.read_text())


if __name__ == "__main__":
    unittest.main()
