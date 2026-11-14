"""Read-only Noctalia upstream security-version diagnostics."""

import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

from nyxniri import doctor


class TestNoctaliaSecurityVersion(unittest.TestCase):
    def _render(self, result):
        output = io.StringIO()
        with (
            patch.object(doctor, "timed_run", return_value=result) as run,
            patch.object(doctor, "text", side_effect=lambda zh, en: en),
            patch.object(doctor, "msg", side_effect=lambda status, message: f"{status}: {message}"),
            contextlib.redirect_stdout(output),
        ):
            doctor._check_noctalia_version()
        run.assert_called_once_with(
            [doctor.THEME_ENGINE, "--version"], 5,
            capture_output=True, text=True, check=False,
        )
        return output.getvalue()

    def test_parser_accepts_stable_version_output(self):
        self.assertEqual(doctor._parse_noctalia_version("noctalia v5.5.0\n"), (5, 5, 0))
        self.assertEqual(doctor._parse_noctalia_version("noctalia 5.3.0"), (5, 3, 0))

    def test_parser_does_not_classify_dev_or_prerelease_as_stable(self):
        for version in ("noctalia 5.3.0-dev", "noctalia v5.3.0-rc1", "noctalia 5.3.0+g123"):
            with self.subTest(version=version):
                self.assertIsNone(doctor._parse_noctalia_version(version))

    def test_outdated_version_warns(self):
        output = self._render(subprocess.CompletedProcess([], 0, stdout="noctalia 5.2.9\n", stderr=""))
        self.assertIn("5.2.9", output)
        self.assertIn("v5.3.0", output)
        self.assertIn("doctor_warn", output)

    def test_security_baseline_passes(self):
        for version in ("5.3.0", "5.5.0"):
            with self.subTest(version=version):
                output = self._render(subprocess.CompletedProcess([], 0, stdout=f"noctalia {version}\n", stderr=""))
                self.assertIn("doctor_ok", output)
                self.assertIn(version, output)

    def test_unknown_version_is_not_called_safe(self):
        output = self._render(subprocess.CompletedProcess([], 0, stdout="noctalia git-main\n", stderr=""))
        self.assertIn("doctor_warn", output)
        self.assertNotIn("doctor_ok", output)

    def test_failed_command_is_nonblocking(self):
        for result in (None, subprocess.CompletedProcess([], 1, stdout="", stderr="not available")):
            with self.subTest(result=result):
                output = self._render(result)
                self.assertIn("doctor_warn", output)

    def test_operating_system_error_is_nonblocking(self):
        output = io.StringIO()
        with (
            patch.object(doctor, "timed_run", side_effect=OSError("not executable")),
            patch.object(doctor, "text", side_effect=lambda zh, en: en),
            patch.object(doctor, "msg", side_effect=lambda status, message: f"{status}: {message}"),
            contextlib.redirect_stdout(output),
        ):
            doctor._check_noctalia_version()
        self.assertIn("doctor_warn", output.getvalue())

    def test_daemon_status_check_remains_in_place(self):
        output = io.StringIO()
        responses = [
            subprocess.CompletedProcess([], 0, stdout=b"", stderr=b""),
            subprocess.CompletedProcess([], 0, stdout="noctalia 5.5.0\n", stderr=""),
        ]
        with (
            patch.object(doctor.shutil, "which", return_value="/usr/bin/noctalia"),
            patch.object(doctor, "timed_run", side_effect=responses) as run,
            patch.object(doctor, "text", side_effect=lambda zh, en: en),
            patch.object(doctor, "msg", side_effect=lambda status, message: f"{status}: {message}"),
            contextlib.redirect_stdout(output),
        ):
            doctor._check_noctalia(None)
        self.assertEqual(run.call_count, 2)
        self.assertIn("daemon is responding", output.getvalue())
        self.assertIn("security-fix version baseline", output.getvalue())


if __name__ == "__main__":
    unittest.main()
