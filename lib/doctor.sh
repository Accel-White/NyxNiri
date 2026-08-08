#!/usr/bin/env bash

# ==============================================================================
# NyxNiri System Diagnostics (System Doctor & Bug Report Exporter)
# ==============================================================================

set -euo pipefail

run_doctor() {
    msg running_doctor
    sleep 1

    local xdg_curr="${XDG_CURRENT_DESKTOP:-}"
    if [ "$xdg_curr" = "niri" ]; then
        msg doctor_ok "Compositor: Niri is currently running."
    else
        msg doctor_warn "Compositor: Current desktop environment is '${xdg_curr:-Unknown}' (Niri is not running)."
    fi

    if [ -f "/usr/share/wayland-sessions/niri.desktop" ]; then
        msg doctor_ok "Session: Niri Wayland session desktop file is registered."
    else
        msg doctor_warn "Session: /usr/share/wayland-sessions/niri.desktop is missing. (Niri might not show up on your Display Manager login screen)"
    fi

    if ! command -v noctalia >/dev/null 2>&1; then
        msg doctor_err "Noctalia: Not installed (not found in PATH). Install via AUR: paru -S noctalia"
    elif noctalia msg status >/dev/null 2>&1; then
        msg doctor_ok "Noctalia Daemon: Running and responsive."
    else
        msg doctor_err "Noctalia Daemon: Not running. (Launch: niri msg action spawn -- noctalia)"
    fi

    local doc_pics_dir
    doc_pics_dir="$(get_pics_dir)"
    if [ -d "$doc_pics_dir/Wallpapers" ]; then
        msg doctor_ok "Wallpapers: $doc_pics_dir/Wallpapers directory exists."
    else
        msg doctor_err "Wallpapers: $doc_pics_dir/Wallpapers directory is missing."
    fi

    local missing_critical=0
    for cmd in niri noctalia fish starship; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            msg doctor_err "Dependency: '$cmd' is missing from PATH."
            missing_critical=$((missing_critical + 1))
        fi
    done

    if [ "$missing_critical" -eq 0 ]; then
        msg doctor_ok "Core Dependencies: All core tools (niri, noctalia, fish, starship) are installed."
    fi

    for script in "theme-sync.sh" "wallpaper-hook.sh" "mpvpaper-sync.sh"; do
        local path="$HOME/.config/noctalia/$script"
        if [ -f "$path" ]; then
            if [ -x "$path" ]; then
                msg doctor_ok "Scripts: $script is executable."
            else
                msg doctor_warn "Scripts: $script is not executable. Fixing permissions..."
                chmod +x "$path"
            fi
        fi
    done

    # Check clean-cache in fish config directory
    local cc_path="$HOME/.config/fish/clean-cache"
    if [ -f "$cc_path" ]; then
        if [ -x "$cc_path" ]; then
            msg doctor_ok "Scripts: clean-cache is executable."
        else
            msg doctor_warn "Scripts: clean-cache is not executable. Fixing permissions..."
            chmod +x "$cc_path"
        fi
    else
        msg doctor_err "Scripts: clean-cache is missing from ~/.config/fish/."
    fi

    # Check toggle-eyecare.sh in niri config directory
    local te_path="$HOME/.config/niri/toggle-eyecare.sh"
    if [ -f "$te_path" ]; then
        if [ -x "$te_path" ]; then
            msg doctor_ok "Scripts: toggle-eyecare.sh is executable."
        else
            msg doctor_warn "Scripts: toggle-eyecare.sh is not executable. Fixing permissions..."
            chmod +x "$te_path"
        fi
    fi

    # Check niri-scratch-toggle.sh in niri config directory
    local st_path="$HOME/.config/niri/niri-scratch-toggle.sh"
    if [ -f "$st_path" ]; then
        if [ -x "$st_path" ]; then
            msg doctor_ok "Scripts: niri-scratch-toggle.sh is executable."
        else
            msg doctor_warn "Scripts: niri-scratch-toggle.sh is not executable. Fixing permissions..."
            chmod +x "$st_path"
        fi
    fi

    if command -v wlsunset >/dev/null 2>&1; then
        msg doctor_ok "EyeCare Component: wlsunset is available for smooth warmth transition."
    else
        msg doctor_warn "EyeCare Component: wlsunset is missing (Night mode temperature ramp will be unavailable)."
    fi

    if command -v tmux >/dev/null 2>&1; then
        msg doctor_ok "Scratchpad Component: tmux is available for persistent session support."
    else
        msg doctor_warn "Scratchpad Component: tmux is missing (Scratchpad will run in temporary fallback mode)."
    fi

    local curr_shell="${SHELL:-}"
    if [[ "$curr_shell" == *fish ]]; then
        msg doctor_ok "Shell: Fish is the current default shell."
    else
        msg doctor_warn "Shell: Current shell is '$curr_shell', not Fish. (Change: chsh -s \$(which fish))"
    fi

    if command -v wpctl >/dev/null 2>&1; then
        msg doctor_ok "Audio Control: wpctl (WirePlumber) is available."
    else
        msg doctor_warn "Audio Control: wpctl is missing. (Volume control keys will not work)"
    fi

    if command -v ddcutil >/dev/null 2>&1 || command -v brightnessctl >/dev/null 2>&1; then
        msg doctor_ok "Brightness Control: ddcutil / brightnessctl is available."
    else
        msg doctor_warn "Brightness Control: ddcutil and brightnessctl are missing."
    fi

    if systemctl --user is-active xdg-desktop-portal >/dev/null 2>&1 || pgrep -f "xdg-desktop-portal" >/dev/null 2>&1; then
        msg doctor_ok "Desktop Portal: xdg-desktop-portal is active."
    else
        msg doctor_warn "Desktop Portal: xdg-desktop-portal is not active."
    fi

    # GTK portal backend (file dialogs / screen capture in GTK apps)
    if command -v pacman >/dev/null 2>&1 && pacman -Qq xdg-desktop-portal-gtk >/dev/null 2>&1; then
        msg doctor_ok "Desktop Portal: xdg-desktop-portal-gtk backend is installed."
    elif command -v pacman >/dev/null 2>&1; then
        msg doctor_warn "Desktop Portal: xdg-desktop-portal-gtk is missing. (GTK apps may lack native file dialogs; install with: paru -S xdg-desktop-portal-gtk)"
    fi

    # Free disk space on $HOME (10 GiB threshold)
    local disk_free_kb=""
    disk_free_kb=$(df -k --output=avail "$HOME" 2>/dev/null | awk 'NR==2{print $1}' || true)
    if [ -n "${disk_free_kb:-}" ]; then
        if [ "$disk_free_kb" -lt $((10 * 1024 * 1024)) ]; then
            local free_human
            free_human=$(awk -v k="$disk_free_kb" 'BEGIN{ if (k >= 1048576) printf "%.1f GiB", k/1048576; else if (k >= 1024) printf "%.1f MiB", k/1024; else printf "%d KiB", k }')
            msg doctor_warn "Disk Space: only $free_human free on $HOME. (Try: clean-cache or nyxniri snapshot prune)"
        else
            msg doctor_ok "Disk Space: sufficient free space on $HOME."
        fi
    fi

    # NyxMellow fcitx5 skin enabled state (only relevant when fcitx5 is around)
    if command -v fcitx5 >/dev/null 2>&1 || [ -f "$HOME/.config/fcitx5/conf/classicui.conf" ]; then
        if fcitx_enabled; then
            msg doctor_ok "Fcitx5: NyxMellow skin is enabled (will auto-refresh on update)."
        else
            msg doctor_warn "Fcitx5: NyxMellow skin not enabled. (Run: nyxniri fcitx install)"
        fi
    fi

    # Virtual Machine Check
    if command -v lspci >/dev/null 2>&1 && lspci | grep -i -q "VMware\|VirtualBox\|QEMU\|Virtio"; then
        msg doctor_warn "Virtual Machine detected (VMware/VirtualBox/QEMU). Ensure 'Accelerate 3D Graphics' is enabled in VM settings to avoid black screen in Niri Wayland!"
    fi

    greeter_status

    msg all_done
    msg reboot_hint
}

