"""Portable template rendering — /home/user → real $HOME, dynamic paths.

Called by the full deploy pipeline (render all) and the preset-switch narrow
path (render only one app, §9). Kept side-effect-light: pure text substitution
on already-deployed config files.
"""

import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Optional

from nyxniri.constants import MAIN_WM, THEME_ENGINE
from nyxniri.core import get_env, get_pics_dir


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
_REGULAR_READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK


@contextmanager
def _opened_app_root(app_root: Path) -> Iterator[int]:
    """Bind one deployed app directory without following its final symlink."""
    path = Path(app_root)
    if path.parent == Path("/proc/self/fd") and path.name.isdecimal():
        fd = os.dup(int(path.name))
    else:
        fd = os.open(path, _DIRECTORY_FLAGS)
    try:
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("deployed app is not a directory")
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _opened_regular_leaf(
    parent_fd: int,
    name: str,
    *,
    writable: bool = False,
) -> Iterator[int]:
    """Open one direct regular-file child without following a symlink."""
    if not name or name in (".", "..") or Path(name).name != name:
        raise OSError("unsafe deployed file name")
    flags = _REGULAR_READ_FLAGS | (os.O_RDWR if writable else 0)
    fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("deployed file is not regular")
        yield fd
    finally:
        os.close(fd)


def _rewrite_regular_leaf(
    app_root: Path,
    name: str,
    rewrite: Callable[[str], str],
    *,
    errors: str = "strict",
) -> bool:
    """Rewrite a bound regular leaf through its fd, returning False if unsafe."""
    try:
        with _opened_app_root(app_root) as app_fd, \
             _opened_regular_leaf(app_fd, name, writable=True) as file_fd:
            with os.fdopen(os.dup(file_fd), "r+", encoding="utf-8", errors=errors) as handle:
                content = handle.read()
                rendered = rewrite(content)
                if rendered != content:
                    handle.seek(0)
                    handle.write(rendered)
                    handle.truncate()
                    handle.flush()
                    os.fsync(handle.fileno())
        return True
    except OSError:
        return False


def _phase_render_templates(
    only_app: Optional[str] = None,
    *,
    config_dir: Optional[Path] = None,
    app_root: Optional[Path] = None,
) -> None:
    """Render portable template paths (/home/user -> real $HOME, dynamic screenshot path).

    When ``only_app`` is set, render only that app's templates (narrow path for
    preset switches — no cross-app side effects). None = render all (full deploy).
    """
    env = get_env()
    home = env.home
    config_dir = config_dir or env.config_dir
    wp_dest = get_pics_dir() / "Wallpapers"

    def app_path(name: str) -> Path:
        if app_root is not None and only_app == name:
            return app_root
        return config_dir / name

    if only_app in (None, THEME_ENGINE):
        def render_noctalia(content: str) -> str:
            content = re.sub(r'^directory = ".*"', f'directory = "{wp_dest}"', content, flags=re.MULTILINE)
            content = re.sub(r'^video_directory = ".*"', f'video_directory = "{wp_dest / "video"}"', content, flags=re.MULTILINE)
            return content.replace("/home/user", str(home))

        _rewrite_regular_leaf(
            app_path(THEME_ENGINE),
            f"{THEME_ENGINE}-config.toml",
            render_noctalia,
            errors="replace",
        )

    if only_app in (None, MAIN_WM):
        def render_niri(content: str) -> str:
            content = content.replace("/home/user", str(home))
            pics_dir = get_pics_dir()
            if str(pics_dir).startswith(str(home)):
                rel_pics = "~" + str(pics_dir)[len(str(home)):]
            else:
                rel_pics = str(pics_dir)
            screenshot_target = f'screenshot-path "{rel_pics}/Screenshots/Screenshot from %Y-%m-%d %H-%M-%S.png"'
            return re.sub(r'^\s*(//)?\s*screenshot-path\s+.*', screenshot_target, content, flags=re.MULTILINE)

        _rewrite_regular_leaf(
            app_path(MAIN_WM),
            "config.kdl",
            render_niri,
            errors="replace",
        )

    if only_app in (None, "fish"):
        _rewrite_regular_leaf(
            app_path("fish"),
            "fish_variables",
            lambda content: content.replace("/home/user", str(home)),
            errors="replace",
        )
