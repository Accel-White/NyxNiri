"""Shared package adapter contracts: argv, failure propagation and probe scope."""

import contextlib
import io
import signal
import subprocess
import unittest
from unittest.mock import MagicMock, call, patch

from nyxniri import pkg
from nyxniri.pkg import cli
from nyxniri.pkg.detection import DependencyProbe
from tests.utils import TempEnv


class TestPackageAdapter(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    @staticmethod
    def _process(returncode=0, stdout="", stderr=""):
        process = MagicMock(pid=4321, returncode=returncode)
        process.communicate.return_value = (stdout, stderr)
        process.poll.return_value = returncode
        return process

    def test_install_command_shapes(self):
        cases = [
            ("pacman", "repo", ["sudo", "pacman", "-S", "--needed", "--noconfirm", "fish"]),
            ("paru", "aur", ["paru", "-S", "--needed", "--noconfirm", "fish"]),
            ("yay", "repo", ["yay", "-S", "--needed", "--noconfirm", "fish"]),
            ("shelly", "repo", ["shelly", "install", "standard", "--no-confirm", "fish"]),
            ("shelly", "aur", ["shelly", "install", "aur", "--no-confirm", "fish"]),
        ]
        for manager, source, expected in cases:
            with self.subTest(manager=manager, source=source), \
                 patch("nyxniri.pkg.subprocess.Popen", return_value=self._process()) as popen:
                self.assertTrue(pkg.install(["fish", "fish"], source=source, manager=manager))
                popen.assert_called_once_with(
                    expected,
                    stdout=None,
                    stderr=None,
                    text=True,
                    start_new_session=True,
                )

    def test_remove_and_upgrade_commands(self):
        self.assertEqual(pkg.command("remove", ["fish"], manager="pacman"), ["sudo", "pacman", "-Rns", "fish"])
        self.assertEqual(pkg.command("remove", ["fish"], manager="shelly"), ["shelly", "remove", "standard", "fish"])
        self.assertEqual(pkg.command("upgrade", manager="shelly"), ["shelly", "upgrade", "all"])
        self.assertEqual(pkg.command("upgrade", manager="yay"), ["yay", "-Syu"])
        with self.assertRaises(ValueError):
            pkg.command("install", ["aur-pkg"], source="aur", manager="pacman")

    def test_failure_and_timeout_are_not_success(self):
        for failure in (self._process(returncode=1), FileNotFoundError("missing")):
            with self.subTest(failure=failure), patch("nyxniri.pkg.subprocess.Popen") as popen:
                if isinstance(failure, OSError):
                    popen.side_effect = failure
                else:
                    popen.return_value = failure
                self.assertFalse(pkg.install(["fish"], manager="pacman"))

    def test_timeout_terminates_package_process_group(self):
        process = self._process()
        process.communicate.side_effect = [
            subprocess.TimeoutExpired(["sudo", "pacman"], 1800),
            ("", ""),
        ]
        with patch("nyxniri.pkg.subprocess.Popen", return_value=process) as popen, \
             patch("nyxniri.pkg.os.killpg") as killpg:
            result = pkg.run(["sudo", "pacman", "-S", "fish"])

        self.assertEqual(result.returncode, 124)
        popen.assert_called_once_with(
            ["sudo", "pacman", "-S", "fish"],
            stdout=None,
            stderr=None,
            text=True,
            start_new_session=True,
        )
        self.assertEqual(killpg.call_args_list, [
            call(process.pid, signal.SIGTERM),
            call(process.pid, signal.SIGKILL),
        ])

    def test_upgrade_cancellation_does_not_retry_with_another_manager(self):
        with patch("nyxniri.pkg.cli.preferred_manager", return_value="shelly"), \
             patch("nyxniri.pkg.subprocess.Popen", return_value=self._process(returncode=130)) as popen:
            self.assertEqual(cli.main(["upgrade"]), 130)
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(popen.call_args.args[0], ["shelly", "upgrade", "all"])

    def test_signal_exit_uses_shell_status(self):
        with patch("nyxniri.pkg.subprocess.Popen", return_value=self._process(returncode=-2)):
            self.assertEqual(pkg.run(["paru", "-Syu"]).returncode, 130)

    def test_flatpak_remote_failure_stops_install(self):
        with patch("shutil.which", return_value="/usr/bin/flatpak"), \
             patch("nyxniri.pkg.subprocess.Popen", return_value=self._process(returncode=1)) as popen:
            self.assertFalse(pkg.install_flatpaks(["com.qq.QQ"]))
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(popen.call_args.args[0], ["flatpak", "remote-add", "--system", "--if-not-exists", "flathub", pkg.FLATHUB_REMOTE_URL])

    def test_probe_caches_only_within_one_inspection(self):
        with patch("shutil.which", return_value="/usr/bin/pacman"), \
             patch("nyxniri.pkg.detection.timed_run", side_effect=[
                 subprocess.CompletedProcess([], 0, "old\n"),
                 subprocess.CompletedProcess([], 0, "old\nnew\n"),
             ]) as run:
            first = DependencyProbe()
            self.assertEqual(first.packages, {"old"})
            self.assertEqual(first.packages, {"old"})
            self.assertEqual(DependencyProbe().packages, {"old", "new"})
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args.args, (["pacman", "-Qq"], 30))

    def test_search_preserves_source_and_uses_bounded_query(self):
        with patch("nyxniri.pkg.cli.preferred_manager", return_value="paru"), \
             patch("nyxniri.pkg.subprocess.Popen", return_value=self._process(stdout="some-app\n")) as popen, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["search", "aur", "some"]), 0)
        self.assertEqual(output.getvalue(), "[AUR] some-app\n")
        self.assertEqual(popen.call_args.args[0], ["paru", "-Ssq", "--aur", "--", "some"])
        popen.return_value.communicate.assert_called_once_with(timeout=30)

    def test_installer_reports_failed_dependency_batch(self):
        from nyxniri.deps import install_selected_deps
        with patch("nyxniri.pkg.preferred_manager", return_value="pacman"), \
             patch("nyxniri.pkg.subprocess.Popen", return_value=self._process(returncode=7)) as popen, \
             patch("nyxniri.deps.check_mpvpaper_leak"):
            self.assertFalse(install_selected_deps(["fish"]))
        self.assertEqual(popen.call_args.args[0], ["sudo", "pacman", "-S", "--needed", "--noconfirm", "fish"])

    def test_shelly_search_decodes_structured_names(self):
        with patch("nyxniri.pkg.cli.preferred_manager", return_value="shelly"), \
             patch("nyxniri.pkg.subprocess.Popen", return_value=self._process(stdout='[{"Name":"sample-bin","Description":"Name is not a package"}]')) as popen, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["search", "aur sample"]), 0)
        self.assertEqual(output.getvalue(), "[AUR] sample-bin\n")
        self.assertEqual(popen.call_args.args[0], ["shelly", "search", "aur", "--json", "sample"])

    def test_block_page_is_not_a_package_list(self):
        with patch("nyxniri.pkg.cli.preferred_manager", return_value="shelly"), \
             patch("nyxniri.pkg.subprocess.Popen", return_value=self._process(stdout='<html>Blocked</html>')), \
             contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["search", "aur sample"]), 1)
        self.assertEqual(output.getvalue(), "")

    def test_selected_sources_reach_shelly_install(self):
        with patch("nyxniri.pkg.cli.preferred_manager", return_value="shelly"), \
             patch("nyxniri.pkg.subprocess.Popen", side_effect=[
                 self._process(stdout="fish\n"),
                 self._process(), self._process(),
             ]) as popen:
            self.assertEqual(cli.main(["install", "repo/fish", "aur/sample-bin"]), 0)
        self.assertEqual([invocation.args[0] for invocation in popen.call_args_list], [
            ["pacman", "-Slq"], ["shelly", "install", "standard", "fish"],
            ["shelly", "install", "aur", "sample-bin"],
        ])

    def test_tool_help_does_not_create_deployment_state(self):
        from pathlib import Path
        import os
        import sys
        before = set(self.env.home.rglob("*"))
        result = subprocess.run([sys.executable, "-m", "nyxniri", "clean", "--help"],
                                cwd=Path(__file__).resolve().parent.parent,
                                env=dict(os.environ), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("clean", result.stdout)
        self.assertEqual(set(self.env.home.rglob("*")), before)
