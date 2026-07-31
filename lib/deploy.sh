#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Dotfiles Atomic Deployment & Hardware Configuration Engine
# ==============================================================================

set -euo pipefail

# Replace dest with a copy of src without ever leaving dest half-deleted:
# copy to a sibling temp dir first (dest untouched if this fails), then swap
# in with rm+mv instead of a long-running rm+cp that a Ctrl+C/crash could
# interrupt mid-copy.
atomic_replace_item() {
    local src="$1" dest="$2"
    if [ -f "$src" ]; then
        local tmp_file="${dest}.new.$$"
        rm -f "$tmp_file" 2>/dev/null || true
        register_temp_path "$tmp_file"
        cp -a "$src" "$tmp_file" || { rm -f "$tmp_file" 2>/dev/null || true; return 1; }
        rm -f "$dest" 2>/dev/null || true
        mv "$tmp_file" "$dest"
        return 0
    fi

    local tmp_new="${dest}.new.$$"
    rm -rf "$tmp_new" 2>/dev/null || true
    register_temp_path "$tmp_new"
    cp -a "$src" "$tmp_new" || { rm -rf "$tmp_new" 2>/dev/null || true; return 1; }

    # [NEW] Dunder 私有命名空间继承 (High Robustness & Zero False Positives)
    if [ -d "$dest" ]; then
        # 1. 继承入口文件 (匹配 *__custom__*，跳过 *__custom__* 目录内部)
        (cd "$dest" && find . -type d -name "*__custom__*" -prune -o -type f -name "*__custom__*" -print0 2>/dev/null | while IFS= read -r -d '' file; do
            mkdir -p "$tmp_new/$(dirname "$file")"
            cp -a "$file" "$tmp_new/$file"
            echo "  Preserved custom file: $dest/${file#./}"
            if [ -n "${NYXNIRI_CUSTOM_LOG:-}" ]; then
                echo "    - File: $dest/${file#./}" >> "$NYXNIRI_CUSTOM_LOG"
            fi
        done || true)
        # 2. 继承整套自定义目录 (连根提取 *__custom__* 目录及其内部全部文件)
        (cd "$dest" && find . -type d -name "*__custom__*" -prune -print0 2>/dev/null | while IFS= read -r -d '' dir; do
            mkdir -p "$tmp_new/$(dirname "$dir")"
            cp -a "$dir" "$tmp_new/$(dirname "$dir")/"
            echo "  Preserved custom dir:  $dest/${dir#./}"
            if [ -n "${NYXNIRI_CUSTOM_LOG:-}" ]; then
                echo "    - Dir:  $dest/${dir#./}" >> "$NYXNIRI_CUSTOM_LOG"
            fi
        done || true)
    fi

    rm -rf "$dest" 2>/dev/null || true
    mv "$tmp_new" "$dest"
}

atomic_replace_dir() {
    atomic_replace_item "$@"
}

