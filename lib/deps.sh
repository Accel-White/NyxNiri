#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Dependency Management & System Package Helper
# ==============================================================================

set -euo pipefail

DEPS=(
    "$MAIN_WM"
    "$THEME_ENGINE"
    "wlsunset"
    "fish"
    "starship"
    "kitty"
    "fastfetch"
    "eza"
    "mpvpaper"
    "ffmpeg"
    "jq"
    "tmux"
    "inotify-tools"
    "fzf"
    "ttf-jetbrains-mono"
    "ttf-jetbrains-mono-nerd"
    "noto-fonts-cjk"
)

# Packages only available via AUR (not in official repos)
AUR_DEPS=(
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
        elif [ "$cmd" = "ttf-jetbrains-mono" ] && command -v fc-list >/dev/null 2>&1 && fc-list : family 2>/dev/null | grep -qi "JetBrains Mono"; then
            is_installed=1
        elif [ "$cmd" = "ttf-jetbrains-mono-nerd" ] && command -v fc-list >/dev/null 2>&1 && fc-list : family 2>/dev/null | grep -qi "JetBrains.*Nerd"; then
            is_installed=1
        elif [ "$cmd" = "noto-fonts-cjk" ] && command -v fc-list >/dev/null 2>&1 && fc-list : family 2>/dev/null | grep -qi "Noto.*CJK"; then
            is_installed=1
        elif command -v "$cmd" >/dev/null 2>&1; then
            is_installed=1
        fi

        DEP_STATUS[i]=$is_installed
    done
}

show_dep_menu() {
    local focus="${1:-0}"
    printf '\e[?25l\e[H'
    show_logo
    msg dep_menu_title
    for i in "${!DEPS[@]}"; do
        local status=""
        local prefix="    "
        if [ "$i" -eq "$focus" ]; then
            prefix="  \e[1;36m❯ \e[0m"
        fi

        if [ "${DEP_STATUS[i]:-0}" -eq 1 ]; then
            status=$(msg installed)
        else
            status=$(msg missing)
        fi

        local check_str="\e[90m[ ]\e[0m"
        if [ "${DEP_SELECT[i]:-0}" -eq 1 ]; then
            check_str="\e[1;32m[✓]\e[0m"
        fi

        if [ "$i" -eq "$focus" ]; then
            printf "%b%b \e[1;37m%-24s\e[0m %s\n" "$prefix" "$check_str" "${DEPS[$i]}" "$status"
        else
            printf "%b%b %-24s %s\n" "$prefix" "$check_str" "${DEPS[$i]}" "$status"
        fi
    done
    echo ""
    msg dep_menu_hint
    echo ""
    printf '\e[J'
}

run_dep_menu_loop() {
    check_all_deps
    DEP_SELECT=()
    for i in "${!DEPS[@]}"; do
        if [ "${DEP_STATUS[i]:-0}" -eq 1 ]; then
            DEP_SELECT[i]=0
        else
            DEP_SELECT[i]=1
        fi
    done

    clear 2>/dev/null || true
    local cur_focus=0
    while true; do
        show_dep_menu "$cur_focus"

        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            break
        fi

        local key
        key=$(read_key) || break

        case "$key" in
            UP|[kK])
                cur_focus=$((cur_focus - 1))
                [ "$cur_focus" -lt 0 ] && cur_focus=$((${#DEPS[@]} - 1))
                ;;
            DOWN|[jJ])
                cur_focus=$((cur_focus + 1))
                [ "$cur_focus" -ge "${#DEPS[@]}" ] && cur_focus=0
                ;;
            SPACE)
                if [ "${DEP_SELECT[cur_focus]:-0}" -eq 1 ]; then
                    DEP_SELECT[cur_focus]=0
                else
                    DEP_SELECT[cur_focus]=1
                fi
                ;;
            ENTER|[iI])
                break
                ;;
            [aA])
                for i in "${!DEPS[@]}"; do DEP_SELECT[i]=1; done
                ;;
            [nN])
                for i in "${!DEPS[@]}"; do DEP_SELECT[i]=0; done
                ;;
            [1-9])
                local idx=$((key - 1))
                if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#DEPS[@]}" ]; then
                    cur_focus=$idx
                    if [ "${DEP_SELECT[idx]:-0}" -eq 1 ]; then
                        DEP_SELECT[idx]=0
                    else
                        DEP_SELECT[idx]=1
                    fi
                fi
                ;;
            [qQ]|0|ESC)
                printf '\e[?25h'
                msg install_cancelled
                return 1
                ;;
        esac
    done
    printf '\e[?25h'

    install_selected_deps
}

# Return the name of a *usable* AUR helper (paru/yay) on stdout, or non-zero.
# Presence alone is not enough: a prebuilt -bin helper is linked against the
# libalpm soname of the system that built it and can die at runtime on a
# different one (e.g. upstream Arch AUR vs CachyOS's libalpm v16). Running
# `--version` proves the binary actually executes.
aur_helper_usable() {
    local helper
    for helper in paru yay; do
        if command -v "$helper" >/dev/null 2>&1 && "$helper" --version >/dev/null 2>&1; then
            echo "$helper"
            return 0
        fi
    done
    return 1
}

