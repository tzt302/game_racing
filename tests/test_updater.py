import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updater import (
    AutoUpdater,
    UPDATE_HELPER_FLAG,
    run_update_helper,
    select_update,
    version_tuple,
)


class UpdaterTests(unittest.TestCase):
    def test_version_comparison_normalizes_release_tags(self):
        self.assertEqual(version_tuple("v2.4"), (2, 4, 0))
        self.assertEqual(version_tuple("2.4.2"), (2, 4, 2))
        self.assertIsNone(version_tuple("v2.4.2-beta"))

    def test_select_update_requires_exact_asset_and_digest(self):
        release = {
            "tag_name": "v2.4.2",
            "draft": False,
            "prerelease": False,
            "assets": [
                {
                    "name": "RacingLinePro-v2.4.2.exe",
                    "size": 123456,
                    "digest": "sha256:" + "a" * 64,
                    "browser_download_url": (
                        "https://github.com/tzt302/game_racing/releases/"
                        "download/v2.4.2/RacingLinePro-v2.4.2.exe"
                    ),
                }
            ],
        }
        update = select_update(release, "2.4.1")
        self.assertEqual(update["version"], "2.4.2")
        self.assertEqual(update["sha256"], "a" * 64)
        self.assertIsNone(select_update(release, "2.4.2"))

        release["assets"][0]["digest"] = None
        self.assertIsNone(select_update(release, "2.4.1"))

    def test_source_build_does_not_start_network_updater(self):
        updater = AutoUpdater("2.4.2", enabled=False)
        updater.start()
        self.assertEqual(updater.status_text, "")
        self.assertIsNone(updater._thread)

    def test_apply_update_launches_validated_exe_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "RacingLinePro.exe"
            staged = executable.with_suffix(".update.exe")
            staged.write_bytes(b"validated update")
            updater = AutoUpdater(
                "2.4.4",
                executable=executable,
                enabled=True,
            )
            updater.staged_path = staged
            with mock.patch("updater.subprocess.Popen") as popen:
                self.assertTrue(updater.apply_on_exit())
            command = popen.call_args.args[0]
            self.assertEqual(command[0], str(staged))
            self.assertEqual(command[1], UPDATE_HELPER_FLAG)
            self.assertNotIn("powershell", " ".join(command).lower())
            self.assertNotIn("cmd.exe", " ".join(command).lower())

    def test_update_helper_rejects_unrelated_source_path(self):
        with (
            mock.patch("updater.os.name", "nt"),
            mock.patch.object(sys, "frozen", True, create=True),
            mock.patch.object(
                sys,
                "executable",
                str(ROOT / "unrelated.exe"),
            ),
        ):
            result = run_update_helper(
                [
                    UPDATE_HELPER_FLAG,
                    str(ROOT / "RacingLinePro.exe"),
                    "1234",
                ]
            )
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
