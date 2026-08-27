"""Deploy orchestrator — config discovery, atomic-deploy phase, post-install
services, completion screen, fisher uninstall, and the deploy/test entry points.

Coordinates the deploy/ siblings: atomic (swap+preserve), templates (render),
assets (wallpapers), hardware (NVIDIA patch), manifest (app discovery), preset
(active variant). Modules/state/deps are lazy-imported to avoid cycles.
"""

import os
import shutil
import stat
import subprocess
import sys
import time
from contextlib import ExitStack, nullcontext
from pathlib import Path
from typing import Iterable, List, Optional

from nyxniri.constants import Colors, MAIN_WM, REPO_URL, THEME_ENGINE
from nyxniri.core import get_env, log_msg
from nyxniri.i18n import msg
from nyxniri.tui import read_key, responsive_hint, show_logo, raw_input_mode, _drain_pending

from nyxniri.deploy.atomic import (
    atomic_replace_item,
    atomic_replace_item_transaction,
)
from nyxniri.deploy.assets import WallpaperDeployResult, deploy_wallpapers, wallpapers_pack_present
from nyxniri.deploy.hardware import _phase_hardware_patches
from nyxniri.deploy.manifest import discover_deployable_apps, load_manifest_at
from nyxniri.deploy.preset import (
    ActivePresetWriteError,
    ActivePresetStatus,
    _active_state_unchanged_at,
    _bound_config_target,
    _opened_presets_dir_at,
    _opened_repo_app,
    _opened_resolved_preset_source,
    _opened_root,
    _read_active_at,
    _write_active_at,
)
from nyxniri.deploy.templates import (
    _opened_app_root,
    _opened_regular_leaf,
    _phase_render_templates,
)

_CONFIG_ITEMS_CACHE: List[str] = []

def discover_config_items() -> List[str]:
    """Deployable config app names (manifest-only dirs like nautilus/ are excluded)."""
    global _CONFIG_ITEMS_CACHE
    if _CONFIG_ITEMS_CACHE:
        return _CONFIG_ITEMS_CACHE
    # Honest empty when nothing is discoverable (broken/unreadable configs/);
    # install.sh's engine_is_complete guards configs/ exists before we run,
    # so a real empty here is an edge case — downstream degrades to "0 configs".
    _CONFIG_ITEMS_CACHE = discover_deployable_apps()
    return _CONFIG_ITEMS_CACHE


def _fchmod_regular_at(app_fd: int, relative: Path) -> None:
    """Apply executable mode to one bound regular file below an app fd."""
    parts = relative.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        return

    parent_fd = os.dup(app_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=parent_fd,
            )
            os.close(parent_fd)
            parent_fd = next_fd
        with _opened_regular_leaf(parent_fd, parts[-1]) as file_fd:
            os.fchmod(file_fd, 0o755)
    except OSError:
        pass
    finally:
        os.close(parent_fd)


def _phase_manifest_chmod(app_root: Path, patterns: Iterable[str]) -> None:
    """Expand manifest globs, then bind every matched component without symlinks."""
    try:
        with _opened_app_root(app_root) as app_fd:
            bound_root = Path("/proc/self/fd") / str(app_fd)
            for pattern in patterns:
                pattern_path = Path(pattern)
                if pattern_path.is_absolute() or ".." in pattern_path.parts:
                    continue
                try:
                    matches = bound_root.glob(pattern)
                    for match in matches:
                        _fchmod_regular_at(app_fd, match.relative_to(bound_root))
                except (OSError, ValueError):
                    continue
    except OSError:
        return


def _phase_initial_eyecare(app_root: Path) -> None:
    """Create niri's initial effects link inside the already-bound app."""
    try:
        with _opened_app_root(app_root) as app_fd, \
             _opened_regular_leaf(app_fd, "effects_normal.kdl") as normal_fd:
            normal_info = os.fstat(normal_fd)
            try:
                os.stat("effects.kdl", dir_fd=app_fd, follow_symlinks=False)
            except FileNotFoundError:
                os.symlink("effects_normal.kdl", "effects.kdl", dir_fd=app_fd)
                current = os.stat(
                    "effects_normal.kdl",
                    dir_fd=app_fd,
                    follow_symlinks=False,
                )
                if (current.st_dev, current.st_ino) != (
                    normal_info.st_dev,
                    normal_info.st_ino,
                ):
                    os.unlink("effects.kdl", dir_fd=app_fd)
    except OSError:
        pass


def _same_config_root(config_fd: int, config_dir: Path) -> bool:
    """Return whether the configured path still names the bound root inode."""
    try:
        current = os.stat(config_dir)
        bound = os.fstat(config_fd)
    except OSError:
        return False
    return (
        stat.S_ISDIR(current.st_mode)
        and (current.st_dev, current.st_ino) == (bound.st_dev, bound.st_ino)
    )

