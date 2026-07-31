#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Dependency Management & System Package Helper
# ==============================================================================

set -euo pipefail

DEPS=(
    "niri"
    "noctalia"
    "fish"
    "starship"
    "kitty"
    "fastfetch"
    "eza"
    "mpvpaper"
    "ffmpeg"
    "jq"
    "inotify-tools"
    "fzf"
    "fd"
    "bat"
    "ttf-jetbrains-mono-nerd"
    "noto-fonts-cjk"
)

# Packages only available via AUR (not in official repos)
AUR_DEPS=(
    "noctalia"
    "mpvpaper"
)

declare -a DEP_STATUS=()
declare -a DEP_SELECT=()

check_all_deps() {
    DEP_STATUS=()
    for i in "${!DEPS[@]}"; do
        local cmd="${DEPS[$i]}"
        local is_installed=0

        # 1. Check pacman database first (most accurate for Arch/AUR packages)
        if command -v pacman >/dev/null 2>&1 && pacman -Qq "$cmd" >/dev/null 2>&1; then
            is_installed=1
        elif [ "$cmd" = "inotify-tools" ] && command -v inotifywait >/dev/null 2>&1; then
            is_installed=1
        elif [ "$cmd" = "ttf-jetbrains-mono-nerd" ] && command -v fc-list >/dev/null 2>&1 && fc-list : family 2>/dev/null | grep -qi "JetBrains"; then
            is_installed=1
        elif [ "$cmd" = "noto-fonts-cjk" ] && command -v fc-list >/dev/null 2>&1 && fc-list : family 2>/dev/null | grep -qi "Noto.*CJK"; then
            is_installed=1
        elif command -v "$cmd" >/dev/null 2>&1; then
            is_installed=1
        fi

        DEP_STATUS[$i]=$is_installed
    done
}

show_dep_menu() {
    clear 2>/dev/null || true
    show_logo
    msg dep_menu_title
    for i in "${!DEPS[@]}"; do
        local status=""
        local check=" "

        if [ "${DEP_STATUS[$i]:-0}" -eq 1 ]; then
            status=$(msg installed)
        else
            status=$(msg missing)
        fi

        if [ "${DEP_SELECT[$i]:-0}" -eq 1 ]; then
            check="*"
        else
            check=" "
        fi

        printf "  [%s] %2d) %-24s %s\n" "$check" "$((i+1))" "${DEPS[$i]}" "$status"
    done
    echo ""
    msg dep_menu_hint
}

run_dep_menu_loop() {
    check_all_deps
    DEP_SELECT=()
    for i in "${!DEPS[@]}"; do
        if [ "${DEP_STATUS[$i]:-0}" -eq 1 ]; then
            DEP_SELECT[$i]=0
        else
            DEP_SELECT[$i]=1
        fi
    done

    while true; do
        show_dep_menu
        local choice=""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "> " choice < /dev/tty || choice=""
        else
            break
        fi

        if [ -z "$choice" ]; then
            break
        fi

        for num in $choice; do
            if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#DEPS[@]}" ]; then
                local index=$((num-1))
                if [ "${DEP_SELECT[$index]:-0}" -eq 1 ]; then
                    DEP_SELECT[$index]=0
                else
                    DEP_SELECT[$index]=1
                fi
            fi
        done
    done

    install_selected_deps
}

install_selected_deps() {
    local repo_install=()
    local aur_install=()
    for i in "${!DEPS[@]}"; do
        if [ "${DEP_SELECT[$i]:-0}" -eq 1 ]; then
            local pkg="${DEPS[$i]}"
            local is_aur=0
            for aur in "${AUR_DEPS[@]}"; do
                if [ "$pkg" = "$aur" ]; then
                    is_aur=1
                    break
                fi
            done
            if [ "$is_aur" -eq 1 ]; then
                aur_install+=("$pkg")
            else
                repo_install+=("$pkg")
            fi
        fi
    done

    if [ ${#repo_install[@]} -eq 0 ] && [ ${#aur_install[@]} -eq 0 ]; then
        return
    fi

    msg installing_selected
    local pkg_manager=""
    local has_aur_helper=false
    if command -v paru >/dev/null 2>&1; then
        pkg_manager="paru"
        has_aur_helper=true
    elif command -v yay >/dev/null 2>&1; then
        pkg_manager="yay"
        has_aur_helper=true
    else
        pkg_manager="sudo pacman"
    fi

    # Install official repo packages
    if [ ${#repo_install[@]} -gt 0 ]; then
        $pkg_manager -S --noconfirm "${repo_install[@]}" || {
            echo "Some repo package installations failed. Continuing..."
        }
    fi

    # Install AUR packages (requires AUR helper)
    if [ ${#aur_install[@]} -gt 0 ]; then
        if [ "$has_aur_helper" = true ]; then
            $pkg_manager -S --noconfirm "${aur_install[@]}" || {
                echo "Some AUR package installations failed. Continuing..."
            }
        else
            local aur_list="${aur_install[*]}"
            msg aur_skip "$aur_list"
            msg aur_helper_required
        fi
    fi

    check_mpvpaper_version
}

check_mpvpaper_version() {
    if ! command -v mpvpaper >/dev/null 2>&1; then
        return
    fi

    msg checking_mpvpaper

    if LC_ALL=C pacman -Qi mpvpaper-git >/dev/null 2>&1; then
        local git_version
        git_version=$(LC_ALL=C pacman -Qi mpvpaper-git 2>/dev/null | awk '/^Version/{print $3}')
        msg mpvpaper_version_ok "git (${git_version:-unknown})"
        return
    fi

    local version
    version=$(LC_ALL=C pacman -Qi mpvpaper 2>/dev/null | awk '/^Version/{print $3}')
    if [ -z "$version" ]; then
        return
    fi

    local clean_ver
    clean_ver=$(echo "$version" | sed -E 's/^[0-9]+://; s/-.*//; s/[^0-9.]//g')
    local major minor
    major=$(echo "$clean_ver" | cut -d. -f1)
    minor=$(echo "$clean_ver" | cut -d. -f2)

    major=${major//[^0-9]/}
    minor=${minor//[^0-9]/}
    major=${major:-0}
    minor=${minor:-0}

    if [ "$major" -gt 1 ] || { [ "$major" -eq 1 ] && [ "$minor" -ge 9 ]; }; then
        msg mpvpaper_version_ok "$version"
    else
        msg mpvpaper_leak_warn "$version"
        local choice=""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "$(msg mpvpaper_upgrade_prompt)" choice < /dev/tty || choice="n"
        fi
        if [[ "$choice" =~ ^[Yy]$ ]]; then
            if command -v paru >/dev/null 2>&1; then
                paru -S --noconfirm mpvpaper-git && msg mpvpaper_upgrade_done || {
                    echo -e "\e[1;31m[-] Failed to install mpvpaper-git.\e[0m"
                }
            elif command -v yay >/dev/null 2>&1; then
                yay -S --noconfirm mpvpaper-git && msg mpvpaper_upgrade_done || {
                    echo -e "\e[1;31m[-] Failed to install mpvpaper-git.\e[0m"
                }
            else
                msg mpvpaper_upgrade_skip
            fi
        else
            msg mpvpaper_upgrade_skip
        fi
    fi
}
