"""Behavior contracts for Noctalia Greeter system setup."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests.utils import TempEnv


def _result(returncode: int = 0, stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


class TestGreeterInstall(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    @staticmethod
    def _run_install(fake_run):
        from nyxniri.modules.greeter import greeter_install

        with patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/tool"):
            with patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run) as mock_run:
                with patch(
                    "nyxniri.modules.greeter.greeter_install_packages", return_value=True
                ) as mock_packages:
                    with patch("nyxniri.modules.greeter._greeter_session_arg", return_value=""):
                        with patch("nyxniri.modules.greeter.log_msg") as mock_log:
                            with patch("builtins.print"):
                                result = greeter_install()

        return result, mock_run, mock_log, mock_packages

    @staticmethod
    def _systemctl_commands(mock_run):
        return [
            mock_call.args[0]
            for mock_call in mock_run.call_args_list
            if "systemctl" in mock_call.args[0]
        ]

    def test_enabled_display_manager_switches_only_after_setup(self):
        def fake_run(argv, **kwargs):
            if argv == ["systemctl", "is-enabled", "sddm"]:
                return _result(0)
            if argv == ["systemctl", "is-enabled", "greetd"]:
                return _result(0)
            return _result(0)

        result, mock_run, mock_log, _ = self._run_install(fake_run)

        self.assertTrue(result)
        mock_log.assert_called_once_with("INFO", "Configured Noctalia Greeter")
        self.assertEqual(
            self._systemctl_commands(mock_run),
            [
                ["systemctl", "cat", "greetd"],
                ["systemctl", "is-enabled", "sddm"],
                ["sudo", "systemctl", "disable", "sddm"],
                ["sudo", "systemctl", "enable", "greetd"],
                ["systemctl", "is-enabled", "greetd"],
            ],
        )
        disable_index = next(
            index
            for index, mock_call in enumerate(mock_run.call_args_list)
            if mock_call.args[0] == ["sudo", "systemctl", "disable", "sddm"]
        )
        self.assertEqual(disable_index, len(mock_run.call_args_list) - 3)

    def test_config_failure_leaves_enabled_display_manager_untouched(self):
        def fake_run(argv, **kwargs):
            if argv == ["systemctl", "is-enabled", "sddm"]:
                return _result(0)
            if argv[:3] == ["sudo", "sh", "-c"] and "config.toml\n" in argv[3]:
                return _result(1)
            return _result(0)

        result, mock_run, mock_log, mock_packages = self._run_install(fake_run)

        self.assertFalse(result)
        mock_log.assert_not_called()
        mock_packages.assert_called_once_with()
        self.assertTrue(
            any(
                mock_call.args[0][:3] == ["sudo", "sh", "-c"]
                and "config.toml\n" in mock_call.args[0][3]
                for mock_call in mock_run.call_args_list
            )
        )
        self.assertEqual(
            self._systemctl_commands(mock_run),
            [],
        )

    def test_missing_greetd_unit_leaves_display_manager_untouched(self):
        def fake_run(argv, **kwargs):
            if argv == ["systemctl", "cat", "greetd"]:
                return _result(1)
            return _result(0)

        result, mock_run, mock_log, _ = self._run_install(fake_run)

        self.assertFalse(result)
        mock_log.assert_not_called()
        self.assertEqual(
            self._systemctl_commands(mock_run),
            [["systemctl", "cat", "greetd"]],
        )

    def test_enable_failure_restores_previous_display_manager(self):
        def fake_run(argv, **kwargs):
            if argv == ["systemctl", "is-enabled", "sddm"]:
                return _result(0)
            if argv == ["sudo", "systemctl", "enable", "greetd"]:
                return _result(1)
            if argv == ["systemctl", "is-enabled", "greetd"]:
                return _result(1)
            return _result(0)

        result, mock_run, mock_log, _ = self._run_install(fake_run)

        self.assertFalse(result)
        mock_log.assert_not_called()
        self.assertEqual(
            self._systemctl_commands(mock_run),
            [
                ["systemctl", "cat", "greetd"],
                ["systemctl", "is-enabled", "sddm"],
                ["sudo", "systemctl", "disable", "sddm"],
                ["sudo", "systemctl", "enable", "greetd"],
                ["systemctl", "is-enabled", "greetd"],
                ["sudo", "systemctl", "disable", "greetd"],
                ["sudo", "systemctl", "enable", "--force", "sddm"],
                ["systemctl", "is-enabled", "sddm"],
            ],
        )

    def test_disable_failure_restores_previous_display_manager(self):
        def fake_run(argv, **kwargs):
            if argv == ["systemctl", "is-enabled", "sddm"]:
                return _result(0)
            if argv == ["sudo", "systemctl", "disable", "sddm"]:
                return _result(1)
            return _result(0)

        result, mock_run, mock_log, _ = self._run_install(fake_run)

        self.assertFalse(result)
        mock_log.assert_not_called()
        self.assertEqual(
            self._systemctl_commands(mock_run),
            [
                ["systemctl", "cat", "greetd"],
                ["systemctl", "is-enabled", "sddm"],
                ["sudo", "systemctl", "disable", "sddm"],
                ["sudo", "systemctl", "disable", "greetd"],
                ["sudo", "systemctl", "enable", "--force", "sddm"],
                ["systemctl", "is-enabled", "sddm"],
            ],
        )

    def test_verification_failure_restores_previous_display_manager(self):
        def fake_run(argv, **kwargs):
            if argv == ["systemctl", "is-enabled", "sddm"]:
                return _result(0)
            if argv == ["systemctl", "is-enabled", "greetd"]:
                return _result(1)
            return _result(0)

        result, mock_run, mock_log, _ = self._run_install(fake_run)

        self.assertFalse(result)
        mock_log.assert_not_called()
        self.assertEqual(
            self._systemctl_commands(mock_run),
            [
                ["systemctl", "cat", "greetd"],
                ["systemctl", "is-enabled", "sddm"],
                ["sudo", "systemctl", "disable", "sddm"],
                ["sudo", "systemctl", "enable", "greetd"],
                ["systemctl", "is-enabled", "greetd"],
                ["sudo", "systemctl", "disable", "greetd"],
                ["sudo", "systemctl", "enable", "--force", "sddm"],
                ["systemctl", "is-enabled", "sddm"],
            ],
        )

    def test_success_without_conflict_verifies_greetd_and_logs(self):
        def fake_run(argv, **kwargs):
            if argv[:2] == ["systemctl", "is-enabled"]:
                return _result(0 if argv[-1] == "greetd" else 1)
            return _result(0)

        result, mock_run, mock_log, _ = self._run_install(fake_run)

        self.assertTrue(result)
        mock_log.assert_called_once_with("INFO", "Configured Noctalia Greeter")
        self.assertEqual(
            self._systemctl_commands(mock_run),
            [
                ["systemctl", "cat", "greetd"],
                ["systemctl", "is-enabled", "sddm"],
                ["systemctl", "is-enabled", "lightdm"],
                ["systemctl", "is-enabled", "gdm"],
                ["systemctl", "is-enabled", "ly"],
                ["sudo", "systemctl", "enable", "greetd"],
                ["systemctl", "is-enabled", "greetd"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