# Bootstrap an AUR helper (paru) when none is usable. Runs as the normal user
# (never root); `makepkg -si` handles the privileged install via sudo.
# Strategy: prefer the official repo package (ABI always matches the local
# libalpm), then build the AUR *source* package on this machine. A prebuilt
# -bin helper is deliberately avoided — it is linked against the libalpm of
# whatever built it and fails at runtime elsewhere.
# Returns 0 only if a usable helper is available afterwards. Never aborts the
# caller on failure — every step is fault-tolerant.
ensure_aur_helper() {
    if aur_helper_usable >/dev/null 2>&1; then
        return 0
    fi

    if ! prompt_confirm aur_bootstrap_prompt "y"; then
        msg aur_bootstrap_skip
        return 1
    fi

    msg aur_bootstrap_start

    if ! command -v pacman >/dev/null 2>&1; then
        msg aur_bootstrap_failed
        return 1
    fi

    # An earlier failed bootstrap can leave paru-bin/paru-bin-debug installed.
    # They conflict with the paru package by name (same /usr/bin/paru), which
    # would abort both the repo install and `pacman -U` from the source build.
    # Remove them before attempting either path.
    if pacman -Qq paru-bin >/dev/null 2>&1; then
        msg aur_bootstrap_cleanup
        sudo pacman -Rdd --noconfirm paru-bin || true
    fi
    if pacman -Qq paru-bin-debug >/dev/null 2>&1; then
        sudo pacman -Rdd --noconfirm paru-bin-debug || true
    fi

    # 1) Official repo first (paru is in Arch extra and CachyOS): built against
    #    the system's own libalpm, so always ABI-compatible.
    if pacman -Si paru >/dev/null 2>&1; then
        msg aur_bootstrap_repo
        if sudo pacman -S --needed --noconfirm paru && aur_helper_usable >/dev/null 2>&1; then
            msg aur_bootstrap_ok
            return 0
        fi
        # Installed but unusable (should not happen for a repo build); remove it
        # so the source build below does not hit a file/name conflict.
        if pacman -Qq paru >/dev/null 2>&1; then
            sudo pacman -Rdd --noconfirm paru || true
        fi
    fi

    if ! sudo pacman -S --needed --noconfirm base-devel git; then
        msg aur_bootstrap_failed
        return 1
    fi

    # 2) AUR source package, compiled on this machine against the local libalpm.
    msg aur_bootstrap_source
    local build_dir
    build_dir=$(mktemp -d) || {
        msg aur_bootstrap_failed
        return 1
    }
    register_temp_path "$build_dir"

    if ! git clone --depth 1 -c http.lowSpeedLimit=0 -c http.lowSpeedTime=15 \
        https://aur.archlinux.org/paru.git "$build_dir/paru" 2>/dev/null; then
        msg aur_bootstrap_failed
        return 1
    fi

    if ! (cd "$build_dir/paru" && makepkg -si --noconfirm); then
        msg aur_bootstrap_failed
        return 1
    fi

    if aur_helper_usable >/dev/null 2>&1; then
        msg aur_bootstrap_ok
        return 0
    fi
    msg aur_bootstrap_failed
    return 1
}

install_selected_deps() {
    local repo_install=()
    local aur_install=()
    for i in "${!DEPS[@]}"; do
        if [ "${DEP_SELECT[i]:-0}" -eq 1 ]; then
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
    local mgr=""
    if mgr=$(aur_helper_usable); then
        pkg_manager="$mgr"
        has_aur_helper=true
    else
        pkg_manager="sudo pacman"
    fi

    # Install official repo packages
    if [ ${#repo_install[@]} -gt 0 ]; then
        $pkg_manager -S --noconfirm "${repo_install[@]}" || {
            msg log_official_pkgs_partial_fail
        }
    fi

    # Install AUR packages (bootstraps paru if no helper is available)
    if [ ${#aur_install[@]} -gt 0 ]; then
        if [ "$has_aur_helper" = false ] && ensure_aur_helper; then
            pkg_manager="paru"
            has_aur_helper=true
        fi
        if [ "$has_aur_helper" = true ]; then
            $pkg_manager -S --noconfirm "${aur_install[@]}" || {
                msg log_aur_pkgs_partial_fail
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
        git_version=$(LC_ALL=C pacman -Qi mpvpaper-git 2>/dev/null | awk '/^Version/{print $3}' || true)
        msg mpvpaper_version_ok "git (${git_version:-unknown})"
        return
    fi

    local version
    version=$(LC_ALL=C pacman -Qi mpvpaper 2>/dev/null | awk '/^Version/{print $3}' || true)
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
        if prompt_confirm mpvpaper_upgrade_prompt "n"; then
            local mgr=""
            if ! mgr=$(aur_helper_usable); then
                ensure_aur_helper || {
                    msg mpvpaper_upgrade_skip
                    return
                }
                mgr=$(aur_helper_usable) || {
                    msg mpvpaper_upgrade_skip
                    return
                }
            fi
            if $mgr -S --noconfirm mpvpaper-git; then
                msg mpvpaper_upgrade_done
            else
                msg err_mpvpaper_git_failed
            fi
        else
            msg mpvpaper_upgrade_skip
        fi
    fi
}
