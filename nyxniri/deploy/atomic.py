"""Atomic swap deployment + Dunder preservation + manifest-declared snapshots.

The atomic_replace_item stage-preserve-swap flow is the heart of NyxNiri's deploy
(§7.1). Two preserve mechanisms live here and stay deliberately separate
(§3.2): the Dunder __custom__ walk (magic filename) and the manifest
``preserve`` snapshot (files referenced by name, e.g. niri/monitor.kdl).
"""

import ctypes
import errno
import os
import secrets
import shutil
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Tuple

from nyxniri.core import get_env, log_msg, register_temp_path, remove_path
from nyxniri.i18n import msg


_RENAME_NOREPLACE = 1
_RENAME_EXCHANGE = 2
_LIBC = ctypes.CDLL(None, use_errno=True)
_RENAMEAT2 = getattr(_LIBC, "renameat2", None)
if _RENAMEAT2 is not None:
    _RENAMEAT2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    _RENAMEAT2.restype = ctypes.c_int


def _deploy_ignore_factory(root_src: Path):
    """copytree ignore: drop repo-only entries that must not ship to ~/.config.

    - .module.toml: self-describing manifest (NyxNiri metadata, §10.4 boundary)
    - __pycache__: bytecode cache, never user config
    - presets/: top-level variant source tree (only at app root, not nested)
    """
    root = root_src

    def _ignore(src_dir, names):
        skip = {n for n in names if n in ("__pycache__", ".module.toml")}
        if Path(src_dir) == root and "presets" in names:
            skip.add("presets")
        return skip

    return _ignore


_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _random_sibling(dest: Path, kind: str) -> Path:
    return dest.with_name(f".{dest.name}.{kind}.{secrets.token_hex(16)}")


