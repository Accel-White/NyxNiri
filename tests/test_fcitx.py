"""Behavior contracts for fcitx: partial template registration detection (OR logic)."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, mock_open

from tests.utils import TempEnv


class TestFcitxTemplateDetection(unittest.TestCase):
    """fcitx_templates_registered must use OR logic (any one template = registered)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_all_three_registered_returns_true(self):
        """All 3 templates present → True."""
        from nyxniri.modules.fcitx import fcitx_templates_registered, FCITX_THEME

        content = (
            f"[theme.templates.user.{FCITX_THEME}_theme]\n"
            f"[theme.templates.user.{FCITX_THEME}_panel]\n"
            f"[theme.templates.user.{FCITX_THEME}_highlight]\n"
        )
        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value=content):
                    self.assertTrue(fcitx_templates_registered())

    def test_only_one_registered_returns_true(self):
        """Only 1 of 3 templates present → True (OR logic)."""
        from nyxniri.modules.fcitx import fcitx_templates_registered, FCITX_THEME

        content = f"[theme.templates.user.{FCITX_THEME}_theme]\n"
        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value=content):
                    self.assertTrue(fcitx_templates_registered(),
                                    "Partial registration (1/3) should return True with OR logic")

    def test_none_registered_returns_false(self):
        """No templates present → False."""
        from nyxniri.modules.fcitx import fcitx_templates_registered, FCITX_THEME

        content = "[some.other.template]\n"
        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value=content):
                    self.assertFalse(fcitx_templates_registered())

    def test_no_config_file_returns_false(self):
        """No config file → False."""
        from nyxniri.modules.fcitx import fcitx_templates_registered

        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=False):
                self.assertFalse(fcitx_templates_registered())

    def test_registration_replaces_legacy_restart_hook(self):
        from nyxniri.modules.fcitx import (
            FCITX_CLASSICUI_RELOAD_HOOK,
            FCITX_THEME,
            fcitx_register_templates,
        )

        config_path = self._ctx.env.config_dir / "noctalia" / "noctalia-config.toml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            f"""[theme.templates.user.unrelated]
post_hook = "{FCITX_CLASSICUI_RELOAD_HOOK}"

[theme.templates.user.{FCITX_THEME}_theme]
index = 0

[theme.templates.user.{FCITX_THEME}_panel]
index = 1

[theme.templates.user.{FCITX_THEME}_highlight]
index = 2
post_hook = "pkill -x fcitx5; sleep 1; fcitx5 -d &"
""",
            encoding="utf-8",
        )

        self.assertTrue(fcitx_register_templates())
        updated = config_path.read_text(encoding="utf-8")
        self.assertIn("ReloadAddonConfig s classicui", updated)
        self.assertNotIn("pkill -x fcitx5", updated)

class TestFcitxStartup(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_restart_starts_daemon_when_current_user_dbus_reload_fails(self):
        from nyxniri.modules.fcitx import fcitx_restart
        from nyxniri.i18n import msg

        with patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.fcitx.timed_run", return_value=SimpleNamespace(returncode=1)) as run, \
             patch("nyxniri.modules.fcitx.subprocess.Popen") as popen, \
             patch("nyxniri.modules.fcitx.print") as output:
            fcitx_restart()

        run.assert_called_once_with(
            [
                "busctl", "--user", "call",
                "org.fcitx.Fcitx5", "/controller",
                "org.fcitx.Fcitx.Controller1", "ReloadAddonConfig",
                "s", "classicui",
            ],
            5,
            stdout=-3,
            stderr=-3,
            check=False,
        )
        popen.assert_called_once_with(
            ["fcitx5", "-d"], stdout=-3, stderr=-3,
        )
        output.assert_called_once_with(msg("fcitx_start_requested"))

    def test_restart_reloads_classicui_without_restarting_running_daemon(self):
        from nyxniri.modules.fcitx import fcitx_restart

        reloaded = SimpleNamespace(returncode=0)
        with patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.fcitx.timed_run", return_value=reloaded) as run, \
             patch("nyxniri.modules.fcitx.subprocess.Popen") as popen:
            fcitx_restart()

        self.assertEqual(
            run.call_args.args[0],
            [
                "busctl", "--user", "call",
                "org.fcitx.Fcitx5", "/controller",
                "org.fcitx.Fcitx.Controller1", "ReloadAddonConfig",
                "s", "classicui",
            ],
        )
        popen.assert_not_called()

    def test_theme_post_hook_reloads_classicui_without_killing_fcitx(self):
        config = (self.env.configs_src / "noctalia" / "noctalia-config.toml").read_text(encoding="utf-8")
        self.assertIn("ReloadAddonConfig s classicui", config)
        self.assertNotIn("pkill -x fcitx5", config)
        self.assertNotIn("pgrep -x fcitx5", config)


class TestFcitxClassicUIConfig(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.classicui = self._ctx.env.config_dir / "fcitx5" / "conf" / "classicui.conf"

    def tearDown(self):
        self._ctx.__exit__()

    def test_theme_settings_use_fcitx_flat_addon_config_format(self):
        from nyxniri.modules.fcitx import fcitx_set_theme_conf

        fcitx_set_theme_conf()

        content = self.classicui.read_text(encoding="utf-8")
        self.assertEqual(content, "Theme=nyxmellow\nDarkTheme=nyxmellow\n")
        self.assertNotIn("[ClassicUI]", content)

    def test_theme_settings_migrate_invalid_legacy_section_header(self):
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

if __name__ == "__main__":
    unittest.main()
