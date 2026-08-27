"""Optional Noctalia Greeter (greetd login) installation and system setup."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from nyxniri.constants import (
    Colors,
    GREETER_ETC_CFG,
    GREETER_PKG,
    GREETER_POLKIT_RULE,
    GREETER_SESSION_BIN,
    GREETER_STATE_DIR,
    MAIN_WM,
    THEME_ENGINE,
)
from nyxniri.core import log_msg
from nyxniri.i18n import msg, text

CONFLICT_DMS = ["sddm", "lightdm", "gdm", "ly"]


def _enabled_conflicting_dm() -> Optional[str]:
    """Return the enabled display manager that currently owns the login alias."""
    if not shutil.which("systemctl"):
        return None
    for dm in CONFLICT_DMS:
        res = subprocess.run(["systemctl", "is-enabled", dm], capture_output=True, check=False)
        if res.returncode == 0:
            return dm
    return None


def _greetd_unit_available() -> bool:
    """Check the unit before changing the working display manager."""
    if not shutil.which("systemctl"):
        return False
    res = subprocess.run(["systemctl", "cat", "greetd"], capture_output=True, check=False)
    return res.returncode == 0


def _restore_display_manager(previous_dm: Optional[str]) -> bool:
    """Clear a partial greetd enable and restore the previous login alias."""
    try:
        subprocess.run(["sudo", "systemctl", "disable", "greetd"], check=False)
    except OSError:
        pass

    if not previous_dm:
        return True

    try:
        subprocess.run(
            ["sudo", "systemctl", "enable", "--force", previous_dm], check=False
        )
        restored = subprocess.run(
            ["systemctl", "is-enabled", previous_dm], capture_output=True, check=False
        ).returncode == 0
    except OSError:
        restored = False

    if restored:
        print(msg("greeter_dm_restored", previous_dm))
    else:
        print(msg("greeter_dm_restore_failed", previous_dm))
    return restored


def _switch_to_greetd(previous_dm: Optional[str]) -> bool:
    """Enable greetd for the next boot, rolling back an incomplete switch."""
    switch_started = False
    committed = False
    try:
        if previous_dm:
            switch_started = True
            disabled = subprocess.run(
                ["sudo", "systemctl", "disable", previous_dm], check=False
            )
            if disabled.returncode != 0:
                print(msg("greeter_dm_disable_failed", previous_dm))
                return False

        switch_started = True
        subprocess.run(["sudo", "systemctl", "enable", "greetd"], check=False)
        enabled = subprocess.run(
            ["systemctl", "is-enabled", "greetd"], capture_output=True, check=False
        )
        if enabled.returncode != 0:
            print(msg("greeter_enable_failed"))
            return False

        committed = True
        print(msg("greeter_enabled"))
        return True
    except OSError:
        print(msg("greeter_enable_failed"))
        return False
    finally:
        if switch_started and not committed:
            _restore_display_manager(previous_dm)


def greeter_installed() -> bool:
    """Check if noctalia-greeter session binary exists in PATH."""
    return shutil.which(GREETER_SESSION_BIN) is not None

def greeter_status_label() -> str:
    """Return compact status label for menus."""
    if not greeter_installed():
        return msg("status_not_installed")

    cfg_ok = False
    if GREETER_ETC_CFG.is_file():
        try:
            content = GREETER_ETC_CFG.read_text(encoding="utf-8", errors="ignore")
            if GREETER_SESSION_BIN in content:
                cfg_ok = True
        except Exception:
            pass

    enabled = False
    if shutil.which("systemctl"):
        res = subprocess.run(["systemctl", "is-enabled", "greetd"], capture_output=True, check=False)
        enabled = res.returncode == 0

    if enabled and cfg_ok:
        return msg("status_installed_enabled")
    return msg("status_installed")

def _greeter_session_arg() -> str:
    """Check if niri session is discoverable by noctalia-greeter."""
    if shutil.which(GREETER_PKG):
        try:
            res = subprocess.run([GREETER_PKG, "sessions"], capture_output=True, text=True, check=False)
            if MAIN_WM.lower() in res.stdout.lower():
                return f"-- --session {MAIN_WM}"
        except Exception:
            pass
    return ""

def greeter_install_packages() -> bool:
    """Install greetd and noctalia-greeter."""
    from nyxniri.deps import ensure_aur_helper, get_preferred_pkg_manager
    print(msg("greeter_install_pkgs"))

    pkg_mgr = get_preferred_pkg_manager()
    is_aur = pkg_mgr != ["sudo", "pacman"]

    # Check greetd
    if shutil.which("pacman"):
        res = subprocess.run(["pacman", "-Qq", "greetd"], capture_output=True, check=False)
        if res.returncode != 0:
            subprocess.run([*pkg_mgr, "-S", "--noconfirm", "greetd"], check=False)

    if not greeter_installed():
        has_aur_helper = ensure_aur_helper() is not None if not is_aur else True
        if not has_aur_helper:
            print(msg("greeter_aur_required"))
            return False
        res_inst = subprocess.run([*pkg_mgr, "-S", "--noconfirm", GREETER_PKG], check=False)
        if res_inst.returncode != 0 or not greeter_installed():
            print(msg("greeter_install_failed"))
            return False

    return True

def greeter_install() -> bool:
    """Full Noctalia Greeter installation and configuration pipeline."""
    print(msg("greeter_install_title"))

    if not greeter_install_packages():
        return False

    # Backup & Write /etc/greetd/config.toml
    sess_path = shutil.which(GREETER_SESSION_BIN) or f"/usr/bin/{GREETER_SESSION_BIN}"
    sess_arg = _greeter_session_arg()
    command_str = f"{sess_path} {sess_arg}".strip()

    toml_content = (
        "[terminal]\n"
        "vt = 1\n\n"
        "[default_session]\n"
        f'command = "{command_str}"\n'
        'user = "greeter"\n'
    )

    bak = Path(f"{GREETER_ETC_CFG}.nyxniri.bak")
    backup_cmd = f"mkdir -p {GREETER_ETC_CFG.parent} && if [ -f {GREETER_ETC_CFG} ] && [ ! -f {bak} ]; then cp {GREETER_ETC_CFG} {bak}; fi"
    res_b = subprocess.run(["sudo", "sh", "-c", backup_cmd], check=False)
    if res_b.returncode != 0:
        print(msg("greeter_cmd_failed", str(bak)))
        return False

    write_cmd = f"cat << 'EOF' > {GREETER_ETC_CFG}\n{toml_content}\nEOF"
    res_w = subprocess.run(["sudo", "sh", "-c", write_cmd], check=False)
    if res_w.returncode == 0:
        print(msg("greeter_config_written", str(GREETER_ETC_CFG)))
    else:
        print(msg("greeter_config_failed", str(GREETER_ETC_CFG)))
        return False

    state_cmd = (
        f"mkdir -p {GREETER_STATE_DIR} && "
        f"(chown -R greeter:greeter {GREETER_STATE_DIR} 2>/dev/null || true) && "
        f"chmod 755 {GREETER_STATE_DIR}"
    )
    res_s = subprocess.run(["sudo", "sh", "-c", state_cmd], check=False)
    if res_s.returncode == 0:
        print(msg("greeter_state_dir_created"))
    else:
        print(msg("greeter_cmd_failed", str(GREETER_STATE_DIR)))
        return False

    # Polkit rule
    polkit_rule = (
        'polkit.addRule(function(action, subject) {\n'
        f'    if (action.id == "org.{THEME_ENGINE}.greeter.apply-appearance" &&\n'
        '        subject.isInGroup("wheel")) {\n'
        '        return polkit.Result.YES;\n'
        '    }\n'
        '});\n'
    )
    polkit_cmd = f"mkdir -p {GREETER_POLKIT_RULE.parent} && cat << 'EOF' > {GREETER_POLKIT_RULE}\n{polkit_rule}\nEOF"
    res_p = subprocess.run(["sudo", "sh", "-c", polkit_cmd], check=False)
    if res_p.returncode == 0:
        print(msg("greeter_polkit_written", str(GREETER_POLKIT_RULE)))
    else:
        print(msg("greeter_polkit_failed"))
        return False

    # Switch only after every prerequisite is ready. Do not use --now here: stopping
    # the active display manager would terminate the current graphical session.
    if not _greetd_unit_available():
        print(msg("greeter_service_missing"))
        return False

    previous_dm = _enabled_conflicting_dm()
    if previous_dm:
        print(msg("greeter_dm_conflict", previous_dm))
    if not _switch_to_greetd(previous_dm):
        return False

    print(msg("greeter_reboot_hint"))
    log_msg("INFO", "Configured Noctalia Greeter")
    return True

def greeter_status() -> None:
    """Print detailed status of Noctalia Greeter."""
    print(msg("greeter_status_title"))
    if greeter_installed():
        print(msg("doctor_ok", text(f"{GREETER_PKG}: 已安装", f"{GREETER_PKG}: installed")))
    else:
        print(msg("doctor_warn", text(f"{GREETER_PKG}: 未安装", f"{GREETER_PKG}: not installed")))

    if GREETER_ETC_CFG.is_file():
        try:
            content = GREETER_ETC_CFG.read_text(encoding="utf-8", errors="ignore")
            if GREETER_SESSION_BIN in content:
                print(msg("doctor_ok", text(f"greetd 配置: 已使用 {GREETER_PKG}", f"greetd config: using {GREETER_PKG}")))
            else:
                print(msg("doctor_warn", text(
                    f"greetd 配置存在，但未使用 {GREETER_PKG}",
                    f"greetd config exists but does not use {GREETER_PKG}",
                )))
        except Exception:
            pass
    else:
        print(msg("doctor_warn", text(f"greetd 配置缺失: {GREETER_ETC_CFG}", f"greetd config is missing: {GREETER_ETC_CFG}")))

    if shutil.which("systemctl"):
        res = subprocess.run(["systemctl", "is-enabled", "greetd"], capture_output=True, check=False)
        if res.returncode == 0:
            print(msg("doctor_ok", text("greetd 服务: 已启用", "greetd service: enabled")))
        else:
            print(msg("doctor_warn", text("greetd 服务: 未启用", "greetd service: disabled")))

def greeter_uninstall() -> bool:
    """Uninstall Noctalia Greeter configuration and restore backups."""
    print(msg("greeter_uninstall_title"))

    bak = Path(f"{GREETER_ETC_CFG}.nyxniri.bak")
    if bak.is_file():
        restore_cmd = f"mv {bak} {GREETER_ETC_CFG}"
        subprocess.run(["sudo", "sh", "-c", restore_cmd], check=False)
        print(msg("greeter_uninstall_restored", str(GREETER_ETC_CFG)))
    else:
        print(msg("greeter_uninstall_nobackup"))

    if GREETER_POLKIT_RULE.is_file():
        subprocess.run(["sudo", "rm", "-f", str(GREETER_POLKIT_RULE)], check=False)
        print(msg("greeter_uninstall_polkit"))

    # Remove the greeter's state directory (created at install; previously leaked)
    subprocess.run(["sudo", "rm", "-rf", str(GREETER_STATE_DIR)], check=False)
    print(msg("greeter_uninstall_state_dir", str(GREETER_STATE_DIR)))

    print(msg("greeter_uninstall_done"))
    log_msg("INFO", "Uninstalled Noctalia Greeter configuration")
    return True