def _renameat2(
    src_dir_fd: int,
    src: str,
    dst_dir_fd: int,
    dst: str,
    flags: int,
) -> None:
    """Invoke Linux renameat2 or fail closed when the primitive is unavailable."""
    if _RENAMEAT2 is None:
        raise OSError(errno.ENOSYS, "renameat2 is unavailable")
    result = _RENAMEAT2(
        src_dir_fd,
        os.fsencode(src),
        dst_dir_fd,
        os.fsencode(dst),
        flags,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _stat_at(parent_fd: int, name: str) -> Optional[os.stat_result]:
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _entry_matches_at(
    parent_fd: int,
    name: str,
    expected: os.stat_result,
) -> bool:
    current = _stat_at(parent_fd, name)
    return current is not None and _same_inode(current, expected)


def _copy_stat_to_fd(source: os.stat_result, target_fd: int) -> None:
    """Copy the portable metadata used by copytree without reopening a path."""
    os.fchmod(target_fd, stat.S_IMODE(source.st_mode))
    os.utime(target_fd, ns=(source.st_atime_ns, source.st_mtime_ns))


def _copy_bound_tree(
    source_fd: int,
    target_fd: int,
    *,
    ignore: Optional[Callable[[str, bool], bool]] = None,
    _is_root: bool = True,
) -> None:
    """Copy one held directory into another without following target children."""
    for name in os.listdir(source_fd):
        if ignore is not None and ignore(name, _is_root):
            continue

        source_info = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
        if stat.S_ISLNK(source_info.st_mode):
            link_target = os.readlink(name, dir_fd=source_fd)
            if not _entry_matches_at(source_fd, name, source_info):
                raise OSError("deploy source symlink changed while reading")
            os.symlink(link_target, name, dir_fd=target_fd)
            continue

        if stat.S_ISREG(source_info.st_mode):
            input_fd = os.open(name, _READ_FLAGS, dir_fd=source_fd)
            output_fd: Optional[int] = None
            try:
                if not _same_inode(source_info, os.fstat(input_fd)):
                    raise OSError("deploy source file changed while binding")
                output_fd = os.open(
                    name,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | os.O_NOFOLLOW
                    | os.O_CLOEXEC,
                    0o600,
                    dir_fd=target_fd,
                )
                with os.fdopen(os.dup(input_fd), "rb", closefd=True) as source, \
                     os.fdopen(os.dup(output_fd), "wb", closefd=True) as target:
                    shutil.copyfileobj(source, target)
                    target.flush()
                    os.fsync(target.fileno())
                _copy_stat_to_fd(source_info, output_fd)
            finally:
                if output_fd is not None:
                    os.close(output_fd)
                os.close(input_fd)
            continue

        if stat.S_ISDIR(source_info.st_mode):
            input_fd = os.open(name, _DIR_FLAGS, dir_fd=source_fd)
            output_fd: Optional[int] = None
            try:
                if not _same_inode(source_info, os.fstat(input_fd)):
                    raise OSError("deploy source directory changed while binding")
                os.mkdir(name, mode=0o700, dir_fd=target_fd)
                output_fd = os.open(name, _DIR_FLAGS, dir_fd=target_fd)
                output_info = os.fstat(output_fd)
                if not _entry_matches_at(target_fd, name, output_info):
                    raise OSError("deploy target directory changed while binding")
                _copy_bound_tree(
                    input_fd,
                    output_fd,
                    ignore=ignore,
                    _is_root=False,
                )
                if not _entry_matches_at(target_fd, name, output_info):
                    raise OSError("deploy target directory changed while copying")
                _copy_stat_to_fd(source_info, output_fd)
            finally:
                if output_fd is not None:
                    os.close(output_fd)
                os.close(input_fd)
            continue

        raise OSError("unsupported deploy source entry type")


@dataclass
class _BoundStage:
    name: str
    fd: int
    info: os.stat_result
    is_dir: bool


def _open_directory_path(path: Path) -> int:
    if path.parent == Path("/proc/self/fd") and path.name.isdecimal():
        fd = os.dup(int(path.name))
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            os.close(fd)
            raise OSError("bound path is not a directory")
        return fd
    return os.open(path, _DIR_FLAGS)


def _open_source_path(path: Path) -> Tuple[int, os.stat_result]:
    """Open a deploy source once and retain its inode for the full copy."""
    if path.parent == Path("/proc/self/fd") and path.name.isdecimal():
        fd = os.dup(int(path.name))
    else:
        fd = os.open(path, _READ_FLAGS)
    try:
        info = os.fstat(fd)
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise OSError("unsupported deploy source type")
        return fd, info
    except Exception:
        os.close(fd)
        raise


@contextmanager
def _opened_relative_parent(
    root: Path,
    relative: Path,
    *,
    create: bool,
) -> Iterator[Tuple[int, str]]:
    """Bind a relative entry parent without following any path component."""
    parts = relative.parts
    if (
        relative.is_absolute()
        or not parts
        or any(part in ("", ".", "..") for part in parts)
    ):
        raise OSError("unsafe preserved path")

    fd = _open_directory_path(root)
    try:
        for part in parts[:-1]:
            try:
                next_fd = os.open(part, _DIR_FLAGS, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=0o700, dir_fd=fd)
                next_fd = os.open(part, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd, parts[-1]
    finally:
        os.close(fd)


def _remove_bound_entry(parent_fd: int, name: str) -> None:
    info = _stat_at(parent_fd, name)
    if info is None:
        return
    if stat.S_ISDIR(info.st_mode):
        child_fd = os.open(name, _DIR_FLAGS, dir_fd=parent_fd)
        try:
            if not _same_inode(info, os.fstat(child_fd)):
                raise OSError("preserved target changed while binding")
            if not _entry_matches_at(parent_fd, name, info):
                raise OSError("preserved target changed before cleanup")
            _clear_bound_dir(child_fd)
            if not _entry_matches_at(parent_fd, name, info):
                raise OSError("preserved target changed before removal")
            os.rmdir(name, dir_fd=parent_fd)
        finally:
            os.close(child_fd)
    elif _entry_matches_at(parent_fd, name, info):
        os.unlink(name, dir_fd=parent_fd)


def _copy_preserved_entry(
    source_root: Path,
    target_root: Path,
    relative: Path,
    *,
    allow_directory: bool,
) -> bool:
    """Copy one preserved entry through bound parents without following links."""
    try:
        with _opened_relative_parent(
            source_root,
            relative,
            create=False,
        ) as (source_parent, source_name), _opened_relative_parent(
            target_root,
            relative,
            create=True,
        ) as (target_parent, target_name):
            source_info = _stat_at(source_parent, source_name)
            if source_info is None:
                return False
            _remove_bound_entry(target_parent, target_name)

            if stat.S_ISLNK(source_info.st_mode):
                link_target = os.readlink(source_name, dir_fd=source_parent)
                if not _entry_matches_at(source_parent, source_name, source_info):
                    raise OSError("preserved symlink changed while reading")
                os.symlink(link_target, target_name, dir_fd=target_parent)
                return True

            if stat.S_ISREG(source_info.st_mode):
                source_fd = os.open(source_name, _READ_FLAGS, dir_fd=source_parent)
                target_fd: Optional[int] = None
                try:
                    if not _same_inode(source_info, os.fstat(source_fd)):
                        raise OSError("preserved file changed while binding")
                    target_fd = os.open(
                        target_name,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | os.O_NOFOLLOW
                        | os.O_CLOEXEC,
                        stat.S_IMODE(source_info.st_mode),
                        dir_fd=target_parent,
                    )
                    with os.fdopen(
                        os.dup(source_fd),
                        "rb",
                        closefd=True,
                    ) as source_handle, os.fdopen(
                        os.dup(target_fd),
                        "wb",
                        closefd=True,
                    ) as target_handle:
                        shutil.copyfileobj(source_handle, target_handle)
                        target_handle.flush()
                        os.fsync(target_handle.fileno())
                    _copy_stat_to_fd(source_info, target_fd)
                    return True
                finally:
                    if target_fd is not None:
                        os.close(target_fd)
                    os.close(source_fd)

            if allow_directory and stat.S_ISDIR(source_info.st_mode):
                source_fd = os.open(source_name, _DIR_FLAGS, dir_fd=source_parent)
                target_fd: Optional[int] = None
                try:
                    if not _same_inode(source_info, os.fstat(source_fd)):
                        raise OSError("preserved directory changed while binding")
                    os.mkdir(target_name, mode=0o700, dir_fd=target_parent)
                    target_fd = os.open(target_name, _DIR_FLAGS, dir_fd=target_parent)
                    target_info = os.fstat(target_fd)
                    if not _entry_matches_at(target_parent, target_name, target_info):
                        raise OSError("preserved target changed while binding")
                    _copy_bound_tree(source_fd, target_fd)
                    if not _entry_matches_at(target_parent, target_name, target_info):
                        raise OSError("preserved target changed while copying")
                    _copy_stat_to_fd(source_info, target_fd)
                    return True
                finally:
                    if target_fd is not None:
                        os.close(target_fd)
                    os.close(source_fd)
    except FileNotFoundError:
        return False
    return False


def _allocate_stage(parent_fd: int, src: Path, dest: Path) -> _BoundStage:
    source_fd, source_info = _open_source_path(src)
    source_is_dir = stat.S_ISDIR(source_info.st_mode)
    try:
        for _ in range(128):
            candidate = _random_sibling(dest, "new").name
            try:
                if source_is_dir:
                    os.mkdir(candidate, mode=0o700, dir_fd=parent_fd)
                    fd = os.open(
                        candidate,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=parent_fd,
                    )
                else:
                    fd = os.open(
                        candidate,
                        os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                        0o600,
                        dir_fd=parent_fd,
                    )
            except FileExistsError:
                continue
            except Exception:
                if source_is_dir:
                    try:
                        os.rmdir(candidate, dir_fd=parent_fd)
                    except OSError:
                        pass
                raise

            info = os.fstat(fd)
            if not _entry_matches_at(parent_fd, candidate, info):
                # The visible name now belongs to the racer, not this fd. Never
                # unlink it; closing reclaims our inode if it was merely removed.
                os.close(fd)
                raise OSError("deploy staging item changed while binding")

            stage = _BoundStage(candidate, fd, info, source_is_dir)
            try:
                if source_is_dir:
                    _copy_bound_tree(
                        source_fd,
                        fd,
                        ignore=lambda name, is_root: (
                            name in ("__pycache__", ".module.toml")
                            or (is_root and name == "presets")
                        ),
                    )
                    _copy_stat_to_fd(source_info, fd)
                    os.fsync(fd)
                else:
                    with os.fdopen(os.dup(source_fd), "rb", closefd=True) as source, \
                         os.fdopen(os.dup(fd), "wb", closefd=True) as target:
                        shutil.copyfileobj(source, target)
                        target.flush()
                        os.fsync(target.fileno())
                    _copy_stat_to_fd(source_info, fd)
                    os.fsync(fd)
                return stage
            except Exception:
                try:
                    _cleanup_bound_stage(parent_fd, stage)
                finally:
                    os.close(fd)
                raise
        raise FileExistsError("cannot allocate deploy staging item")
    finally:
        os.close(source_fd)


def _clear_bound_dir(fd: int) -> None:
    """Remove contents of a held directory without following child symlinks."""
    for name in os.listdir(fd):
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            child_fd = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=fd,
            )
            try:
                if not _same_inode(info, os.fstat(child_fd)):
                    raise OSError("cleanup child changed while binding")
                if not _entry_matches_at(fd, name, info):
                    raise OSError("cleanup child changed before traversal")
                _clear_bound_dir(child_fd)
                if _entry_matches_at(fd, name, info):
                    os.rmdir(name, dir_fd=fd)
            finally:
                os.close(child_fd)
        elif _entry_matches_at(fd, name, info):
            os.unlink(name, dir_fd=fd)


def _cleanup_bound_stage(parent_fd: int, stage: _BoundStage) -> None:
    """Clean only the held inode and never a replacement at its former name."""
    if not _entry_matches_at(parent_fd, stage.name, stage.info):
        raise OSError("deploy staging item changed before cleanup")
    if stage.is_dir:
        _clear_bound_dir(stage.fd)
        if not _entry_matches_at(parent_fd, stage.name, stage.info):
            raise OSError("deploy staging item changed during cleanup")
        os.rmdir(stage.name, dir_fd=parent_fd)
    else:
        os.unlink(stage.name, dir_fd=parent_fd)


def _copy_preserved_state(
    source: Path,
    target: Path,
    shown_dest: Path,
    preserved_log: Optional[List[str]],
    test_mode: bool,
    preserve: Optional[List[str]],
) -> None:
    """Inject Dunder and manifest-preserved entries into a staged tree."""
    home = get_env().home

    for root, dirs, files in os.walk(source):
        dirs[:] = [name for name in dirs if "__custom__" not in name]
        for name in files:
            if "__custom__" not in name:
                continue
            if test_mode and name in (
                "scratchpad-items__custom__.toml",
                "orbit-items__custom__.toml",
            ):
                continue
            rel = Path(root).relative_to(source) / name
            if not _copy_preserved_entry(
                source,
                target,
                rel,
                allow_directory=False,
            ):
                continue

            rel_display = str(shown_dest.relative_to(home / ".config") / rel)
            print(msg("log_keep_custom_file", rel_display))
            if preserved_log is not None:
                preserved_log.append(f"~/.config/{rel_display}")

    for root, dirs, _ in os.walk(source):
        for name in list(dirs):
            if "__custom__" not in name:
                continue
            dirs.remove(name)
            rel = Path(root).relative_to(source) / name
            if not _copy_preserved_entry(
                source,
                target,
                rel,
                allow_directory=True,
            ):
                continue

            rel_display = str(shown_dest.relative_to(home / ".config") / rel)
            print(msg("log_keep_custom_dir", rel_display))
            if preserved_log is not None:
                preserved_log.append(f"~/.config/{rel_display}/")

    for rel in preserve or []:
        relative = Path(rel)
        if not _copy_preserved_entry(
            source,
            target,
            relative,
            allow_directory=False,
        ):
            continue
        print(msg("log_keep_preserved_file", shown_dest.name, rel))
        if preserved_log is not None:
            preserved_log.append(f"~/.config/{shown_dest.name}/{rel}")


@dataclass
class _BoundSwap:
    """A published swap whose old inode stays owned until commit or rollback."""

    parent_fd: int
    dest_name: str
    shown_dest: Path
    new: _BoundStage
    old: Optional[_BoundStage]
    finalized: bool = False

    @property
    def path(self) -> Path:
        """Expose the published inode without reopening its mutable name."""
        return Path("/proc/self/fd") / str(self.new.fd)

    def _ensure_current(self) -> None:
        if not _entry_matches_at(self.parent_fd, self.dest_name, self.new.info):
            raise OSError("deployed target changed after publish")

    def commit(self) -> None:
        """Finalize the new target and best-effort remove the old inode."""
        if self.finalized:
            return
        self._ensure_current()
        if self.old is not None:
            try:
                _cleanup_bound_stage(self.parent_fd, self.old)
            except OSError as exc:
                log_msg(
                    "WARN",
                    f"Old deploy target retained after publish for {self.shown_dest}: {exc}",
                )
        try:
            os.fsync(self.parent_fd)
        except OSError as exc:
            # The rename is already visible; do not report a false rollback.
            log_msg("WARN", f"Published deploy not fsynced for {self.shown_dest}: {exc}")
        self.finalized = True

    def rollback(self) -> None:
        """Restore the old target, or remove a newly-created target."""
        if self.finalized:
            return
        self._ensure_current()
        if self.old is not None:
            if not _entry_matches_at(self.parent_fd, self.old.name, self.old.info):
                raise OSError("old deploy target changed before rollback")
            _renameat2(
                self.parent_fd,
                self.new.name,
                self.parent_fd,
                self.dest_name,
                _RENAME_EXCHANGE,
            )
            if not _entry_matches_at(self.parent_fd, self.dest_name, self.old.info):
                raise OSError("old deploy target not restored")
        else:
            _renameat2(
                self.parent_fd,
                self.dest_name,
                self.parent_fd,
                self.new.name,
                _RENAME_NOREPLACE,
            )
        try:
            _cleanup_bound_stage(self.parent_fd, self.new)
        except OSError as exc:
            log_msg("WARN", f"Rolled-back deploy stage retained for {self.shown_dest}: {exc}")
        self.finalized = True

    def close(self) -> None:
        os.close(self.new.fd)
        if self.old is not None:
            os.close(self.old.fd)
        os.close(self.parent_fd)


def _begin_bound_swap(
    src: Path,
    dest: Path,
    shown_dest: Path,
    preserved_log: Optional[List[str]],
    test_mode: bool,
    preserve: Optional[List[str]],
) -> _BoundSwap:
    """Prepare and publish one bound swap, leaving cleanup to its owner."""
    parent_fd: Optional[int] = None
    old_fd: Optional[int] = None
    stage: Optional[_BoundStage] = None
    swap: Optional[_BoundSwap] = None
    try:
        if dest.name in ("", ".", ".."):
            raise OSError("unsafe deploy target name")
        parent_fd = _open_directory_path(dest.parent)
        initial = _stat_at(parent_fd, dest.name)
        if initial is not None and not (
            stat.S_ISDIR(initial.st_mode) or stat.S_ISREG(initial.st_mode)
        ):
            raise OSError("unsafe deploy target type")

        if initial is not None:
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
            if stat.S_ISDIR(initial.st_mode):
                flags |= os.O_DIRECTORY
            old_fd = os.open(dest.name, flags, dir_fd=parent_fd)
            if not _same_inode(initial, os.fstat(old_fd)):
                raise OSError("deploy target changed while binding")

        stage = _allocate_stage(parent_fd, src, dest)
        if stage.is_dir and old_fd is not None and stat.S_ISDIR(initial.st_mode):
            _copy_preserved_state(
                Path("/proc/self/fd") / str(old_fd),
                Path("/proc/self/fd") / str(stage.fd),
                shown_dest,
                preserved_log,
                test_mode,
                preserve,
            )
        if not _entry_matches_at(parent_fd, stage.name, stage.info):
            raise OSError("deploy staging item changed before publish")

        current = _stat_at(parent_fd, dest.name)
        if initial is None:
            if current is not None:
                raise OSError("deploy target appeared during staging")
        elif current is None or not _same_inode(initial, current):
            raise OSError("deploy target changed during staging")

        if initial is None:
            _renameat2(parent_fd, stage.name, parent_fd, dest.name, _RENAME_NOREPLACE)
            swap = _BoundSwap(parent_fd, dest.name, shown_dest, stage, None)
        else:
            _renameat2(parent_fd, stage.name, parent_fd, dest.name, _RENAME_EXCHANGE)
            old_stage = _BoundStage(stage.name, old_fd, initial, stat.S_ISDIR(initial.st_mode))
            swap = _BoundSwap(parent_fd, dest.name, shown_dest, stage, old_stage)
        if not _entry_matches_at(parent_fd, dest.name, stage.info):
            raise OSError("deploy staging item changed during publish")
        if swap.old is not None and not _entry_matches_at(parent_fd, swap.old.name, swap.old.info):
            raise OSError("old deploy target changed during publish")
        # Ownership has moved into swap; its close path owns old_fd and parent_fd.
        parent_fd = None
        old_fd = None
        stage = None
        return swap
    except Exception:
        if swap is not None:
            try:
                swap.rollback()
            except OSError:
                pass
            swap.close()
        elif stage is not None:
            try:
                _cleanup_bound_stage(parent_fd, stage)
            except OSError:
                pass
            os.close(stage.fd)
        if old_fd is not None:
            os.close(old_fd)
        if parent_fd is not None:
            os.close(parent_fd)
        raise


@contextmanager
def atomic_replace_item_transaction(
    src: Path,
    dest: Path,
    preserved_log: Optional[List[str]] = None,
    test_mode: bool = False,
    preserve: Optional[List[str]] = None,
    *,
    display_dest: Optional[Path] = None,
) -> Iterator[_BoundSwap]:
    """Publish a bound item and keep it rollback-capable until the caller commits."""
    swap = _begin_bound_swap(
        src,
        dest,
        display_dest or dest,
        preserved_log,
        test_mode,
        preserve,
    )
    try:
        yield swap
    except BaseException:
        if not swap.finalized:
            try:
                swap.rollback()
            except OSError as exc:
                log_msg("ERROR", f"Deploy rollback failed for {swap.shown_dest}: {exc}")
        raise
    else:
        if not swap.finalized:
            swap.rollback()
    finally:
        swap.close()


def _atomic_replace_item_bound(
    src: Path,
    dest: Path,
    shown_dest: Path,
    preserved_log: Optional[List[str]],
    test_mode: bool,
    preserve: Optional[List[str]],
) -> bool:
    """Replace below an already-bound parent without following the target leaf."""
    try:
        with atomic_replace_item_transaction(
            src,
            dest,
            preserved_log=preserved_log,
            test_mode=test_mode,
            preserve=preserve,
            display_dest=shown_dest,
        ) as swap:
            swap.commit()
        return True
    except Exception as exc:
        log_msg("ERROR", f"Atomic replace failed for {shown_dest}: {exc}")
        return False


def _atomic_replace_item_legacy(
    src: Path,
    dest: Path,
    preserved_log: Optional[List[str]],
    test_mode: bool,
    preserve: Optional[List[str]],
) -> bool:
    """Original path-based replacement used by non-preset call sites."""
    pid = os.getpid()
    dest_parent = dest.parent

    if src.is_file():
        tmp_file = dest.with_name(f"{dest.name}.new.{pid}")
        register_temp_path(tmp_file)
        old_dest = None
        try:
            dest_parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp_file)
            if dest.exists() or dest.is_symlink():
                old_dest = dest.with_name(f"{dest.name}.old.{pid}")
                dest.rename(old_dest)
                tmp_file.rename(dest)
                remove_path(old_dest)
            else:
                tmp_file.rename(dest)
            return True
        except Exception as e:
            remove_path(tmp_file)
            if old_dest is not None and old_dest.exists():
                try:
                    old_dest.rename(dest)
                except Exception:
                    pass
            log_msg("ERROR", f"Atomic replace failed for {dest}: {e}")
            return False

    tmp_new = dest.with_name(f"{dest.name}.new.{pid}")
    register_temp_path(tmp_new)
    try:
        dest_parent.mkdir(parents=True, exist_ok=True)
        if tmp_new.exists() or tmp_new.is_symlink():
            remove_path(tmp_new)
        shutil.copytree(src, tmp_new, symlinks=True, ignore=_deploy_ignore_factory(src))
        if dest.is_dir():
            _copy_preserved_state(
                dest,
                tmp_new,
                dest,
                preserved_log,
                test_mode,
                preserve,
            )
        if dest.exists() or dest.is_symlink():
            old_dest = dest.with_name(f"{dest.name}.old.{pid}")
            dest.rename(old_dest)
            try:
                tmp_new.rename(dest)
                remove_path(old_dest)
            except Exception:
                old_dest.rename(dest)
                raise
            return True
        tmp_new.rename(dest)
        return True
    except Exception as e:
        remove_path(tmp_new)
        log_msg("ERROR", f"Atomic replace failed for directory {dest}: {e}")
        return False


def atomic_replace_item(
    src: Path,
    dest: Path,
    preserved_log: Optional[List[str]] = None,
    test_mode: bool = False,
    preserve: Optional[List[str]] = None,
    *,
    display_dest: Optional[Path] = None,
    bind_dest: bool = False,
) -> bool:
    """Atomically replace one item, optionally below an already-bound parent.

    ``bind_dest`` is for callers that pass a ``/proc/self/fd`` parent. It uses
    exclusive random staging and binds an existing directory while preserved
    state is copied. Other callers keep the established path-based behavior.
    """
    if bind_dest:
        return _atomic_replace_item_bound(
            src,
            dest,
            display_dest or dest,
            preserved_log,
            test_mode,
            preserve,
        )
    return _atomic_replace_item_legacy(
        src,
        dest,
        preserved_log,
        test_mode,
        preserve,
    )
