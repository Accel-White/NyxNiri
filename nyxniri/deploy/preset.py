"""Preset mechanism — switch an app's active variant (default / official / user).

Three layers stack, lowest to highest (§2.4)::

    默认 config  ←  官方预设  ←  __custom__ 文件

The active choice lives in a state file ``~/.config/NyxNiri/presets/<app>.active``
(one line: the preset name, or ``default``). This module owns the read/write and
the src-resolution that picks which directory gets deployed for an app.

Write timing (iron law, §3.2): apply flows deploy first, then write the active
file. The dest-missing reset is the only sanctioned write-before-deploy (dest is
empty, and deployment aborts if the state write does not complete).
"""

import hashlib
import os
import secrets
import shutil
import stat
import subprocess
import sys
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Union

from nyxniri.constants import Colors, PROJECT_NAME
from nyxniri.core import get_env, log_msg
from nyxniri.deploy.atomic import _entry_matches_at, _same_inode
from nyxniri.i18n import msg


_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
_ACTIVE_MAX_BYTES = 4096


class ActivePresetStatus(Enum):
    """State of an app's active preset slot."""

    MISSING = auto()
    VALID = auto()
    INVALID = auto()


@dataclass(frozen=True)
class _ActiveSlotSnapshot:
    """Opaque identity of one active slot without retaining malformed data."""

    exists: bool
    device: int = 0
    inode: int = 0
    mode: int = 0
    size: int = 0
    mtime_ns: int = 0
    ctime_ns: int = 0
    digest: bytes = b""


@dataclass(frozen=True)
class ActivePresetState:
    """Validated active selection without retaining malformed input."""

    status: ActivePresetStatus
    selected: Optional[str]
    _snapshot: Optional[_ActiveSlotSnapshot] = field(
        default=None,
        compare=False,
        repr=False,
    )


class InvalidActivePresetError(ValueError):
    """Raised when an active preset slot exists but is unsafe or malformed."""


class ActivePresetWriteError(OSError):
    """Active-slot failure with publication and verification state."""

    def __init__(self, published: bool, verified: bool, message: str):
        super().__init__(message)
        self.published = published
        self.verified = verified


