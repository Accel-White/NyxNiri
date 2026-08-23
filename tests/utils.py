"""Shared test utilities: environment reset, temp HOME isolation, subprocess mocks."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import nyxniri.core as core


def reset_env(home: Path) -> None:
    """Reset the cached Environment singleton, forcing re-init against a new HOME."""
    core._ENV = None
    os.environ["HOME"] = str(home)
    os.environ["XDG_STATE_HOME"] = str(home / ".local" / "state")


def make_temp_home() -> tempfile.TemporaryDirectory:
    """Create a temp HOME with a fake NyxNiri repo skeleton so get_env() sees 'repo' mode."""
    tmp = tempfile.TemporaryDirectory()
    home = Path(tmp.name)
    (home / ".config").mkdir(parents=True, exist_ok=True)
    (home / ".local" / "bin").mkdir(parents=True, exist_ok=True)
    (home / ".local" / "state" / "NyxNiri").mkdir(parents=True, exist_ok=True)

    # Minimal repo skeleton so Environment detects "repo" mode
    repo = home / "NyxNiri"
    (repo / "configs").mkdir(parents=True)
    (repo / "assets" / "wallpapers").mkdir(parents=True)
    (repo / "nyxniri").mkdir(parents=True)

    # Point __file__ resolution: we need to make core.py think the package lives under repo
    # The real repo detection uses Path(__file__).resolve().parent.parent — we can't fake that,
    # so we patch run_mode to "repo" after init instead.
    reset_env(home)

    return tmp


def force_repo_mode():
    """Patch the Environment to report 'repo' mode with a given repo_dir."""
    env = core.get_env()
    env.run_mode = "repo"
    env.mode_label = "Local Path"
    env.repo_dir = Path(__file__).resolve().parent.parent
    env.configs_src = env.repo_dir / "configs"
    env.assets_src = env.repo_dir / "assets"
    return env
