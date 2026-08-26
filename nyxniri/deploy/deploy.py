"""Deploy orchestrator — config discovery, atomic-deploy phase, post-install
services, completion screen, fisher uninstall, and the deploy/test entry points.

Coordinates the deploy/ siblings: atomic (swap+preserve), templates (render),
assets (wallpapers), hardware (NVIDIA patch), manifest (app discovery), preset
(active variant). Modules/state/deps are lazy-imported to avoid cycles.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

from nyxniri.constants import Colors, MAIN_WM, REPO_URL, THEME_ENGINE
from nyxniri.core import get_env, log_msg, register_temp_path
from nyxniri.i18n import msg
from nyxniri.network import fetch_raw_with_fallback
from nyxniri.tui import read_key, responsive_hint, show_logo

from nyxniri.deploy.atomic import (
    _cleanup_snapshots,
    _restore_preserved,
    _snapshot_preserved,
    atomic_replace_item,
)
from nyxniri.deploy.assets import WallpaperDeployResult, deploy_wallpapers, wallpapers_pack_present
from nyxniri.deploy.hardware import _phase_hardware_patches
from nyxniri.deploy.manifest import discover_deployable_apps, load_manifest
from nyxniri.deploy.preset import read_active_preset, resolve_preset_src, write_active_preset
from nyxniri.deploy.templates import _phase_render_templates

_CONFIG_ITEMS_CACHE: List[str] = []

def discover_config_items() -> List[str]:
    """Deployable config app names (manifest-only dirs like nautilus/ are excluded)."""
    global _CONFIG_ITEMS_CACHE
    if _CONFIG_ITEMS_CACHE:
        return _CONFIG_ITEMS_CACHE
    apps = discover_deployable_apps()
    if apps:
        _CONFIG_ITEMS_CACHE = apps
        return _CONFIG_ITEMS_CACHE
    # Fallback when configs/ is unreadable (e.g. bundled engine without a repo)
    _CONFIG_ITEMS_CACHE = ["fastfetch", "fish", "kitty", "niri", "noctalia", "starship.toml", "xdg-desktop-portal", "zed"]
    return _CONFIG_ITEMS_CACHE

def _phase_atomic_deployment(
    items_to_deploy: List[str],
    keep_preserved: bool = True,
    preserved_log: Optional[List[str]] = None,
    test_mode: bool = False,
) -> List[str]:
    """Execute atomic copy for selected configuration units.

    Per-app manifest drives: the preserve list (files kept across deploys,
    e.g. niri/monitor.kdl), and the chmod globs (executable scripts). The
    Dunder __custom__ walk inside atomic_replace_item is untouched.
    """
    env = get_env()
    config_dir = env.config_dir
    config_dir.mkdir(parents=True, exist_ok=True)

    failed_items: List[str] = []
    for item in items_to_deploy:
        dest = config_dir / item

        # Resolve which source tree to deploy: default config, an official
        # preset, or a user preset — based on the app's active state file.
        active = read_active_preset(item)
        result = resolve_preset_src(item, active, dest)
        for w in result.warnings:
            print(w)
        if result.src is None:
            # Preset not found anywhere — freeze dest, do not fall back to
            # default (would silently wipe the user's config). §3.2
            log_msg("WARN", f"Preset '{active}' for {item} not found; dest frozen, skipped")
            continue
        src = result.src
        # dest-missing reset: sanctioned write-before-deploy (dest is empty,
        # so a half-written state self-heals next run). §3.2
        if result.reset_active is not None:
            try:
                write_active_preset(item, result.reset_active)
            except Exception as e:
                log_msg("ERROR", f"Failed to write active preset for {item}: {e}")

        if not src.exists():
            failed_items.append(item)
            print(msg("log_deploy_config_failed", item), file=sys.stderr)
            log_msg("ERROR", f"Missing config source: {src}")
            continue

        # Manifest always loaded from the app root (not the preset dir):
        # preserve/chmod describe the app, independent of which variant ships.
        manifest = load_manifest(env.configs_src / item)
        snaps: List[Tuple[str, Path]] = []
        if keep_preserved and manifest.preserve:
            snaps = _snapshot_preserved(dest, manifest.preserve)

        if not atomic_replace_item(src, dest, preserved_log=preserved_log, test_mode=test_mode):
            _cleanup_snapshots(snaps)
            failed_items.append(item)
            print(msg("log_deploy_config_failed", item), file=sys.stderr)
            continue

        if snaps:
            _restore_preserved(dest, snaps, preserved_log)

        # Executable permissions — manifest chmod globs, relative to app dir
        for pattern in manifest.chmod:
            for p in dest.glob(pattern):
                if p.is_file():
                    try:
                        p.chmod(0o755)
                    except OSError:
                        pass

        print(msg("log_deploy_config_item", item))
        log_msg("INFO", f"Deployed config ~/.config/{item}")

    # Initial EyeCare symlink (niri one-off, not manifest-driven)
    effects_normal = config_dir / MAIN_WM / "effects_normal.kdl"
    effects_sym = config_dir / MAIN_WM / "effects.kdl"
    if effects_normal.is_file() and not effects_sym.exists():
        try:
            effects_sym.symlink_to(effects_normal)
        except Exception:
            pass

    return failed_items

def _phase_post_install_services() -> None:
    """Run post-deployment hooks (theme-sync, mpvpaper enable, Fisher plugins)."""
    env = get_env()
    config_dir = env.config_dir

    sync_script = config_dir / THEME_ENGINE / "theme-sync.sh"
    if sync_script.is_file():
        sync_script.chmod(0o755)
        subprocess.run(["bash", str(sync_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        print(msg("log_gtk_theme_init"))

    if shutil.which(THEME_ENGINE):
        from nyxniri.modules.gtktheme import gtktheme_trigger_render
        gtktheme_trigger_render()
        print(msg("log_enable_mpvpaper"))
        subprocess.run([THEME_ENGINE, "msg", "plugins", "enable", f"{THEME_ENGINE}/mpvpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    if shutil.which("fish"):
        print(msg("log_check_fisher"))
        log_msg("INFO", "Checking Fisher plugin manager installation")
        fish_check = subprocess.run(["fish", "-c", "functions -q fisher; echo $status"], capture_output=True, text=True, check=False)
        if fish_check.returncode == 0 and fish_check.stdout.strip() == "0":
            log_msg("INFO", "Fisher already installed, running update")
            subprocess.run(["fish", "-c", "fisher update"], check=False)
        else:
            tfd, tname = tempfile.mkstemp(suffix=".fish")
            os.close(tfd)
            fisher_path = Path(tname)
            register_temp_path(fisher_path)

            msg_install = msg("log_install_fish_plugins")
            msg_skip = msg("log_fisher_update_skipped")
            if fetch_raw_with_fallback("jorgebucaran/fisher", "main", "functions/fisher.fish", fisher_path):
                fish_code = (
                    f"if not functions -q fisher; source '{fisher_path}' && fisher install jorgebucaran/fisher; end; "
                    f"if test -f ~/.config/fish/fish_plugins && functions -q fisher; "
                    f"echo '{msg_install}'; fisher update || echo '{msg_skip}'; end"
                )
                subprocess.run(["fish", "-c", fish_code], check=False)
            else:
                print(msg("log_fisher_install_skipped"))
                log_msg("WARN", "Fisher auto-install skipped (network unreachable)")

def fisher_uninstall() -> bool:
    """Remove fisher and every plugin it installed (§8.4 decision #1: aggressive).

    NyxNiri installed fisher → NyxNiri removes it. fish present: ask fisher to
    ``remove --all`` (it knows its plugins), then drop the loader. fish absent:
    degrade to a direct ``rm -rf`` of fisher.fish + conf.d/ — uninstall often
    happens because the user already left fish, so the host may be gone. §8.6
    """
    env = get_env()
    fish_dir = env.config_dir / "fish"
    fisher_file = fish_dir / "functions" / "fisher.fish"
    conf_d = fish_dir / "conf.d"

    if shutil.which("fish"):
        check = subprocess.run(
            ["fish", "-c", "functions -q fisher; echo $status"],
            capture_output=True, text=True, check=False,
        )
        if check.returncode == 0 and check.stdout.strip() == "0":
            subprocess.run(
                ["fish", "-c", "fisher remove --all"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            log_msg("INFO", "fisher remove --all ran")
        # fisher not installed → no managed plugins to remove; just drop the loader.
    else:
        # Host gone — fisher can't enumerate plugins. Nuke its footprint directly.
        if conf_d.is_dir():
            shutil.rmtree(conf_d, ignore_errors=True)
            log_msg("INFO", "Removed fish conf.d/ (fisher fallback, fish absent)")
    fisher_file.unlink(missing_ok=True)
    log_msg("INFO", "Uninstalled fisher + fish plugins")
    return True

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
            if wallpaper_result and wallpaper_result.downloaded:
                wallpaper_key = "summary_item_wallpapers_downloaded"
                wallpaper_color = Colors.BOLD_GREEN
                wallpaper_icon = "[✓]"
            elif wallpaper_result and wallpaper_result.download_failed and wallpaper_result.pack_present:
                wallpaper_key = "summary_item_wallpapers_refresh_failed"
                wallpaper_color = Colors.BOLD_YELLOW
                wallpaper_icon = "[!]"
            elif wallpaper_result and wallpaper_result.download_failed and wallpaper_result.fallback_synced:
                wallpaper_key = "summary_item_wallpapers_failed_fallback"
                wallpaper_color = Colors.BOLD_YELLOW
                wallpaper_icon = "[!]"
            elif wallpaper_result and wallpaper_result.download_failed:
                wallpaper_key = "summary_item_wallpapers_failed"
                wallpaper_color = Colors.BOLD_RED
                wallpaper_icon = "[✗]"
            elif (wallpaper_result and wallpaper_result.pack_present) or wallpapers_pack_present():
                wallpaper_key = "summary_item_wallpapers_existing"
                wallpaper_color = Colors.BOLD_GREEN
                wallpaper_icon = "[✓]"
            elif wallpaper_result and wallpaper_result.fallback_synced:
                wallpaper_key = "summary_item_wallpapers_fallback"
                wallpaper_color = Colors.BOLD_YELLOW
                wallpaper_icon = "[!]"
            else:
                wallpaper_key = "summary_item_wallpapers_skip"
                wallpaper_color = Colors.BOLD_YELLOW
                wallpaper_icon = "[!]"
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
    try:
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
    failed_items = _phase_atomic_deployment(items_to_deploy, keep_preserved=True, preserved_log=preserved_log)
    if failed_items:
        print(msg("deploy_failed", ", ".join(failed_items)), file=sys.stderr)
        return failed_items
    _phase_render_templates()
    _phase_hardware_patches()
    _phase_post_install_services()
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
    _phase_render_templates()
    _phase_hardware_patches()
    wallpaper_result = deploy_wallpapers(do_download=False)
    render_completion_screen(
        mode="test",
        chosen_items=items,
        preserved_lines=preserved_log,
        wallpaper_result=wallpaper_result,
    )
    return True