deploy_selected_configs() {
    local do_backup="${1:-nobackup}"
    shift || true
    local items_to_deploy=("$@")
    if [ ${#items_to_deploy[@]} -eq 0 ]; then
        items_to_deploy=("${CONFIG_ITEMS[@]}")
    fi

    if [ "$do_backup" = "backup" ]; then
        backup_configs "auto_snapshot_before_deploy" "non_interactive"
    fi

    msg copying_configs
    local repo_config_dir="${REPO_DIR:-.}/$CONFIG_DIR_NAME"

    local _custom_log
    _custom_log=$(mktemp) || _custom_log=""
    export NYXNIRI_CUSTOM_LOG="$_custom_log"
    register_temp_path "$NYXNIRI_CUSTOM_LOG"

    mkdir -p "$HOME/.config"

    for item in "${items_to_deploy[@]}"; do
        local src="$repo_config_dir/$item"
        local dest="$HOME/.config/$item"

        if [ -e "$src" ]; then
            local temp_monitor=""
            if [ "$item" = "niri" ] && [ -f "$dest/monitor.kdl" ]; then
                local mon_choice="y"
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    read -p "$(msg ask_keep_monitor)" mon_choice < /dev/tty || mon_choice="y"
                fi
                if [[ "$mon_choice" =~ ^[Yy]$ || -z "$mon_choice" ]]; then
                    temp_monitor=$(mktemp)
                    register_temp_path "$temp_monitor"
                    cp "$dest/monitor.kdl" "$temp_monitor"
                fi
            fi

            atomic_replace_dir "$src" "$dest"

            if [ -n "$temp_monitor" ] && [ -f "$temp_monitor" ]; then
                cp "$temp_monitor" "$dest/monitor.kdl"
                rm -f "$temp_monitor" 2>/dev/null || true
                echo "  Preserved existing: ~/.config/niri/monitor.kdl"
            fi

            echo "  Deployed: ~/.config/$item"
        fi
    done

    local pics_dir
    pics_dir=$(xdg-user-dir PICTURES 2>/dev/null || echo "$HOME/Pictures")
    [ -z "$pics_dir" ] && pics_dir="$HOME/Pictures"
    local wp_dest="$pics_dir/Wallpapers"

    # Ensure scripts are executable and initial effects symlink exists
    if [ -f "$HOME/.config/fish/clean-cache" ]; then
        chmod +x "$HOME/.config/fish/clean-cache"
    fi
    if [ -f "$HOME/.config/niri/toggle-eyecare.sh" ]; then
        chmod +x "$HOME/.config/niri/toggle-eyecare.sh"
    fi
    if [ -f "$HOME/.config/niri/effects_normal.kdl" ] && [ ! -e "$HOME/.config/niri/effects.kdl" ]; then
        ln -sfn "$HOME/.config/niri/effects_normal.kdl" "$HOME/.config/niri/effects.kdl"
    fi

    # Post-process to replace hardcoded template home paths with actual '$HOME' and '$wp_dest' for portability
    local esc_home esc_wp_dest
    esc_home=$(printf '%s\n' "$HOME" | sed 's/[|&]/\\&/g')
    esc_wp_dest=$(printf '%s\n' "$wp_dest" | sed 's/[|&]/\\&/g')

    if [ -f "$HOME/.config/noctalia/noctalia-config.toml" ]; then
        # Language-agnostic TOML key-based replacement (works on all locales).
        # Wallpapers/video suffix is fixed; $wp_dest comes from xdg-user-dir PICTURES.
        local esc_wp_video_dest
        esc_wp_video_dest=$(printf '%s\n' "$wp_dest/video" | sed 's/[|&]/\\&/g')
        sed -i "s|^directory = \".*\"|directory = \"${esc_wp_dest}\"|" "$HOME/.config/noctalia/noctalia-config.toml"
        sed -i "s|^video_directory = \".*\"|video_directory = \"${esc_wp_video_dest}\"|" "$HOME/.config/noctalia/noctalia-config.toml"
        sed -i "s|/home/[^/]\+|${esc_home}|g" "$HOME/.config/noctalia/noctalia-config.toml"
    fi
    if [ -f "$HOME/.config/niri/config.kdl" ]; then
        sed -i "s|/home/[^/]\+|${esc_home}|g" "$HOME/.config/niri/config.kdl"
        local rel_pics_dir esc_rel_pics_dir
        if [[ "$pics_dir" == "$HOME"* ]]; then
            rel_pics_dir="~${pics_dir#$HOME}"
        else
            rel_pics_dir="$pics_dir"
        fi
        esc_rel_pics_dir=$(printf '%s\n' "$rel_pics_dir" | sed 's/[|&]/\\&/g')
        sed -i -E "s|^[[:space:]]*(//)?[[:space:]]*screenshot-path .*|screenshot-path \"${esc_rel_pics_dir}/Screenshots/Screenshot from %Y-%m-%d %H-%M-%S.png\"|g" "$HOME/.config/niri/config.kdl"
    fi
    if [ -f "$HOME/.config/fish/fish_variables" ]; then
        sed -i "s|/home/[^/]\+|${esc_home}|g" "$HOME/.config/fish/fish_variables"
    fi

    # GPU Hardware Detection: Automatically uncomment NVIDIA environment variables if NVIDIA GPU is present
    if [ -f "$HOME/.config/niri/config.kdl" ]; then
        if command -v lspci >/dev/null 2>&1 && lspci | grep -i -q "NVIDIA"; then
            echo ":: NVIDIA GPU detected. Enabling NVIDIA Wayland environment variables in config.kdl..."
            log_msg "INFO" "NVIDIA GPU detected via lspci. Enabled NVIDIA Wayland envs in config.kdl"
            sed -i 's|^[[:space:]]*//[[:space:]]*\(GBM_BACKEND "nvidia-drm"\)|\1|g' "$HOME/.config/niri/config.kdl"
            sed -i 's|^[[:space:]]*//[[:space:]]*\(__GLX_VENDOR_LIBRARY_NAME "nvidia"\)|\1|g' "$HOME/.config/niri/config.kdl"
            sed -i 's|^[[:space:]]*//[[:space:]]*\(LIBVA_DRIVER_NAME "nvidia"\)|\1|g' "$HOME/.config/niri/config.kdl"
        else
            echo ":: Non-NVIDIA GPU / Virtual Machine detected. Keeping NVIDIA envs disabled to prevent black screens."
            log_msg "INFO" "Non-NVIDIA / Virtual Machine GPU detected. NVIDIA envs kept disabled."
        fi
    fi

    # Post-deployment initialization: Trigger theme-sync to apply GTK and system theme settings
    if [ -f "$HOME/.config/noctalia/theme-sync.sh" ]; then
        chmod +x "$HOME/.config/noctalia/theme-sync.sh"
        bash "$HOME/.config/noctalia/theme-sync.sh" >/dev/null 2>&1 || true
        echo "  Initialized: Noctalia theme and GTK sync"
    fi

    # Enable Noctalia mpvpaper plugin if noctalia CLI is available
    if command -v noctalia >/dev/null 2>&1; then
        echo ":: Enabling Noctalia mpvpaper plugin..."
        noctalia msg plugins enable noctalia/mpvpaper 2>/dev/null || true
    fi

    # Install/Update Fisher plugins if fish is available
    if command -v fish >/dev/null 2>&1; then
        echo -e "\e[1;34m:: [Fisher] 正在检查/更新 Fisher 插件管理器...\e[0m"
        log_msg INFO "Checking Fisher plugin manager installation"
        local fisher_tmp
        fisher_tmp=$(mktemp)
        register_temp_path "$fisher_tmp"
        if fetch_raw_with_fallback "jorgebucaran/fisher" "main" "functions/fisher.fish" "$fisher_tmp"; then
            fish -c "
                if not functions -q fisher
                    source '$fisher_tmp' && fisher install jorgebucaran/fisher
                end
                if test -f ~/.config/fish/fish_plugins && functions -q fisher
                    echo 'Installing plugins listed in fish_plugins...'
                    fisher update || echo '[-] Fisher update skipped due to network connectivity issue.'
                end
            " || true
        else
            echo "[-] Fisher auto-install skipped due to network connectivity issues across all mirrors."
            log_msg WARN "Fisher auto-install skipped (all mirrors unreachable)"
        fi
    fi

    msg copy_done

    if [ -n "${NYXNIRI_CUSTOM_LOG:-}" ] && [ -s "$NYXNIRI_CUSTOM_LOG" ]; then
        echo -e "\n\e[1;36m==================================================\e[0m"
        echo -e "\e[1;36m[ NyxNiri Customizations Preserved ]\e[0m"
        cat "$NYXNIRI_CUSTOM_LOG"
        echo -e "\e[1;36m==================================================\e[0m\n"
    fi
    [ -n "${NYXNIRI_CUSTOM_LOG:-}" ] && rm -f "$NYXNIRI_CUSTOM_LOG" 2>/dev/null || true
    unset NYXNIRI_CUSTOM_LOG || true
}

deploy_wallpapers() {
    local pics_dir
    pics_dir=$(xdg-user-dir PICTURES 2>/dev/null || echo "$HOME/Pictures")
    [ -z "$pics_dir" ] && pics_dir="$HOME/Pictures"
    local wp_src="${REPO_DIR:-.}/Wallpapers"
    local wp_dest="$pics_dir/Wallpapers"

    if [ ! -d "$wp_src" ]; then
        return 0
    fi

    mkdir -p "$wp_dest"
    cp -an "$wp_src"/. "$wp_dest"/ 2>/dev/null || cp -a "$wp_src"/. "$wp_dest"/
    echo "  Deployed & Synced (incremental): $wp_dest"
}

run_selective_upgrade_menu() {
    local select_status=()
    for i in "${!CONFIG_ITEMS[@]}"; do
        select_status[$i]=1
    done

    while true; do
        clear 2>/dev/null || true
        show_logo
        msg selective_title
        for i in "${!CONFIG_ITEMS[@]}"; do
            local check=" "
            if [ "${select_status[$i]:-0}" -eq 1 ]; then
                check="*"
            else
                check=" "
            fi
            printf "  [%s] %2d) %s\n" "$check" "$((i+1))" "${CONFIG_ITEMS[$i]}"
        done
        echo ""
        msg selective_hint
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
            if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#CONFIG_ITEMS[@]}" ]; then
                local index=$((num-1))
                if [ "${select_status[$index]:-0}" -eq 1 ]; then
                    select_status[$index]=0
                else
                    select_status[$index]=1
                fi
            fi
        done
    done

    local chosen_items=()
    for i in "${!CONFIG_ITEMS[@]}"; do
        if [ "${select_status[$i]:-0}" -eq 1 ]; then
            chosen_items+=("${CONFIG_ITEMS[$i]}")
        fi
    done

    if [ ${#chosen_items[@]} -gt 0 ]; then
        msg upgrading_selected
        deploy_selected_configs "nobackup" "${chosen_items[@]}"
        msg overwrite_done
    else
        echo "No components selected."
    fi
}

offer_overwrite_upgrade() {
    local flag="${1:-}"
    if [ "$flag" = "--force" ] || [ "$flag" = "--deploy" ]; then
        deploy_selected_configs "nobackup"
        deploy_wallpapers
        return 0
    elif [ "$flag" = "--no-deploy" ]; then
        return 0
    fi

    if [ ! -t 0 ]; then
        deploy_selected_configs "nobackup"
        deploy_wallpapers
        return 0
    fi

    msg overwrite_title
    msg overwrite_opt1
    msg overwrite_opt2
    msg overwrite_opt3
    msg overwrite_opt4
    echo ""
    local mode_choice=""
    if [ -c /dev/tty ]; then
        read -p "$(msg overwrite_prompt)" mode_choice < /dev/tty || mode_choice="1"
    fi
    mode_choice="${mode_choice:-1}"

    case "$mode_choice" in
        1)
            deploy_selected_configs "nobackup"
            deploy_wallpapers
            msg overwrite_done
            ;;
        2)
            deploy_selected_configs "backup"
            deploy_wallpapers
            msg overwrite_done
            ;;
        3)
            run_selective_upgrade_menu
            ;;
        4)
            echo "Skipped config deployment."
            ;;
        *)
            deploy_selected_configs "nobackup"
            deploy_wallpapers
            msg overwrite_done
            ;;
    esac
}

install_configs() {
    local mode="${1:-full}"

    local choice=""
    if [ -t 0 ] && [ -c /dev/tty ]; then
        read -p "$(msg ask_backup_before_deploy)" choice < /dev/tty || choice="n"
    fi
    local do_backup="nobackup"
    if [[ "$choice" =~ ^[Yy]$ ]]; then
        do_backup="backup"
    fi

    deploy_selected_configs "$do_backup"
    deploy_wallpapers

    if [ "$mode" = "full" ]; then
        check_all_deps
        local missing_count=0
        for stat in "${DEP_STATUS[@]:-}"; do
            if [ "${stat:-0}" -eq 0 ]; then
                missing_count=$((missing_count + 1))
            fi
        done

        if [ "$missing_count" -gt 0 ]; then
            msg warn_deps_missing
            local ask_choice=""
            if [ -t 0 ] && [ -c /dev/tty ]; then
                read -p "$(msg ask_install_now)" ask_choice < /dev/tty || ask_choice="y"
            fi
            if [[ "$ask_choice" =~ ^[Yy]$ || -z "$ask_choice" ]]; then
                run_dep_menu_loop
            fi
        fi
    fi
}