def _phase_atomic_deployment(
    items_to_deploy: List[str],
    keep_preserved: bool = True,
    preserved_log: Optional[List[str]] = None,
    test_mode: bool = False,
    *,
    _config_fd: Optional[int] = None,
) -> List[str]:
    """Execute atomic copy for selected configuration units.

    Per-app manifest drives: the preserve list (files kept across deploys,
    e.g. niri/monitor.kdl), and the chmod globs (executable scripts). The
    Dunder __custom__ walk inside atomic_replace_item is untouched.
    """
    env = get_env()
    config_dir = env.config_dir

    failed_items: List[str] = []
    try:
        root_context = (
            _opened_root(config_dir, create=True)
            if _config_fd is None
            else nullcontext(_config_fd)
        )
        with root_context as config_fd, \
             _opened_presets_dir_at(config_fd, create=True) as presets_fd:
            for item in items_to_deploy:
                dest = config_dir / item
                deployed_ok = False
                try:
                    target = _bound_config_target(config_fd, item)
                    with _opened_repo_app(item) as repo_app:
                        manifest = load_manifest_at(
                            item,
                            repo_app.fd,
                            repo_app.info,
                            repo_app.root_fd,
                        )
                        preserve = manifest.preserve if keep_preserved else None

                        for _attempt in range(3):
                            active_state = _read_active_at(presets_fd, item)
                            with _opened_resolved_preset_source(
                                item,
                                active_state,
                                dest,
                                presets_fd=presets_fd,
                                bound_dest=target.path,
                                repo_app=repo_app,
                            ) as (result, selected, source):
                                if (
                                    active_state.status is not ActivePresetStatus.INVALID
                                    and not _active_state_unchanged_at(
                                        presets_fd,
                                        item,
                                        active_state,
                                    )
                                ):
                                    continue

                                for warning in result.warnings:
                                    print(warning)
                                if result.src is None or selected is None or source is None:
                                    if active_state.status is ActivePresetStatus.INVALID:
                                        log_msg(
                                            "WARN",
                                            f"Invalid active preset state for {item}; dest frozen, skipped",
                                        )
                                    else:
                                        log_msg(
                                            "WARN",
                                            f"Preset '{active_state.selected}' for {item} not found; dest frozen, skipped",
                                        )
                                    break

                                if result.reset_active is not None:
                                    try:
                                        _write_active_at(
                                            presets_fd,
                                            item,
                                            result.reset_active,
                                        )
                                    except ActivePresetWriteError as exc:
                                        if not exc.published:
                                            log_msg(
                                                "ERROR",
                                                f"Failed to write active preset for {item}: {exc}",
                                            )
                                            break
                                        log_msg(
                                            "WARN",
                                            f"Published active preset for {item} without durability confirmation: {exc}",
                                        )
                                    except Exception as exc:
                                        log_msg(
                                            "ERROR",
                                            f"Failed to write active preset for {item}: {exc}",
                                        )
                                        break
                                    active_state = _read_active_at(presets_fd, item)
                                    if (
                                        active_state.status is not ActivePresetStatus.VALID
                                        or active_state.selected != selected
                                    ):
                                        continue

                                if not _active_state_unchanged_at(
                                    presets_fd,
                                    item,
                                    active_state,
                                ):
                                    continue
                                with atomic_replace_item_transaction(
                                    source.path,
                                    target.path,
                                    preserved_log=preserved_log,
                                    test_mode=test_mode,
                                    preserve=preserve,
                                    display_dest=dest,
                                ) as swap:
                                    if not _active_state_unchanged_at(presets_fd, item, active_state):
                                        continue
                                    _phase_manifest_chmod(swap.path, manifest.chmod)
                                    _phase_render_templates(only_app=item, app_root=swap.path)
                                    if item == MAIN_WM:
                                        _phase_hardware_patches(app_root=swap.path)
                                        _phase_initial_eyecare(swap.path)
                                    if not _active_state_unchanged_at(presets_fd, item, active_state):
                                        log_msg(
                                            "WARN",
                                            f"Active preset changed during post-processing {item}; retrying",
                                        )
                                        continue
                                    swap.commit()
                                    deployed_ok = True
                                    break
                except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
                    log_msg("ERROR", f"Missing or unsafe config source for {item}: {exc}")
                if not deployed_ok:
                    failed_items.append(item)
                    print(msg("log_deploy_config_failed", item), file=sys.stderr)
                    continue

                print(msg("log_deploy_config_item", item))
                log_msg("INFO", f"Deployed config ~/.config/{item}")
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        log_msg("ERROR", f"Cannot bind preset storage: {exc}")
        for item in items_to_deploy:
            if item not in failed_items:
                failed_items.append(item)
                print(msg("log_deploy_config_failed", item), file=sys.stderr)

    return failed_items

