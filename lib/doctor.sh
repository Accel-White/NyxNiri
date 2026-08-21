#!/usr/bin/env bash

# ==============================================================================
# NyxNiri System Diagnostics (System Doctor & Bug Report Exporter)
# ==============================================================================

set -euo pipefail

run_doctor() {
    msg running_doctor
    sleep 1

    local xdg_curr="${XDG_CURRENT_DESKTOP:-}"
    if [ "$xdg_curr" = "$MAIN_WM" ]; then
        msg doctor_ok "Compositor: $MAIN_WM is currently running"
    else
        msg doctor_warn "Compositor: Current desktop environment is '${xdg_curr:-Unknown}' ($MAIN_WM is not running)"
    fi

    if [ -f "/usr/share/wayland-sessions/$MAIN_WM.desktop" ]; then
        msg doctor_ok "Session: $MAIN_WM Wayland session desktop file is registered"
    else
        msg doctor_warn "Session: /usr/share/wayland-sessions/$MAIN_WM.desktop is missing"
    fi

    if ! command -v "$THEME_ENGINE" >/dev/null 2>&1; then
        msg doctor_err "$THEME_ENGINE: Not installed in PATH"
    elif "$THEME_ENGINE" msg status >/dev/null 2>&1; then
        msg doctor_ok "$THEME_ENGINE Daemon: Running and responsive"
    else
        msg doctor_err "$THEME_ENGINE Daemon: Not running"
    fi

    local doc_pics_dir
    doc_pics_dir="$(get_pics_dir)"
    if [ -d "$doc_pics_dir/Wallpapers" ]; then
        msg doctor_ok "Wallpapers: $doc_pics_dir/Wallpapers directory exists"
    else
        msg doctor_err "Wallpapers: $doc_pics_dir/Wallpapers directory is missing"
    fi

    local missing_critical=0
    for cmd in "$MAIN_WM" "$THEME_ENGINE" fish starship; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            msg doctor_err "Dependency: '$cmd' is missing from PATH"
            missing_critical=$((missing_critical + 1))
        fi
    done

    if [ "$missing_critical" -eq 0 ]; then
        msg doctor_ok "Core Dependencies: All core tools ($MAIN_WM, $THEME_ENGINE, fish, starship) are installed"
    fi

    for script_info in \
        "$THEME_ENGINE/theme-sync.sh:theme-sync.sh" \
        "$THEME_ENGINE/wallpaper-hook.sh:wallpaper-hook.sh" \
        "$THEME_ENGINE/mpvpaper-sync.sh:mpvpaper-sync.sh" \
        "fish/clean-cache:clean-cache" \
        "$MAIN_WM/scripts/toggle-eyecare.sh:toggle-eyecare.sh" \
        "$MAIN_WM/scripts/niri-scratch-toggle.sh:niri-scratch-toggle.sh" \
        "$MAIN_WM/scripts/orbit-launcher.py:orbit-launcher.py" \
        "$MAIN_WM/scripts/niri-scratch-menu.py:niri-scratch-menu.py" \
        "$MAIN_WM/scripts/wallpaper-picker.py:wallpaper-picker.py"; do
        local rel_path="${script_info%%:*}"
        local name="${script_info##*:}"
        local full_path="$HOME/.config/$rel_path"
        if [ ! -f "$full_path" ] && [ -f "$HOME/.config/$MAIN_WM/$name" ]; then
            full_path="$HOME/.config/$MAIN_WM/$name"
        fi
        if [ -f "$full_path" ]; then
            if [ -x "$full_path" ]; then
                msg doctor_ok "Scripts: $name is executable"
            else
                msg doctor_warn "Scripts: $name is not executable. Fixing permissions…"
                chmod +x "$full_path"
            fi
        elif [ "$name" = "clean-cache" ]; then
            msg doctor_err "Scripts: clean-cache is missing from ~/.config/fish/"
        fi
    done

    if command -v wlsunset >/dev/null 2>&1; then
        msg doctor_ok "EyeCare Component: wlsunset is installed"
    else
        msg doctor_warn "EyeCare Component: wlsunset is missing"
    fi

    if command -v tmux >/dev/null 2>&1; then
        msg doctor_ok "Scratchpad Component: tmux is installed"
    else
        msg doctor_warn "Scratchpad Component: tmux is missing"
    fi

    if python3 -c "import gi; gi.require_version('Gtk', '3.0'); gi.require_version('GtkLayerShell', '0.1')" >/dev/null 2>&1; then
        msg doctor_ok "Orbit Launcher Component: GtkLayerShell Python runtime is available"
    else
        msg doctor_warn "Orbit Launcher Component: GtkLayerShell Python bindings missing (install python-gobject gtk-layer-shell)"
    fi

    local curr_shell="${SHELL:-}"
    if [[ "$curr_shell" == *fish ]]; then
        msg doctor_ok "Shell: Fish is the current default shell"
    else
        msg doctor_warn "Shell: Current shell is '$curr_shell', not Fish"
    fi

    if command -v wpctl >/dev/null 2>&1; then
        msg doctor_ok "Audio Control: wpctl (WirePlumber) is available"
    else
        msg doctor_warn "Audio Control: wpctl is missing"
    fi

    if command -v ddcutil >/dev/null 2>&1 || command -v brightnessctl >/dev/null 2>&1; then
        msg doctor_ok "Brightness Control: ddcutil / brightnessctl is available"
    else
        msg doctor_warn "Brightness Control: ddcutil and brightnessctl are missing"
    fi

    if systemctl --user is-active xdg-desktop-portal >/dev/null 2>&1 || pgrep -f "xdg-desktop-portal" >/dev/null 2>&1; then
        msg doctor_ok "Desktop Portal: xdg-desktop-portal is active"
    else
        msg doctor_warn "Desktop Portal: xdg-desktop-portal is not active"
    fi

    # GTK portal backend (file dialogs / screen capture in GTK apps)
    if command -v pacman >/dev/null 2>&1 && pacman -Qq xdg-desktop-portal-gtk >/dev/null 2>&1; then
        msg doctor_ok "Desktop Portal: xdg-desktop-portal-gtk backend is installed"
    elif command -v pacman >/dev/null 2>&1; then
        msg doctor_warn "Desktop Portal: xdg-desktop-portal-gtk is missing"
    fi

    if [ -f "$HOME/.config/xdg-desktop-portal/niri-portals.conf" ] || [ -f "$HOME/.config/xdg-desktop-portal/portals.conf" ]; then
        msg doctor_ok "Desktop Portal: niri-portals.conf routing is configured"
    fi

    # Free disk space on $HOME (10 GiB threshold)
    local disk_free_kb=""
    disk_free_kb=$(df -k --output=avail "$HOME" 2>/dev/null | awk 'NR==2{print $1}' || true)
    if [ -n "${disk_free_kb:-}" ]; then
        if [ "$disk_free_kb" -lt $((10 * 1024 * 1024)) ]; then
            local free_human
            free_human=$(awk -v k="$disk_free_kb" 'BEGIN{ if (k >= 1048576) printf "%.1f GiB", k/1048576; else if (k >= 1024) printf "%.1f MiB", k/1024; else printf "%d KiB", k }')
            msg doctor_warn "Disk Space: only $free_human free on $HOME"
        else
            msg doctor_ok "Disk Space: sufficient free space on $HOME"
        fi
    fi

    # NyxMellow fcitx5 skin enabled state (only relevant when fcitx5 is around)
    if command -v fcitx5 >/dev/null 2>&1 || [ -f "$HOME/.config/fcitx5/conf/classicui.conf" ]; then
        if fcitx_enabled; then
            msg doctor_ok "Fcitx5: NyxMellow skin is enabled"
        else
            msg doctor_warn "Fcitx5: $FCITX_THEME skin not enabled"
        fi
    fi

    # Virtual Machine Check
    if command -v lspci >/dev/null 2>&1 && lspci | grep -i -q "VMware\|VirtualBox\|QEMU\|Virtio"; then
        msg doctor_warn "Virtual Machine detected. Ensure 3D Graphics Acceleration is enabled in VM settings"
    fi

    greeter_status

    msg all_done
    msg reboot_hint
}

generate_bug_report() {
    msg generating_report
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="$HOME/$PROJECT_NAME-bug-report-${timestamp}.md"

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
        if command -v "$MAIN_WM" >/dev/null 2>&1; then
            "$MAIN_WM" msg outputs 2>/dev/null || echo "$MAIN_WM msg outputs failed (is $MAIN_WM running?)"
        else
            echo "$MAIN_WM is not installed"
        fi
        echo '```'
        echo ""
        echo "## 4. Installed Tool Versions"
        echo '```text'
        for cmd in "$MAIN_WM" "$THEME_ENGINE" fish starship kitty mpvpaper wpctl ddcutil brightnessctl; do
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
        "$THEME_ENGINE" msg status 2>/dev/null || echo "$THEME_ENGINE daemon not responding"
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
        local hook_log="${XDG_STATE_HOME:-$HOME/.local/state}/$THEME_ENGINE/hook.log"
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
