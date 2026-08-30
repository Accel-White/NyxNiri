#!/usr/bin/env python3
"""Regression contract for the NyxMellow Fcitx theme reload fix.

Run this file from any checkout against the checkout to verify:

    python3 contracts/fcitx_theme_hot_reload.py /path/to/NyxNiri
"""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from pathlib import Path


DBUS_RELOAD_ARGS = [
    "busctl", "--user", "--auto-start=no", "call",
    "org.fcitx.Fcitx5", "/controller",
    "org.fcitx.Fcitx.Controller1", "ReloadAddonConfig",
    "s", "classicui",
]


def fail(message: str) -> None:
    print(f"contract failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} CHECKOUT", file=sys.stderr)
        return 2

    checkout = Path(argv[1]).resolve()
    module_file = checkout / "nyxniri" / "modules" / "fcitx.py"
    config_file = checkout / "configs" / "noctalia" / "noctalia-config.toml"
    if not module_file.is_file() or not config_file.is_file():
        fail(f"not a NyxNiri checkout: {checkout}")

    sys.path.insert(0, str(checkout))
    target_utils = importlib.import_module("tests.utils")
    with target_utils.TempEnv() as temp_env:
        fcitx = importlib.import_module("nyxniri.modules.fcitx")

        classicui = temp_env.env.config_dir / "fcitx5" / "conf" / "classicui.conf"
        classicui.parent.mkdir(parents=True)
        classicui.write_text(
            "[ClassicUI]\nTheme=default\nDarkTheme=default-dark\nFont=Sans 10\n",
            encoding="utf-8",
        )
        fcitx.fcitx_set_theme_conf()
        flat_config = classicui.read_text(encoding="utf-8")
        if "[ClassicUI]" in flat_config:
            fail("classicui.conf retains an invalid legacy section header")
        if "Theme=nyxmellow\n" not in flat_config or "DarkTheme=nyxmellow\n" not in flat_config:
            fail("classicui.conf does not set flat Theme/DarkTheme options")
        if "Font=Sans 10\n" not in flat_config:
            fail("classicui.conf migration discarded unrelated options")

        command_calls = []
        daemon_starts = []

        def reload_ok(args, timeout, **kwargs):
            command_calls.append((args, timeout, kwargs))
            return SimpleNamespace(returncode=0)

        fcitx.fcitx5_installed = lambda: True
        fcitx.timed_run = reload_ok
        fcitx.subprocess.Popen = lambda args, **kwargs: daemon_starts.append((args, kwargs))
        fcitx.fcitx_restart()
        expected_call = (
            DBUS_RELOAD_ARGS,
            5,
            {"stdout": fcitx.subprocess.DEVNULL, "stderr": fcitx.subprocess.DEVNULL, "check": False},
        )
        if command_calls != [expected_call] or daemon_starts:
            fail("successful ClassicUI reload did not preserve the running daemon")

        command_calls.clear()

        def reload_fails(args, timeout, **kwargs):
            command_calls.append((args, timeout, kwargs))
            return SimpleNamespace(returncode=1)

        fcitx.timed_run = reload_fails
        fcitx.fcitx_restart()
        expected_start = (
            ["fcitx5", "-d"],
            {"stdout": fcitx.subprocess.DEVNULL, "stderr": fcitx.subprocess.DEVNULL},
        )
        if command_calls != [expected_call] or daemon_starts != [expected_start]:
            fail("failed reload did not request only the current user's Fcitx daemon")

        noctalia = temp_env.env.config_dir / "noctalia" / "noctalia-config.toml"
        noctalia.parent.mkdir(parents=True)
        noctalia.write_text(
            "[theme.templates.user.nyxmellow_theme]\nindex = 0\n\n"
            "[theme.templates.user.nyxmellow_panel]\nindex = 1\n\n"
            "[theme.templates.user.nyxmellow_highlight]\nindex = 2\n"
            "post_hook = \"pkill -x fcitx5; fcitx5 -d &\"\n",
            encoding="utf-8",
        )
        if not fcitx.fcitx_register_templates():
            fail("NyxMellow template registration failed")
        registered = noctalia.read_text(encoding="utf-8")
        if (
            "ReloadAddonConfig s classicui" not in registered
            or "--auto-start=no" not in registered
            or "fcitx5-remote --check -r" not in registered
            or "pkill -x fcitx5" in registered
        ):
            fail("NyxMellow template hook does not use ClassicUI D-Bus reload")

    print(f"contract passed: {checkout}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