def _phase_post_install_services(*, config_fd: Optional[int] = None) -> None:
    """Run post-deployment hooks (theme-sync, mpvpaper enable, Fisher plugins)."""
    env = get_env()
    config_dir = env.config_dir

    try:
        root_context = (
            _opened_root(config_dir)
            if config_fd is None
            else nullcontext(config_fd)
        )
        with root_context as bound_fd:
            if not _same_config_root(bound_fd, config_dir):
                log_msg("WARN", "Config root changed before post-install; hooks skipped")
                return

            theme_root = Path("/proc/self/fd") / str(bound_fd) / THEME_ENGINE
            try:
                with _opened_app_root(theme_root) as theme_fd, \
                     _opened_regular_leaf(theme_fd, "theme-sync.sh") as script_fd:
                    os.fchmod(script_fd, 0o755)
                    if not _same_config_root(bound_fd, config_dir):
                        log_msg("WARN", "Config root changed before theme sync; hooks skipped")
                        return
                    subprocess.run(
                        ["bash", f"/proc/self/fd/{script_fd}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        timeout=30,
                        pass_fds=(script_fd,),
                    )
                    print(msg("log_gtk_theme_init"))
            except OSError:
                pass

            if not _same_config_root(bound_fd, config_dir):
                log_msg("WARN", "Config root changed during post-install; hooks stopped")
                return
            if shutil.which(THEME_ENGINE):
                from nyxniri.modules.gtktheme import gtktheme_trigger_render
                gtktheme_trigger_render()
                print(msg("log_enable_mpvpaper"))
                subprocess.run([THEME_ENGINE, "msg", "plugins", "enable", f"{THEME_ENGINE}/mpvpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=15)

            if not _same_config_root(bound_fd, config_dir):
                log_msg("WARN", "Config root changed during post-install; Fisher skipped")
                return
            if shutil.which("fish"):
                from nyxniri.modules.fisher import fisher_install
                fisher_install()
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        log_msg("WARN", f"Cannot bind config root for post-install: {exc}")

def render_completion_screen(
    mode: str = "install",
    chosen_items: Optional[List[str]] = None,
    preserved_lines: Optional[List[str]] = None,
    wallpaper_result: Optional[WallpaperDeployResult] = None,
    do_fcitx: bool = False,
    do_greeter: bool = False,
    failed_items: Optional[List[str]] = None,
) -> None:
    """Render minimal, zero-entropy TUI Completion Screen according to TUI Design Charter."""
    if chosen_items is None:
        chosen_items = discover_config_items()
    if preserved_lines is None:
        preserved_lines = []
    if failed_items is None:
        failed_items = []

    from nyxniri.modules.fcitx import fcitx5_installed, fcitx_enabled
    from nyxniri.deps import get_missing_deps

    title_key = "summary_title_failed" if failed_items else ("summary_title_update" if mode == "update" else ("summary_title_test" if mode == "test" else "summary_title_install"))
    missing_deps = get_missing_deps() if mode == "full" else []

    def _render_body():
        title_color = Colors.BOLD_RED if failed_items else Colors.BOLD_GREEN
        sys.stdout.write(f"  {title_color}{msg(title_key)}{Colors.RESET}\n\n")
        sys.stdout.write(f"  {Colors.BOLD_WHITE}{msg('summary_section_details')}{Colors.RESET}\n")

        if failed_items:
            sys.stdout.write(f"    {Colors.BOLD_RED}[✗]{Colors.RESET} {msg('summary_item_configs_failed', ', '.join(failed_items))}\n")
        elif chosen_items or mode == "test":
            sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_configs_ok', len(chosen_items))}\n")
        else:
            sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_configs_skip')}\n")

        if mode in ("full", "update", "test"):
            if wallpaper_result is not None:
                wallpaper_key, wallpaper_color, wallpaper_icon = wallpaper_result.status_line(wallpapers_pack_present())
            elif wallpapers_pack_present():
                wallpaper_key, wallpaper_color, wallpaper_icon = "summary_item_wallpapers_existing", Colors.BOLD_GREEN, "[✓]"
            else:
                wallpaper_key, wallpaper_color, wallpaper_icon = "summary_item_wallpapers_skip", Colors.BOLD_YELLOW, "[!]"
            sys.stdout.write(f"    {wallpaper_color}{wallpaper_icon}{Colors.RESET} {msg(wallpaper_key)}\n")

        if mode in ("full", "update", "test") and fcitx5_installed():
            if do_fcitx or fcitx_enabled():
                sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_fcitx_ok')}\n")
            else:
                sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_fcitx_skip')}\n")

        if mode == "full":
            if not missing_deps:
                sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_deps_ok')}\n")
            else:
                sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_deps_skip')}\n")

        if do_greeter:
            sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_greeter_ok')}\n")

        if preserved_lines:
            sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_preserved')}{Colors.RESET}\n")
            for pline in sorted(set(preserved_lines)):
                sys.stdout.write(f"    {pline}\n")

    if not sys.stdin.isatty() or mode == "test":
        sys.stdout.write(Colors.CLEAR_SCREEN)
        show_logo()
        _render_body()
        sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_next')}{Colors.RESET}\n")
        sys.stdout.write(f"    {msg('summary_next_start')}\n")
        sys.stdout.write(f"    {msg('summary_next_manual')}\n")
        sys.stdout.write(f"    {msg('summary_next_panel')}\n\n")
        return

    # Interactive Next Steps Menu
    from nyxniri.deps import run_optional_apps_menu_loop
    focus = 0
    sys.stdout.write(Colors.CURSOR_HIDE)
    fd = sys.stdin.fileno()
    stack = ExitStack()
    stack.enter_context(raw_input_mode(fd))
    try:
        _drain_pending(fd)
        while True:
            sys.stdout.write(Colors.CLEAR_SCREEN)
            show_logo()
            _render_body()

            sys.stdout.write(msg("summary_action_title"))
            from nyxniri.tui import render_menu_item
            render_menu_item(0, msg("summary_action_apps"), focus)
            render_menu_item(1, msg("summary_action_star"), focus)
            render_menu_item(2, msg("summary_action_exit"), focus, style="subtle")

            sys.stdout.write(f"\n{responsive_hint('summary_action_hint')}\n")
            sys.stdout.flush()

            key = read_key()
            if key in ("UP", "k", "K"):
                focus = 2 if focus <= 0 else focus - 1
            elif key in ("DOWN", "j", "J"):
                focus = 0 if focus >= 2 else focus + 1
            elif key in ("ENTER", "SPACE"):
                if focus == 0:
                    run_optional_apps_menu_loop()
                elif focus == 1:
                    star_url = REPO_URL.removesuffix(".git")
                    if shutil.which("xdg-open"):
                        subprocess.run(["xdg-open", star_url], check=False, timeout=5)
                    print(msg("msg_star_opened", star_url))
                    time.sleep(1.2)
                elif focus == 2:
                    break
            elif key in ("0", "q", "Q", "ESC", "EXIT"):
                break
    finally:
        _drain_pending(fd, debounce=True)
        stack.close()
        sys.stdout.write(Colors.CURSOR_SHOW)
        sys.stdout.flush()

def deploy_selected_configs(
    do_backup: bool = False,
    items_to_deploy: Optional[List[str]] = None,
    preserved_log: Optional[List[str]] = None,
) -> List[str]:
    """Deploy selected dotfile items with optional backup, template rendering, and hardware patches."""
    if items_to_deploy is None:
        items_to_deploy = discover_config_items()
    if preserved_log is None:
        preserved_log = []

    if do_backup:
        from nyxniri.state.backup import backup_configs
        backup_configs(note="auto_snapshot_before_deploy", interactive=False)

    print(msg("copying_configs"))
    env = get_env()
    try:
        with _opened_root(env.config_dir, create=True) as config_fd:
            failed_items = _phase_atomic_deployment(
                items_to_deploy,
                keep_preserved=True,
                preserved_log=preserved_log,
                _config_fd=config_fd,
            )
            if not failed_items:
                _phase_post_install_services(config_fd=config_fd)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        log_msg("ERROR", f"Cannot bind config root for deployment: {exc}")
        failed_items = list(items_to_deploy)
    if failed_items:
        print(msg("deploy_failed", ", ".join(failed_items)), file=sys.stderr)
        return failed_items
    print(msg("copy_done"))
    return []

def test_deploy() -> bool:
    """Developer test command: fast idempotent re-deploy in current environment."""
    print(msg("test_start"))

    preserved_log: List[str] = []
    items = discover_config_items()
    failed_items = _phase_atomic_deployment(items, keep_preserved=True, preserved_log=preserved_log, test_mode=True)
    if failed_items:
        print(msg("deploy_failed", ", ".join(failed_items)), file=sys.stderr)
        render_completion_screen(mode="test", chosen_items=items, preserved_lines=preserved_log, failed_items=failed_items)
        return False
    wallpaper_result = deploy_wallpapers(do_download=False)
    render_completion_screen(
        mode="test",
        chosen_items=items,
        preserved_lines=preserved_log,
        wallpaper_result=wallpaper_result,
    )
    return True
