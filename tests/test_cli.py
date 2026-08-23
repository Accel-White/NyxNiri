"""Behavior contracts for CLI: exit code propagation, --force path, update hooks."""

import unittest
from unittest.mock import patch, MagicMock

from tests.utils import make_temp_home, force_repo_mode, reset_env
from pathlib import Path


class TestGreeterExitCode(unittest.TestCase):
    """greeter install/uninstall exit code must propagate."""

    def setUp(self):
        self._tmp = make_temp_home()
        reset_env(Path(self._tmp.name))
        force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_greeter_install_failure_propagates_exit_1(self):
        """If greeter_install returns False, CLI should exit(1)."""
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "greeter", "install"]):
            with patch("nyxniri.cli.greeter_install", return_value=False):
                with self.assertRaises(SystemExit) as ctx:
                    main()
                self.assertEqual(ctx.exception.code, 1)

    def test_greeter_install_success_propagates_exit_0(self):
        """If greeter_install returns True, CLI should exit(0)."""
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "greeter", "install"]):
            with patch("nyxniri.cli.greeter_install", return_value=True):
                with self.assertRaises(SystemExit) as ctx:
                    main()
                self.assertEqual(ctx.exception.code, 0)


class TestFcitxExitCode(unittest.TestCase):
    """fcitx install/uninstall exit code must propagate."""

    def setUp(self):
        self._tmp = make_temp_home()
        reset_env(Path(self._tmp.name))
        force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_fcitx_uninstall_failure_propagates_exit_1(self):
        """If fcitx_uninstall returns False, CLI should exit(1)."""
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "fcitx", "uninstall"]):
            with patch("nyxniri.cli.fcitx_uninstall", return_value=False):
                with self.assertRaises(SystemExit) as ctx:
                    main()
                self.assertEqual(ctx.exception.code, 1)


class TestUpdateForcePath(unittest.TestCase):
    """update --force must deploy wallpapers + greeter, not just configs + fcitx."""

    def setUp(self):
        self._tmp = make_temp_home()
        reset_env(Path(self._tmp.name))
        force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_force_deploys_wallpapers_and_greeter(self):
        """--force/--deploy should call deploy_wallpapers and greeter_install."""
        from nyxniri.cli import offer_overwrite_upgrade

        with patch("nyxniri.cli.deploy_selected_configs", return_value=[]):
            with patch("nyxniri.cli.deploy_wallpapers") as mock_wp:
                with patch("nyxniri.cli.fcitx_enabled", return_value=True):
                    with patch("nyxniri.cli.fcitx_install"):
                        with patch("nyxniri.cli.greeter_install") as mock_greeter:
                            with patch("nyxniri.cli.render_completion_screen"):
                                offer_overwrite_upgrade("--force")

        mock_wp.assert_called_once_with(do_download=True)
        mock_greeter.assert_called_once()


class TestUpdateChecksNewDeps(unittest.TestCase):
    """update command should call check_new_deps_post_update after deploy."""

    def setUp(self):
        self._tmp = make_temp_home()
        reset_env(Path(self._tmp.name))
        force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_update_calls_check_new_deps(self):
        """CLI update command should call check_new_deps_post_update."""
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "update"]):
            with patch("nyxniri.cli.safe_git_pull", return_value=True):
                with patch("nyxniri.cli.offer_overwrite_upgrade", return_value=True):
                    with patch("nyxniri.cli.check_new_deps_post_update") as mock_check:
                        with patch("builtins.print"):
                            with self.assertRaises(SystemExit):
                                main()

        mock_check.assert_called_once()


class TestCheckNewDepsPostUpdate(unittest.TestCase):
    """check_new_deps_post_update should detect and offer to install missing deps."""

    def setUp(self):
        self._tmp = make_temp_home()
        reset_env(Path(self._tmp.name))
        force_repo_mode()

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_missing_deps_no_action(self):
        """If no deps missing, should do nothing."""
        from nyxniri.cli import check_new_deps_post_update

        with patch("nyxniri.cli.get_missing_deps", return_value=[]):
            with patch("nyxniri.cli.install_selected_deps") as mock_install:
                check_new_deps_post_update()

        mock_install.assert_not_called()

    def test_missing_deps_non_interactive_auto_installs(self):
        """Non-interactive with missing deps should auto-install."""
        from nyxniri.cli import check_new_deps_post_update

        with patch("nyxniri.cli.get_missing_deps", return_value=["some-pkg"]):
            with patch("sys.stdin.isatty", return_value=False):
                with patch("nyxniri.cli.install_selected_deps") as mock_install:
                    with patch("builtins.print"):
                        check_new_deps_post_update()

        mock_install.assert_called_once_with(["some-pkg"])


if __name__ == "__main__":
    unittest.main()
