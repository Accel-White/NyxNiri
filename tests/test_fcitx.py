"""Behavior contracts for the optional NyxMellow Fcitx module."""

import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.utils import TempEnv


class TestFcitxTemplateDetection(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_all_three_registered_returns_true(self):
        from nyxniri.modules.fcitx import FCITX_THEME, fcitx_templates_registered

        content = (
            f"[theme.templates.user.{FCITX_THEME}_theme]\n"
            f"[theme.templates.user.{FCITX_THEME}_panel]\n"
            f"[theme.templates.user.{FCITX_THEME}_highlight]\n"
        )
        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True), \
                 patch("pathlib.Path.read_text", return_value=content):
                self.assertTrue(fcitx_templates_registered())

    def test_only_one_registered_returns_true(self):
        from nyxniri.modules.fcitx import FCITX_THEME, fcitx_templates_registered

        content = f"[theme.templates.user.{FCITX_THEME}_theme]\n"
        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True), \
                 patch("pathlib.Path.read_text", return_value=content):
                self.assertTrue(fcitx_templates_registered())

    def test_none_registered_returns_false(self):
        from nyxniri.modules.fcitx import fcitx_templates_registered

        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True), \
                 patch("pathlib.Path.read_text", return_value="[some.other.template]\n"):
                self.assertFalse(fcitx_templates_registered())

    def test_no_config_file_returns_false(self):
        from nyxniri.modules.fcitx import fcitx_templates_registered

        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=False):
                self.assertFalse(fcitx_templates_registered())

    def test_registration_updates_only_owned_highlight_hook(self):
        from nyxniri.modules.fcitx import (
            FCITX_CLASSICUI_RELOAD_HOOK,
            FCITX_THEME,
            fcitx_register_templates,
        )

        path = self.env.config_dir / "noctalia/noctalia-config.toml"
        path.parent.mkdir(parents=True)
        unrelated_hook = "fcitx5-remote --check -r >/dev/null 2>&1 || true"
        path.write_text(
            f'[theme.templates.user.personal]\npost_hook = "{unrelated_hook}"\n\n'
            f'[theme.templates.user.{FCITX_THEME}_theme]\nindex = 0\n\n'
            f'[theme.templates.user.{FCITX_THEME}_panel]\nindex = 1\n\n'
            f'[theme.templates.user.{FCITX_THEME}_highlight]\nindex = 2\n'
            'post_hook = "pkill -x fcitx5; sleep 1; fcitx5 -d &"\n',
            encoding="utf-8",
        )

        self.assertTrue(fcitx_register_templates())
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
        registered = parsed["theme"]["templates"]["user"]
        self.assertEqual(registered["personal"]["post_hook"], unrelated_hook)
        self.assertEqual(
            registered[f"{FCITX_THEME}_highlight"]["post_hook"],
            FCITX_CLASSICUI_RELOAD_HOOK,
        )