generate_bug_report() {
    msg generating_report
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="$HOME/nyxniri-bug-report-${timestamp}.md"

    {
        echo "# NyxNiri System Diagnostic Bug Report"
        echo "Generated at: $(date)"
        echo "Author / Maintainer: ech678"
        echo "Contact QQ: 2040244628 | Telegram: @Echoes678 | Linux Ricing QQ Group: 631425889"
        echo "Repository: https://github.com/ech678/NyxNiri"
        echo ""
        echo "## 1. System Information"
        echo '```text'
        echo "OS: $(grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '"' || echo 'Unknown')"
        echo "Kernel: $(uname -r 2>/dev/null || echo 'Unknown')"
        echo "Architecture: $(uname -m 2>/dev/null || echo 'Unknown')"
        echo "Desktop: ${XDG_CURRENT_DESKTOP:-Unknown} (${XDG_SESSION_TYPE:-Unknown})"
        echo "Shell: ${SHELL:-Unknown}"
        echo '```'
        echo ""
        echo "## 2. Hardware / Graphics"
        echo '```text'
        lspci -k 2>/dev/null | grep -A 2 -E "VGA|3D" || echo "lspci not available"
        echo '```'
        echo ""
        echo "## 3. Connected Displays (Niri)"
        echo '```text'
        if command -v niri >/dev/null 2>&1; then
            niri msg outputs 2>/dev/null || echo "niri msg outputs failed (is Niri running?)"
        else
            echo "niri is not installed"
        fi
        echo '```'
        echo ""
        echo "## 4. Installed Tool Versions"
        echo '```text'
        for cmd in niri noctalia fish starship kitty mpvpaper wpctl ddcutil brightnessctl; do
            if command -v "$cmd" >/dev/null 2>&1; then
                local ver=""
                if [ "$cmd" = "wpctl" ]; then
                    ver=$(wireplumber --version 2>&1 | grep -i "libwireplumber" | head -n 1 || true)
                    [ -z "$ver" ] && ver=$(pacman -Q wireplumber 2>/dev/null || echo "installed")
                elif [ "$cmd" = "mpvpaper" ]; then
                    ver=$(pacman -Q mpvpaper mpvpaper-git 2>/dev/null | head -n 1 || echo "installed")
                else
                    ver=$($cmd --version 2>&1 | head -n 1 || echo "installed")
                fi
                echo "$cmd: ${ver:-installed}"
            else
                echo "$cmd: NOT INSTALLED"
            fi
        done
        echo '```'
        echo ""
        echo "## 5. Daemon & Service Status"
        echo '```text'
        echo "--- Noctalia status ---"
        noctalia msg status 2>/dev/null || echo "Noctalia daemon not responding"
        echo ""
        echo "--- Desktop portal status ---"
        systemctl --user status xdg-desktop-portal 2>/dev/null | head -n 10 || echo "xdg-desktop-portal service check failed"
        echo '```'
        echo ""
        echo "## 6. NyxNiri Health Checks"
        echo '```text'
        if command -v pacman >/dev/null 2>&1; then
            echo "xdg-desktop-portal-gtk: $(pacman -Qq xdg-desktop-portal-gtk 2>/dev/null || echo 'NOT INSTALLED')"
        fi
        df -h "$HOME" 2>/dev/null | awk 'NR==2{print "home free space:", $4}'
        if command -v fcitx5 >/dev/null 2>&1 || [ -f "$HOME/.config/fcitx5/conf/classicui.conf" ]; then
            if fcitx_enabled; then
                echo "fcitx5 nyxmellow: enabled"
            else
                echo "fcitx5 nyxmellow: NOT enabled"
            fi
        fi
        echo '```'
        echo ""
        echo "## 7. Noctalia Hook Log (Last 20 Lines)"
        echo '```text'
        local hook_log="${XDG_STATE_HOME:-$HOME/.local/state}/noctalia/hook.log"
        if [ -f "$hook_log" ]; then
            tail -n 20 "$hook_log"
        else
            echo "No hook.log found at $hook_log"
        fi
        echo '```'
        echo ""
        echo "## 8. Systemd User Journal Logs (Last 30 Lines)"
        echo '```text'
        journalctl --user -n 30 --no-pager 2>/dev/null || echo "journalctl log access unavailable"
        echo '```'
        echo ""
        echo "## 9. NyxNiri Installer Log (Last 30 Lines)"
        echo '```text'
        if [ -f "${INSTALL_LOG:-}" ]; then
            tail -n 30 "$INSTALL_LOG"
        else
            echo "No install.log found at ${INSTALL_LOG:-$HOME/.local/state/NyxNiri/install.log}"
        fi
        echo '```'
    } > "$report_file"

    msg report_done "$report_file"
}