@contextmanager
def _opened_root(path: Path, *, create: bool = False) -> Iterator[int]:
    """Resolve a trust root, then bind every resolved component no-follow."""
    absolute = Path(os.path.abspath(path))
    missing: List[str] = []
    cursor = absolute
    while True:
        try:
            resolved = cursor.resolve(strict=True)
            break
        except FileNotFoundError:
            if not create or cursor == cursor.parent:
                raise
            if cursor.name in ("", ".", ".."):
                raise OSError("unsafe trust root component")
            missing.append(cursor.name)
            cursor = cursor.parent

    if not resolved.is_absolute():
        raise OSError("trust root must resolve to an absolute path")

    fd = os.open(os.sep, _DIR_FLAGS)
    try:
        for component in resolved.parts[1:]:
            next_fd = os.open(component, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        for component in reversed(missing):
            try:
                next_fd = os.open(component, _DIR_FLAGS, dir_fd=fd)
            except FileNotFoundError:
                os.mkdir(component, mode=0o755, dir_fd=fd)
                next_fd = os.open(component, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


def _open_dir_at(parent_fd: int, name: str, *, create: bool = False) -> int:
    """Open one directory leaf without following it."""
    try:
        return os.open(name, _DIR_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise
    try:
        os.mkdir(name, mode=0o755, dir_fd=parent_fd)
    except FileExistsError:
        pass
    return os.open(name, _DIR_FLAGS, dir_fd=parent_fd)


@contextmanager
def _opened_presets_dir_at(config_fd: int, *, create: bool = False) -> Iterator[int]:
    """Bind NyxNiri/presets below one already-bound config root."""
    nyx_fd = _open_dir_at(config_fd, PROJECT_NAME, create=create)
    try:
        presets_fd = _open_dir_at(nyx_fd, "presets", create=create)
        try:
            yield presets_fd
        finally:
            os.close(presets_fd)
    finally:
        os.close(nyx_fd)


@contextmanager
def _opened_presets_dir(*, create: bool = False) -> Iterator[int]:
    """Bind ~/.config/NyxNiri/presets below the resolved config trust root."""
    with _opened_root(get_env().config_dir, create=create) as config_fd:
        with _opened_presets_dir_at(config_fd, create=create) as presets_fd:
            yield presets_fd


@contextmanager
def _opened_user_app_at(
    presets_fd: int,
    app: str,
    *,
    create: bool = False,
) -> Iterator[int]:
    """Bind one user preset app directory below the safe preset root."""
    app_fd = _open_dir_at(presets_fd, app, create=create)
    try:
        yield app_fd
    finally:
        os.close(app_fd)


@contextmanager
def _opened_user_app(app: str, *, create: bool = False) -> Iterator[int]:
    """Bind one user preset app through a newly opened config root."""
    with _opened_presets_dir(create=create) as presets_fd:
        with _opened_user_app_at(presets_fd, app, create=create) as app_fd:
            yield app_fd


def _proc_fd_path(fd: int) -> Path:
    """Expose an already-bound fd to stdlib copy helpers on Linux."""
    path = Path("/proc/self/fd") / str(fd)
    if not path.exists():
        raise OSError("bound fd path unavailable")
    return path


def _is_safe_component(value: str) -> bool:
    """Return whether value is one losslessly stored filesystem leaf name."""
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if value in (".", "..") or Path(value).is_absolute():
        return False
    if os.sep in value or (os.altsep and os.altsep in value):
        return False
    try:
        encoded = os.fsencode(value)
    except (TypeError, UnicodeEncodeError):
        return False
    return len(encoded) <= 255 and all(
        unicodedata.category(char) not in ("Cc", "Cs") for char in value
    )


@dataclass(frozen=True)
class _BoundRepoApp:
    root_fd: int
    fd: int
    info: os.stat_result
    path: Path


@contextmanager
def _opened_repo_app(app: str) -> Iterator[_BoundRepoApp]:
    """Bind a repo app and its configs parent for one complete operation."""
    if not _is_safe_component(app):
        raise OSError("unsafe repo app")
    with _opened_root(get_env().configs_src) as root_fd:
        fd = os.open(app, _READ_FLAGS, dir_fd=root_fd)
        try:
            info = os.fstat(fd)
            if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                raise OSError("unsafe repo app type")
            yield _BoundRepoApp(
                root_fd=root_fd,
                fd=fd,
                info=info,
                path=_proc_fd_path(fd),
            )
        finally:
            os.close(fd)


def _open_repo_app_fd(app: str) -> Tuple[int, os.stat_result]:
    """Bind one repo app while preserving the established fd-returning API."""
    with _opened_repo_app(app) as bound:
        return os.dup(bound.fd), bound.info


@dataclass(frozen=True)
class _BoundConfigTarget:
    parent_fd: int
    name: str
    path: Path
    display_path: Path


def _bound_config_target(config_fd: int, app: str) -> _BoundConfigTarget:
    """Expose one non-symlink app target below a bound config root."""
    if not _is_safe_component(app):
        raise OSError("unsafe config target")
    try:
        info = os.stat(app, dir_fd=config_fd, follow_symlinks=False)
    except FileNotFoundError:
        info = None
    if info is not None and stat.S_ISLNK(info.st_mode):
        raise OSError("unsafe config target")
    return _BoundConfigTarget(
        parent_fd=config_fd,
        name=app,
        path=_proc_fd_path(config_fd) / app,
        display_path=get_env().config_dir / app,
    )


@contextmanager
def _opened_deployed_config(target: _BoundConfigTarget) -> Iterator[Path]:
    """Bind the just-published app item before chmod or template rendering."""
    fd = os.open(target.name, _READ_FLAGS, dir_fd=target.parent_fd)
    try:
        info = os.fstat(fd)
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise OSError("unsafe deployed config type")
        yield _proc_fd_path(fd)
    finally:
        os.close(fd)


def _open_official_preset_fd_at(
    repo_app: _BoundRepoApp,
    name: str,
) -> Optional[int]:
    """Bind an official preset below one already-bound repo app."""
    if not stat.S_ISDIR(repo_app.info.st_mode):
        return None
    try:
        presets_fd = _open_dir_at(repo_app.fd, "presets")
    except FileNotFoundError:
        return None
    try:
        try:
            return _open_dir_at(presets_fd, name)
        except FileNotFoundError:
            return None
    finally:
        os.close(presets_fd)


def _open_official_preset_fd(app: str, name: str) -> Optional[int]:
    """Bind an official preset, returning None only when it is absent."""
    with _opened_repo_app(app) as repo_app:
        return _open_official_preset_fd_at(repo_app, name)


def _open_user_preset_fd_at(
    presets_fd: int,
    app: str,
    name: str,
) -> Optional[int]:
    """Bind a user preset, returning None only when it is absent."""
    try:
        with _opened_user_app_at(presets_fd, app) as app_fd:
            try:
                return _open_dir_at(app_fd, name)
            except FileNotFoundError:
                return None
    except FileNotFoundError:
        return None


def _open_user_preset_fd(app: str, name: str) -> Optional[int]:
    """Bind a user preset through a newly opened config root."""
    try:
        with _opened_presets_dir() as presets_fd:
            return _open_user_preset_fd_at(presets_fd, app, name)
    except FileNotFoundError:
        return None


@dataclass(frozen=True)
class _BoundPresetSource:
    fd: int
    path: Path
    display_path: Path
    source: str


@contextmanager
def _opened_preset_source(
    app: str,
    name: str,
    *,
    presets_fd: Optional[int] = None,
    paths: Optional["_AppPaths"] = None,
    repo_app: Optional[_BoundRepoApp] = None,
) -> Iterator[_BoundPresetSource]:
    """Bind a default, official, or user source until its consumer finishes."""
    paths = paths or _app_paths(app)
    if paths is None or not _is_safe_component(name):
        raise OSError("unsafe preset path")

    fd: Optional[int] = None
    display_path: Optional[Path] = None
    source = "official"
    try:
        if name == "default":
            fd = os.dup(repo_app.fd) if repo_app is not None else _open_repo_app_fd(app)[0]
            display_path = paths.source
        else:
            fd = (
                _open_official_preset_fd_at(repo_app, name)
                if repo_app is not None
                else _open_official_preset_fd(app, name)
            )
            if fd is not None:
                display_path = paths.source / "presets" / name
            else:
                fd = (
                    _open_user_preset_fd_at(presets_fd, app, name)
                    if presets_fd is not None
                    else _open_user_preset_fd(app, name)
                )
                if fd is not None:
                    display_path = paths.user_presets / name
                    source = "user"
        if fd is None or display_path is None:
            raise FileNotFoundError(name)
        yield _BoundPresetSource(
            fd=fd,
            path=_proc_fd_path(fd),
            display_path=display_path,
            source=source,
        )
    finally:
        if fd is not None:
            os.close(fd)


def _assert_bound_path(path: Path, fd: int) -> None:
    try:
        current = os.stat(path, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise OSError("preset path changed during operation") from exc
    bound = os.fstat(fd)
    if not stat.S_ISDIR(current.st_mode) or not _same_inode(current, bound):
        raise OSError("preset path changed during operation")


def _remove_tree_at(parent_fd: int, name: str, *, parent_path: Optional[Path] = None) -> None:
    """Recursively remove one bound directory without following symlinks."""
    if parent_path is not None:
        _assert_bound_path(parent_path, parent_fd)
    child_fd = _open_dir_at(parent_fd, name)
    original = os.fstat(child_fd)
    try:
        for entry in os.listdir(child_fd):
            info = os.stat(entry, dir_fd=child_fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                _remove_tree_at(child_fd, entry)
            else:
                os.unlink(entry, dir_fd=child_fd)
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(current.st_mode) or not _same_inode(original, current):
            raise OSError("preset path changed during removal")
        os.rmdir(name, dir_fd=parent_fd)
    finally:
        os.close(child_fd)


def _remove_entry_at(parent_fd: int, name: str) -> None:
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISDIR(info.st_mode):
        _remove_tree_at(parent_fd, name)
    else:
        os.unlink(name, dir_fd=parent_fd)


def _random_leaf(prefix: str) -> str:
    return f".{prefix}.{secrets.token_hex(16)}"


def _copy_tree_at(
    src_fd: int,
    parent_fd: int,
    name: str,
    *,
    parent_path: Optional[Path] = None,
) -> None:
    """Copy a bound tree to staging and publish it below one bound parent."""
    stage = _random_leaf("preset-new")
    os.mkdir(stage, mode=0o700, dir_fd=parent_fd)
    stage_fd = _open_dir_at(parent_fd, stage)
    stage_info = os.fstat(stage_fd)
    published = False
    backup: Optional[str] = None
    backup_info: Optional[os.stat_result] = None
    try:
        shutil.copytree(
            _proc_fd_path(src_fd),
            _proc_fd_path(stage_fd),
            dirs_exist_ok=True,
            symlinks=True,
            ignore=_ignore_custom_and_manifest,
        )
        if parent_path is not None:
            _assert_bound_path(parent_path, parent_fd)
        if not _entry_matches_at(parent_fd, stage, stage_info):
            raise OSError("preset staging directory changed before publish")

        try:
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            current = None
        if current is not None:
            if not stat.S_ISDIR(current.st_mode):
                raise OSError("unsafe preset target type")
            backup = _random_leaf("preset-old")
            try:
                os.stat(backup, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise OSError("preset backup path collision")
            os.rename(name, backup, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            backup_info = current
            if not _entry_matches_at(parent_fd, backup, current):
                raise OSError("preset target changed while creating backup")

        try:
            if not _entry_matches_at(parent_fd, stage, stage_info):
                raise OSError("preset staging directory changed before publish")
            os.rename(stage, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            if not _entry_matches_at(parent_fd, name, stage_info):
                raise OSError("preset staging directory changed during publish")
            published = True
        except Exception:
            if (
                backup is not None
                and backup_info is not None
                and _entry_matches_at(parent_fd, backup, backup_info)
            ):
                try:
                    os.rename(
                        backup,
                        name,
                        src_dir_fd=parent_fd,
                        dst_dir_fd=parent_fd,
                    )
                except OSError:
                    pass
                else:
                    backup = None
                    backup_info = None
            raise

        if backup is not None:
            try:
                if backup_info is None or not _entry_matches_at(
                    parent_fd,
                    backup,
                    backup_info,
                ):
                    raise OSError("preset backup changed before cleanup")
                _remove_entry_at(parent_fd, backup)
            except OSError as exc:
                log_msg("WARN", f"Old preset retained after publish for {name}: {exc}")
            else:
                backup = None
                backup_info = None
    finally:
        os.close(stage_fd)
        if not published and _entry_matches_at(parent_fd, stage, stage_info):
            try:
                _remove_entry_at(parent_fd, stage)
            except OSError:
                pass
        if (
            published
            and backup is not None
            and backup_info is not None
            and _entry_matches_at(parent_fd, backup, backup_info)
        ):
            try:
                _remove_entry_at(parent_fd, backup)
            except OSError:
                pass


def _confined_child(root: Path, *parts: str) -> Optional[Path]:
    """Join leaf parts under root, rejecting traversal and symlink escapes."""
    if not all(_is_safe_component(part) for part in parts):
        return None
    candidate = root.joinpath(*parts)
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        return None

    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            return None
    return candidate


@dataclass(frozen=True)
class _AppPaths:
    source: Path
    dest: Path
    user_presets: Path


def _app_paths(app: str) -> Optional[_AppPaths]:
    """Resolve every app-owned path after checking the deployable app boundary."""
    if not _is_safe_component(app):
        return None

    from nyxniri.deploy.manifest import discover_deployable_apps

    try:
        if app not in discover_deployable_apps():
            return None
    except Exception:
        return None

    env = get_env()
    if (env.config_dir.exists() and not env.config_dir.is_dir()) or (
        env.presets_dir.exists() and not env.presets_dir.is_dir()
    ):
        return None
    source = _confined_child(env.configs_src, app)
    dest = _confined_child(env.config_dir, app)
    user_presets = _confined_child(env.presets_dir, app)
    if None in (source, dest, user_presets):
        return None
    if user_presets.exists() and not user_presets.is_dir():
        return None
    return _AppPaths(source=source, dest=dest, user_presets=user_presets)


def _active_snapshot(
    info: os.stat_result,
    data: bytes,
) -> _ActiveSlotSnapshot:
    return _ActiveSlotSnapshot(
        exists=True,
        device=info.st_dev,
        inode=info.st_ino,
        mode=info.st_mode,
        size=info.st_size,
        mtime_ns=info.st_mtime_ns,
        ctime_ns=info.st_ctime_ns,
        digest=hashlib.sha256(data).digest(),
    )


def _read_active_at(presets_fd: int, app: str) -> ActivePresetState:
    """Read one active slot through an already-bound preset directory."""
    try:
        fd = os.open(f"{app}.active", _READ_FLAGS, dir_fd=presets_fd)
    except FileNotFoundError:
        return ActivePresetState(
            ActivePresetStatus.MISSING,
            "default",
            _ActiveSlotSnapshot(exists=False),
        )
    except OSError:
        return ActivePresetState(ActivePresetStatus.INVALID, None)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > _ACTIVE_MAX_BYTES:
            return ActivePresetState(
                ActivePresetStatus.INVALID,
                None,
                _active_snapshot(before, b""),
            )
        data = b""
        while len(data) <= _ACTIVE_MAX_BYTES:
            chunk = os.read(fd, _ACTIVE_MAX_BYTES + 1 - len(data))
            if not chunk:
                break
            data += chunk
        if len(data) > _ACTIVE_MAX_BYTES:
            return ActivePresetState(
                ActivePresetStatus.INVALID,
                None,
                _active_snapshot(before, data),
            )
        after = os.fstat(fd)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if before_identity != after_identity:
            return ActivePresetState(ActivePresetStatus.INVALID, None)
        snapshot = _active_snapshot(after, data)
    except OSError:
        return ActivePresetState(ActivePresetStatus.INVALID, None)
    finally:
        os.close(fd)

    try:
        selected = data.decode("utf-8")
    except UnicodeDecodeError:
        return ActivePresetState(ActivePresetStatus.INVALID, None, snapshot)
    if not _is_safe_component(selected):
        return ActivePresetState(ActivePresetStatus.INVALID, None, snapshot)
    return ActivePresetState(ActivePresetStatus.VALID, selected, snapshot)


def _active_state_unchanged_at(
    presets_fd: int,
    app: str,
    expected: ActivePresetState,
) -> bool:
    """Confirm the active slot is still the exact snapshot previously read."""
    if expected._snapshot is None:
        return False
    current = _read_active_at(presets_fd, app)
    return (
        current.status is expected.status
        and current.selected == expected.selected
        and current._snapshot == expected._snapshot
    )


def read_active_preset_state(app: str) -> ActivePresetState:
    """Read missing, valid, or invalid active state without retaining bad data."""
    if _app_paths(app) is None:
        return ActivePresetState(ActivePresetStatus.INVALID, None)
    try:
        with _opened_presets_dir() as presets_fd:
            return _read_active_at(presets_fd, app)
    except FileNotFoundError:
        return ActivePresetState(ActivePresetStatus.MISSING, "default")
    except (OSError, RuntimeError, ValueError):
        return ActivePresetState(ActivePresetStatus.INVALID, None)


def read_active_preset(app: str) -> str:
    """Return a validated selection, default when missing, or raise if invalid."""
    state = read_active_preset_state(app)
    if state.status is ActivePresetStatus.INVALID or state.selected is None:
        raise InvalidActivePresetError("invalid active preset state")
    return state.selected


def _validate_active_slot(presets_fd: int, app: str) -> None:
    """Allow a missing or regular active slot and reject every other type."""
    try:
        info = os.stat(f"{app}.active", dir_fd=presets_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(info.st_mode):
        raise OSError("unsafe active preset slot")


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short active preset write")
        view = view[written:]


def _write_active_at(presets_fd: int, app: str, name: str) -> None:
    """Write and publish one active state through a bound directory fd."""
    _validate_active_slot(presets_fd, app)
    tmp: Optional[str] = None
    fd: Optional[int] = None
    published = False
    verified = False
    try:
        for _ in range(128):
            candidate = _random_leaf("active-tmp")
            try:
                fd = os.open(
                    candidate,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                    dir_fd=presets_fd,
                )
                tmp = candidate
                break
            except FileExistsError:
                continue
        if fd is None or tmp is None:
            raise FileExistsError("cannot allocate active preset temp file")

        _write_all(fd, name.encode("utf-8"))
        os.fsync(fd)
        staged = os.fstat(fd)
        visible = os.stat(tmp, dir_fd=presets_fd, follow_symlinks=False)
        if not stat.S_ISREG(visible.st_mode) or not _same_inode(staged, visible):
            raise OSError("active preset temp file changed before publish")

        os.replace(
            tmp,
            f"{app}.active",
            src_dir_fd=presets_fd,
            dst_dir_fd=presets_fd,
        )
        tmp = None
        published = True
        published_info = os.stat(
            f"{app}.active",
            dir_fd=presets_fd,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(published_info.st_mode) or not _same_inode(
            staged,
            published_info,
        ):
            raise OSError("active preset changed during publish")
        verified = True
        os.fsync(presets_fd)
    except OSError as exc:
        raise ActivePresetWriteError(published, verified, str(exc)) from exc
    finally:
        if fd is not None:
            os.close(fd)
        if tmp is not None:
            try:
                os.unlink(tmp, dir_fd=presets_fd)
            except OSError:
                pass


def write_active_preset(app: str, name: str) -> None:
    """Atomically write the active preset file (temp + rename).

    Empty or malformed state freezes deployment, while exclusive staging keeps
    incomplete data from ever becoming the visible active slot (§3.2).
    """
    paths = _app_paths(app)
    if paths is None:
        raise ValueError("invalid preset app")
    if not _is_safe_component(name):
        raise ValueError("invalid preset name")
    with _opened_presets_dir(create=True) as presets_fd:
        _write_active_at(presets_fd, app, name)


@dataclass
class PresetSrcResult:
    """Outcome of resolving an app's active preset to a deploy source."""

    src: Optional[Path]          # None → freeze dest, skip deploy (preset not found)
    reset_active: Optional[str]  # write this before deploy (dest-missing reset to default)
    warnings: List[str] = field(default_factory=list)


def _coerce_active_state(active: Union[str, ActivePresetState]) -> ActivePresetState:
    if isinstance(active, ActivePresetState):
        return active
    if _is_safe_component(active):
        return ActivePresetState(ActivePresetStatus.VALID, active)
    return ActivePresetState(ActivePresetStatus.INVALID, None)


def _preset_tree_is_safe(presets_fd: Optional[int] = None) -> bool:
    if presets_fd is not None:
        try:
            stat_result = os.fstat(presets_fd)
            return stat.S_ISDIR(stat_result.st_mode)
        except OSError:
            return False
    try:
        with _opened_presets_dir():
            return True
    except FileNotFoundError:
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def _bound_item_is_missing(path: Path) -> bool:
    """Check a bound config leaf without following a raced symlink."""
    try:
        info = os.stat(path, follow_symlinks=False)
    except FileNotFoundError:
        return True
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise OSError("unsafe config target type")
    return False


def resolve_preset_src(
    app: str,
    active: Union[str, ActivePresetState],
    dest: Path,
    *,
    presets_fd: Optional[int] = None,
    bound_dest: Optional[Path] = None,
) -> PresetSrcResult:
    """Compatibility wrapper around the bound four-branch resolver."""
    state = _coerce_active_state(active)
    try:
        with _opened_resolved_preset_source(
            app,
            state,
            dest,
            presets_fd=presets_fd,
            bound_dest=bound_dest or dest,
            repo_app=None,
        ) as (result, _selected, _source):
            return result
    except OSError:
        return PresetSrcResult(
            src=None,
            reset_active=None,
            warnings=[msg("preset_warn_invalid_active", app)],
        )


@contextmanager
def _opened_resolved_preset_source(
    app: str,
    active: ActivePresetState,
    dest: Path,
    *,
    presets_fd: Optional[int],
    bound_dest: Path,
    repo_app: Optional[_BoundRepoApp],
) -> Iterator[
    Tuple[PresetSrcResult, Optional[str], Optional[_BoundPresetSource]]
]:
    """Resolve and retain the selected source fd through its one consumer."""
    paths = _app_paths(app)
    if (
        paths is None
        or dest != paths.dest
        or not _preset_tree_is_safe(presets_fd)
        or active.status is ActivePresetStatus.INVALID
        or active.selected is None
    ):
        warning = (
            msg("preset_warn_invalid_active", app)
            if active.status is ActivePresetStatus.INVALID
            else msg("preset_invalid_app")
        )
        yield PresetSrcResult(None, None, [warning]), None, None
        return

    selected = active.selected
    reset_active: Optional[str] = None
    warnings: List[str] = []
    if _bound_item_is_missing(bound_dest) and selected != "default":
        try:
            with _opened_preset_source(
                app,
                selected,
                presets_fd=presets_fd,
                paths=paths,
                repo_app=repo_app,
            ):
                pass
        except FileNotFoundError:
            warnings.append(msg("preset_warn_upstream_removed", app, selected))
        selected = "default"
        reset_active = "default"

    try:
        with _opened_preset_source(
            app,
            selected,
            presets_fd=presets_fd,
            paths=paths,
            repo_app=repo_app,
        ) as source:
            yield (
                PresetSrcResult(source.display_path, reset_active, warnings),
                selected,
                source,
            )
    except FileNotFoundError:
        yield (
            PresetSrcResult(
                None,
                None,
                [msg("preset_warn_frozen", app, selected)],
            ),
            None,
            None,
        )


# --- CLI-facing operations ----------------------------------------------------

def _find_preset_src(app: str, name: str) -> Optional[Path]:
    """Direct lookup of a named preset (apply flow). No dest-missing reset.

    Distinct from resolve_preset_src (update flow): apply is an explicit user
    choice, so a missing dest does not silently reset to default — the named
    preset is deployed as-is. 'default' resolves to the app root.
    """
    try:
        with _opened_preset_source(app, name) as bound:
            return bound.display_path
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None


@dataclass
class PresetInfo:
    """Metadata inspection for an app preset."""
    app: str
    name: str
    source: str          # 'official' | 'user'
    is_active: bool
    path: str
    files: List[str]
    preserve: List[str]
    is_editable: bool
    is_deletable: bool


def get_preset_info(app: str, name: str) -> PresetInfo:
    """Inspect detailed metadata and key files for an app preset."""
    from nyxniri.deploy.manifest import load_manifest_for

    paths = _app_paths(app)
    state = read_active_preset_state(app)
    is_active = (
        state.status is not ActivePresetStatus.INVALID
        and state.selected == name
    )
    source = "official"
    is_editable = False
    is_deletable = False
    files: List[str] = []

    if paths is None or not _is_safe_component(name):
        rel_path = "(invalid)"
    else:
        try:
            with _opened_preset_source(app, name) as bound:
                source = bound.source
                is_editable = source == "user"
                is_deletable = source == "user"
                if name == "default":
                    rel_path = f"configs/{app}"
                elif source == "official":
                    rel_path = f"configs/{app}/presets/{name}"
                else:
                    rel_path = f"~/.config/NyxNiri/presets/{app}/{name}"

                if stat.S_ISDIR(os.fstat(bound.fd).st_mode):
                    for p in sorted(bound.path.rglob("*")):
                        if p.is_file() and not p.name.startswith(".") and "__custom__" not in p.name:
                            try:
                                rel = p.relative_to(bound.path)
                            except ValueError:
                                continue
                            if name == "default" and rel.parts and rel.parts[0] == "presets":
                                continue
                            files.append(str(rel))
        except (FileNotFoundError, OSError, RuntimeError, ValueError):
            rel_path = f"configs/{app}/presets/{name} (not found)"
            source = "official"
            is_editable = False
            is_deletable = False

    preserve: List[str] = []
    try:
        if paths is not None:
            manifest = load_manifest_for(app)
            preserve = manifest.preserve or []
    except Exception:
        pass

    return PresetInfo(
        app=app,
        name=name,
        source=source,
        is_active=is_active,
        path=rel_path,
        files=files,
        preserve=preserve,
        is_editable=is_editable,
        is_deletable=is_deletable,
    )


def collect_presets(app: str) -> List[Tuple[str, str, bool]]:
    """Return (name, source, is_active) for every preset of an app.

    source is 'official' (shipped in repo) or 'user' (saved under nyx_dir).
    'default' is always first. Used by list_presets (printing) and the TUI
    switcher (data only) — no side effects.
    """
    paths = _app_paths(app)
    if paths is None or not _preset_tree_is_safe():
        return []

    state = read_active_preset_state(app)
    active = state.selected if state.status is not ActivePresetStatus.INVALID else None
    entries: List[Tuple[str, str, bool]] = [("default", "official", active == "default")]

    try:
        app_fd, app_info = _open_repo_app_fd(app)
        try:
            if stat.S_ISDIR(app_info.st_mode):
                try:
                    official_fd = _open_dir_at(app_fd, "presets")
                except FileNotFoundError:
                    official_fd = None
                if official_fd is not None:
                    try:
                        for name in sorted(os.listdir(official_fd)):
                            if not _is_safe_component(name):
                                continue
                            info = os.stat(name, dir_fd=official_fd, follow_symlinks=False)
                            if stat.S_ISDIR(info.st_mode):
                                entries.append((name, "official", active == name))
                    finally:
                        os.close(official_fd)
        finally:
            os.close(app_fd)
    except (OSError, RuntimeError, ValueError):
        return []

    try:
        with _opened_user_app(app) as user_fd:
            for name in sorted(os.listdir(user_fd)):
                if not _is_safe_component(name):
                    continue
                info = os.stat(name, dir_fd=user_fd, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    entries.append((name, "user", active == name))
    except FileNotFoundError:
        pass
    except (OSError, RuntimeError, ValueError):
        return []
    return entries


def list_presets(app: str) -> Optional[List[Tuple[str, str, bool]]]:
    """List presets for an app; the active one is marked. ``list`` is status.

    Prints a numbered list with the active entry prefixed by ``*``.
    """
    if _app_paths(app) is None:
        print(msg("preset_invalid_app"))
        return None
    state = read_active_preset_state(app)
    invalid = state.status is ActivePresetStatus.INVALID
    if invalid:
        print(msg("preset_warn_invalid_active", app))
    entries = collect_presets(app)
    print(msg("preset_list_title", app))
    for i, (name, source, is_active) in enumerate(entries, 1):
        marker = "*" if is_active else " "
        tag = msg(f"preset_src_{source}")
        print(f"  {marker} [{i}] {name}  {Colors.DIM}{tag}{Colors.RESET}")
    return None if invalid else entries


def _render_preset_result(app: str, name: str, preserved_lines: List[str], failed: bool = False) -> None:
    """Lightweight feedback reusing the completion screen's preserved section."""
    if failed:
        print(msg("preset_apply_failed", app, name))
        return
    print(msg("preset_applied", app, name))
    if preserved_lines:
        print(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_preserved')}{Colors.RESET}")
        for pline in sorted(set(preserved_lines)):
            print(f"    {pline}")


def _operation_paths(app: str, name: str) -> Optional[_AppPaths]:
    """Validate CLI-facing identifiers and return their confined app paths."""
    paths = _app_paths(app)
    if paths is None:
        print(msg("preset_invalid_app"))
        return None
    if not _is_safe_component(name):
        print(msg("preset_invalid_name"))
        return None
    return paths


def apply_preset(app: str, name: str) -> bool:
    """Switch an app to a named preset (narrow deploy path).

    Runs only atomic_replace + template render for this app — no hardware
    patches, no post-install services (§9: switching kitty must not rerun
    fisher). Writes the active file AFTER deploy succeeds (iron law, §3.2).

    The manifest ``preserve`` list (e.g. niri/monitor.kdl, niri/effects.kdl) is
    honoured just like the full-deploy path: a preset switch must not wipe
    runtime-managed files the new variant doesn't ship.
    """
    from nyxniri.deploy.templates import _phase_render_templates
    from nyxniri.deploy.atomic import atomic_replace_item_transaction
    from nyxniri.deploy.manifest import load_manifest_at

    preserved_log: List[str] = []
    active_not_durable = False
    try:
        with _opened_root(get_env().config_dir, create=True) as config_fd:
            paths = _operation_paths(app, name)
            if paths is None:
                return False
            dest = paths.dest

            with _opened_repo_app(app) as repo_app, \
                 _opened_presets_dir_at(config_fd, create=True) as presets_fd, \
                 _opened_preset_source(
                     app,
                     name,
                     presets_fd=presets_fd,
                     paths=paths,
                     repo_app=repo_app,
                 ) as source:
                manifest = load_manifest_at(
                    app,
                    repo_app.fd,
                    repo_app.info,
                    repo_app.root_fd,
                )
                preserve = manifest.preserve or None
                target = _bound_config_target(config_fd, app)
                _validate_active_slot(presets_fd, app)
                with atomic_replace_item_transaction(
                    source.path,
                    target.path,
                    preserved_log=preserved_log,
                    preserve=preserve,
                    display_dest=dest,
                ) as swap:
                    _phase_render_templates(only_app=app, app_root=swap.path)
                    # deploy-then-write: a crash mid-flow must not leave active pointing
                    # at a preset whose deploy did not complete. §3.2
                    try:
                        _write_active_at(presets_fd, app, name)
                    except ActivePresetWriteError as exc:
                        if exc.published:
                            swap.commit()
                        if not exc.verified:
                            raise
                        active_not_durable = True
                    else:
                        swap.commit()
    except FileNotFoundError:
        print(msg("preset_not_found", app, name))
        return False
    except (OSError, RuntimeError, ValueError):
        print(msg("preset_path_unsafe"))
        return False
    _render_preset_result(app, name, preserved_log)
    if active_not_durable:
        print(msg("preset_active_not_durable"))
    return True


def _ignore_custom_and_manifest(_src_dir, names):
    """copytree ignore: drop __custom__ entries (any depth) and .module.toml."""
    return {n for n in names if "__custom__" in n or n == ".module.toml"}


def save_preset(app: str, name: str) -> bool:
    """Snapshot current ~/.config/<app>/ into a user preset, minus __custom__.

    'default' is reserved (apply default = reset). Official-name collisions
    are rejected (official presets win on name). §2.2
    """
    if name == "default":
        print(msg("preset_name_reserved", name))
        return False
    try:
        with _opened_root(get_env().config_dir, create=True) as config_fd:
            paths = _operation_paths(app, name)
            if paths is None:
                return False
            official_fd = _open_official_preset_fd(app, name)
            if official_fd is not None:
                os.close(official_fd)
                print(msg("preset_official_name_collision", name))
                return False

            src_fd = _open_dir_at(config_fd, app)
            try:
                with _opened_presets_dir_at(config_fd, create=True) as presets_fd, \
                     _opened_user_app_at(presets_fd, app, create=True) as user_fd:
                    _copy_tree_at(
                        src_fd,
                        user_fd,
                        name,
                        parent_path=paths.user_presets,
                    )
            finally:
                os.close(src_fd)
    except FileNotFoundError:
        print(msg("preset_nothing_to_save", app))
        return False
    except (OSError, RuntimeError, ValueError):
        print(msg("preset_path_unsafe"))
        return False
    print(msg("preset_saved", app, name))
    return True


def delete_preset(app: str, name: str) -> bool:
    """Delete a user preset. Official presets cannot be deleted. §2.5"""
    if name == "default":
        print(msg("preset_name_reserved", name))
        return False
    try:
        with _opened_root(get_env().config_dir) as config_fd:
            paths = _operation_paths(app, name)
            if paths is None:
                return False
            official_fd = _open_official_preset_fd(app, name)
            if official_fd is not None:
                os.close(official_fd)
                print(msg("preset_delete_official_denied", name))
                return False
            with _opened_presets_dir_at(config_fd) as presets_fd, \
                 _opened_user_app_at(presets_fd, app) as user_fd:
                info = os.stat(name, dir_fd=user_fd, follow_symlinks=False)
                if not stat.S_ISDIR(info.st_mode):
                    raise OSError("unsafe preset target type")
                _remove_tree_at(user_fd, name, parent_path=paths.user_presets)
    except FileNotFoundError:
        print(msg("preset_not_found", app, name))
        return False
    except (OSError, RuntimeError, ValueError):
        print(msg("preset_path_unsafe"))
        return False
    print(msg("preset_deleted", app, name))
    return True

def edit_preset(app: str, name: str) -> bool:
    """Open a user preset's directory in $EDITOR (rejects default + official).

    Default is reserved; official presets are repo-owned read-only. Only user
    presets under ~/.config/NyxNiri/presets/<app>/<name>/ are editable in place;
    re-running ``apply <name>`` deploys the edits. Non-interactive → hint path.
    """
    if name == "default":
        print(msg("preset_name_reserved", name))
        return False
    user_fd: Optional[int] = None
    try:
        with _opened_root(get_env().config_dir) as config_fd:
            paths = _operation_paths(app, name)
            if paths is None:
                return False
            official_fd = _open_official_preset_fd(app, name)
            if official_fd is not None:
                os.close(official_fd)
                print(msg("preset_edit_official_denied", name))
                return False
            with _opened_presets_dir_at(config_fd) as presets_fd:
                user_fd = _open_user_preset_fd_at(presets_fd, app, name)
                if user_fd is None:
                    print(msg("preset_not_found", app, name))
                    return False
                if not sys.stdin.isatty():
                    print(msg("preset_edit_notty", paths.user_presets / name))
                    return False
                editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
                subprocess.run(
                    [editor, str(_proc_fd_path(user_fd))],
                    check=False,
                    pass_fds=(user_fd,),
                )
    except FileNotFoundError:
        print(msg("preset_not_found", app, name))
        return False
    except (OSError, RuntimeError, ValueError):
        print(msg("preset_path_unsafe"))
        return False
    finally:
        if user_fd is not None:
            os.close(user_fd)
    print(msg("preset_edit_opened", app, name))
    return True