class TestFcitxLifecycle(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_niri_starts_fcitx_when_installed(self):
        config = (self.env.configs_src / "niri" / "config.kdl").read_text(encoding="utf-8")
        self.assertIn(
            'spawn-at-startup "sh" "-c" "command -v fcitx5 >/dev/null 2>&1 && exec fcitx5 -d"',
            config,
        )

    def test_reload_does_not_start_or_kill_daemon(self):
        from nyxniri.modules.fcitx import fcitx_reload

        with patch("nyxniri.modules.fcitx.shutil.which", return_value="/usr/bin/fcitx5-remote"), \
             patch("nyxniri.modules.fcitx.timed_run", return_value=SimpleNamespace(returncode=1)) as run, \
             patch("nyxniri.modules.fcitx.subprocess.Popen") as popen:
            fcitx_reload()

        run.assert_called_once_with(
            ["fcitx5-remote", "--check", "-r"],
            5,
            capture_output=True,
            check=False,
        )
        popen.assert_not_called()

    def test_install_reload_starts_daemon_when_classicui_call_fails(self):
        from nyxniri.i18n import msg
        from nyxniri.modules.fcitx import FCITX_CLASSICUI_RELOAD, fcitx_restart

        with patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.fcitx.timed_run", return_value=SimpleNamespace(returncode=1)) as run, \
             patch("nyxniri.modules.fcitx.subprocess.Popen") as popen, \
             patch("nyxniri.modules.fcitx.print") as output:
            fcitx_restart()

        run.assert_called_once_with(
            FCITX_CLASSICUI_RELOAD,
            5,
            stdout=-3,
            stderr=-3,
            check=False,
        )
        popen.assert_called_once_with(["fcitx5", "-d"], stdout=-3, stderr=-3)
        output.assert_called_once_with(msg("fcitx_start_requested"))

    def test_install_reload_does_not_restart_running_daemon(self):
        from nyxniri.modules.fcitx import FCITX_CLASSICUI_RELOAD, fcitx_restart

        with patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.fcitx.timed_run", return_value=SimpleNamespace(returncode=0)) as run, \
             patch("nyxniri.modules.fcitx.subprocess.Popen") as popen:
            fcitx_restart()

        self.assertEqual(run.call_args.args[0], FCITX_CLASSICUI_RELOAD)
        popen.assert_not_called()

    def test_theme_post_hook_reloads_only_classicui(self):
        config = (self.env.configs_src / "noctalia/noctalia-config.toml").read_text(encoding="utf-8")
        self.assertIn("ReloadAddonConfig s classicui", config)
        self.assertNotIn("pkill -x fcitx5", config)
        self.assertNotIn("fcitx5-remote --check -r", config)


class TestFcitxConfiguration(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.classicui = self.env.config_dir / "fcitx5/conf/classicui.conf"

    def tearDown(self):
        self._ctx.__exit__()

    def test_theme_settings_use_root_addon_config_format(self):
        from nyxniri.modules.fcitx import fcitx_set_theme_conf

        fcitx_set_theme_conf()
        self.assertEqual(
            self.classicui.read_text(encoding="utf-8"),
            "Theme=nyxmellow\nDarkTheme=nyxmellow\n",
        )

    def test_theme_settings_migrate_invalid_legacy_header(self):
        from nyxniri.modules.fcitx import fcitx_set_theme_conf

        self.classicui.parent.mkdir(parents=True)
        self.classicui.write_text(
            "[ClassicUI]\nTheme=default\nDarkTheme=default-dark\nFont=Sans 10\n",
            encoding="utf-8",
        )
        fcitx_set_theme_conf()

        content = self.classicui.read_text(encoding="utf-8")
        self.assertNotIn("[ClassicUI]", content)
        self.assertIn("Theme=nyxmellow\n", content)
        self.assertIn("DarkTheme=nyxmellow\n", content)
        self.assertIn("Font=Sans 10\n", content)

    def test_theme_edit_preserves_other_sections_comments_and_mode(self):
        from nyxniri.modules.fcitx import fcitx_set_theme_conf

        self.classicui.parent.mkdir(parents=True)
        self.classicui.write_text(
            "# personal\n[Other]\nTheme=keep\n[ClassicUI]\nTheme=old\nFont=custom\n",
            encoding="utf-8",
        )
        self.classicui.chmod(0o600)
        fcitx_set_theme_conf()

        self.assertEqual(
            self.classicui.read_text(encoding="utf-8"),
            "# personal\nTheme=nyxmellow\nFont=custom\nDarkTheme=nyxmellow\n[Other]\nTheme=keep\n",
        )
        self.assertEqual(self.classicui.stat().st_mode & 0o777, 0o600)

    def test_uninstall_keeps_user_changes_and_private_theme_files(self):
        from nyxniri.modules.fcitx import fcitx_set_theme_conf, fcitx_uninstall

        self.classicui.parent.mkdir(parents=True)
        self.classicui.write_text(
            "[ClassicUI]\nTheme=old\nDarkTheme=old-dark\n",
            encoding="utf-8",
        )
        fcitx_set_theme_conf()
        self.classicui.write_text(
            self.classicui.read_text(encoding="utf-8").replace(
                "Theme=nyxmellow\n",
                "Theme=my-new-theme\n",
                1,
            ),
            encoding="utf-8",
        )
        private = self.env.home / ".local/share/fcitx5/themes/nyxmellow/custom.txt"
        private.parent.mkdir(parents=True)
        private.write_text("mine", encoding="utf-8")

        with patch("nyxniri.modules.fcitx.fcitx_reload"):
            self.assertTrue(fcitx_uninstall())

        self.assertIn("Theme=my-new-theme\n", self.classicui.read_text(encoding="utf-8"))
        self.assertIn("DarkTheme=old-dark\n", self.classicui.read_text(encoding="utf-8"))
        self.assertEqual(private.read_text(encoding="utf-8"), "mine")

    def test_install_preserves_shortcuts_and_is_repeatable(self):
        from nyxniri.modules.fcitx import fcitx_install

        config = self.env.config_dir / "fcitx5/config"
        config.parent.mkdir(parents=True)
        config.write_text("[Hotkey/TriggerKeys]\n0=Alt+space\n", encoding="utf-8")
        quickphrase = config.parent / "conf/quickphrase.conf"
        quickphrase.parent.mkdir()
        quickphrase.write_text("[Hotkey]\nTriggerKey=Super+space\n", encoding="utf-8")
        shell = self.env.config_dir / "noctalia/noctalia-config.toml"
        shell.parent.mkdir()
        shell.write_text('[theme]\nmode = "dark"\n', encoding="utf-8")

        with patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.fcitx.fcitx_trigger_render"), \
             patch("nyxniri.modules.fcitx.fcitx_restart"):
            self.assertTrue(fcitx_install())
            first = shell.read_text(encoding="utf-8")
            self.assertTrue(fcitx_install())
            self.assertEqual(shell.read_text(encoding="utf-8"), first)

        self.assertEqual(config.read_text(encoding="utf-8"), "[Hotkey/TriggerKeys]\n0=Alt+space\n")
        self.assertEqual(quickphrase.read_text(encoding="utf-8"), "[Hotkey]\nTriggerKey=Super+space\n")

    def test_template_removal_leaves_other_templates(self):
        from nyxniri.modules.fcitx import fcitx_register_templates, fcitx_uninstall

        path = self.env.config_dir / "noctalia/noctalia-config.toml"
        path.parent.mkdir()
        personal = '[theme.templates.user.nyxmellow_personal]\ninput_path = "mine"\n'
        owned = '[theme.templates.user.nyxmellow_theme]\nindex = 9\n'
        path.write_text(personal + owned, encoding="utf-8")
        self.assertTrue(fcitx_register_templates())
        self.assertIn(personal, path.read_text(encoding="utf-8"))
        self.assertIn(owned, path.read_text(encoding="utf-8"))

        with patch("nyxniri.modules.fcitx.fcitx_reload"):
            self.assertTrue(fcitx_uninstall())

        self.assertIn(personal, path.read_text(encoding="utf-8"))
        self.assertNotIn("nyxmellow_theme]", path.read_text(encoding="utf-8"))

    def test_failed_template_write_does_not_enable_module(self):
        from nyxniri.modules.fcitx import fcitx_enabled, fcitx_install

        with patch("nyxniri.modules.fcitx.atomic_replace_item", return_value=False):
            self.assertFalse(fcitx_install())
        self.assertFalse(fcitx_enabled())


if __name__ == "__main__":
    unittest.main()
