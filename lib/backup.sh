#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Configuration Backup, Snapshot, Rollback & Uninstall Manager
# ==============================================================================

set -euo pipefail

BACKUP_BASE_DIR="$HOME/.config/NyxNiri/backups"
declare -a CONFIG_ITEMS=()

discover_config_items() {
    CONFIG_ITEMS=()
    local repo_v2="${REPO_DIR:-.}/$CONFIG_DIR_NAME"
    if [ -d "$repo_v2" ]; then
        for entry in "$repo_v2"/*; do
            if [ -e "$entry" ]; then
                local base
                base=$(basename "$entry")
                CONFIG_ITEMS+=("$base")
            fi
        done
    fi
    if [ ${#CONFIG_ITEMS[@]} -eq 0 ]; then
        CONFIG_ITEMS=("fish" "noctalia" "niri" "kitty" "fastfetch" "starship.toml" "zed")
    fi
}

backup_configs() {
    local note="${1:-}"

    msg backing_up
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$BACKUP_BASE_DIR/snapshot_$timestamp"

    local tmp_snap
    tmp_snap=$(mktemp -d) || return 1
    register_temp_path "$tmp_snap"

    for item in "${CONFIG_ITEMS[@]}"; do
        if [ -e "$HOME/.config/$item" ]; then
            cp -rP "$HOME/.config/$item" "$tmp_snap/"
            echo "  Backed up: ~/.config/$item"
        fi
    done

    if [ -n "$note" ]; then
        echo "$note" > "$tmp_snap/note.txt"
    fi

    mkdir -p "$BACKUP_BASE_DIR"
    mv "$tmp_snap" "$backup_dir"

    msg backup_done "$backup_dir"
}

declare -a ALL_BACKUPS=()
get_all_backups() {
    ALL_BACKUPS=()
    local -a raw=()
    if [ -d "$BACKUP_BASE_DIR" ]; then
        for d in "$BACKUP_BASE_DIR"/*; do
            [ -d "$d" ] && raw+=("$d")
        done
    fi
    # Backward-compatible legacy backup dirs left in ~/.config by older versions.
    for d in "$HOME/.config"/dotfiles_backup_*; do
        [ -d "$d" ] && raw+=("$d")
    done
    if [ ${#raw[@]} -gt 0 ]; then
        # ISO timestamps sort lexicographically = chronologically.
        mapfile -t ALL_BACKUPS < <(printf '%s\n' "${raw[@]}" | sort)
    fi
}

list_backups() {
    get_all_backups
    if [ ${#ALL_BACKUPS[@]} -eq 0 ] || [ -z "${ALL_BACKUPS[0]:-}" ] || [ ! -d "${ALL_BACKUPS[0]}" ]; then
        msg no_backups_found
        return 1
    fi

    msg available_backups
    local idx=1
    for b in "${ALL_BACKUPS[@]}"; do
        if [ -d "$b" ]; then
            local bname
            bname=$(basename "$b")
            local note=""
            if [ -f "$b/note.txt" ]; then
                note=" ($(cat "$b/note.txt"))"
            fi
            echo -e "  \e[1;32m[$idx]\e[0m $bname$note"
            idx=$((idx + 1))
        fi
    done
    return 0
}

rollback_configs() {
    local target_idx="${1:-}"
    get_all_backups
    if [ ${#ALL_BACKUPS[@]} -eq 0 ] || [ -z "${ALL_BACKUPS[0]:-}" ] || [ ! -d "${ALL_BACKUPS[0]}" ]; then
        msg no_backups_found
        return 1
    fi

    local valid_backups=()
    for b in "${ALL_BACKUPS[@]}"; do
        if [ -d "$b" ]; then
            valid_backups+=("$b")
        fi
    done

    if [ -z "$target_idx" ]; then
        list_backups
        echo ""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "$(msg select_rollback_target)" target_idx < /dev/tty || target_idx=""
        fi
    fi

    if [[ ! "$target_idx" =~ ^[0-9]+$ ]] || [ "$target_idx" -lt 1 ] || [ "$target_idx" -gt "${#valid_backups[@]}" ]; then
        msg rollback_invalid_num
        return 1
    fi

    local selected_backup="${valid_backups[$((target_idx-1))]}"
    local selected_bname
    selected_bname=$(basename "$selected_backup")

    # Safety auto-backup before rollback
    local pre_ts
    pre_ts=$(date +%Y%m%d_%H%M%S)
    local pre_dir="$BACKUP_BASE_DIR/pre_rollback_$pre_ts"
    local pre_tmp
    pre_tmp=$(mktemp -d) || return 1
    register_temp_path "$pre_tmp"
    for item in "${CONFIG_ITEMS[@]}"; do
        if [ -e "$HOME/.config/$item" ]; then
            cp -rP "$HOME/.config/$item" "$pre_tmp/"
        fi
    done
    echo "pre-rollback safety snapshot" > "$pre_tmp/note.txt"
    mkdir -p "$BACKUP_BASE_DIR"
    mv "$pre_tmp" "$pre_dir"
    msg pre_rollback_backup "$pre_dir"

    msg rolling_back "$selected_bname"
    for item in "${CONFIG_ITEMS[@]}"; do
        if [ -e "$selected_backup/$item" ]; then
            atomic_replace_dir "$selected_backup/$item" "$HOME/.config/$item"
            echo "  Restored: ~/.config/$item"
        fi
    done

    msg rollback_done "$selected_bname"
}

# Delete a single snapshot (by index, or interactive selection). The oldest
# snapshot may hold the pre-install state that "uninstall --restore" depends
# on, so deletion always requires explicit confirmation.
delete_backup() {
    local target_idx="${1:-}"
    get_all_backups
    if [ ${#ALL_BACKUPS[@]} -eq 0 ] || [ -z "${ALL_BACKUPS[0]:-}" ] || [ ! -d "${ALL_BACKUPS[0]}" ]; then
        msg no_backups_found
        return 1
    fi

    local valid_backups=()
    for b in "${ALL_BACKUPS[@]}"; do
        [ -d "$b" ] && valid_backups+=("$b")
    done

    if [ -z "$target_idx" ]; then
        list_backups
        echo ""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "$(msg select_rollback_target)" target_idx < /dev/tty || target_idx=""
        fi
    fi

    if [[ ! "$target_idx" =~ ^[0-9]+$ ]] || [ "$target_idx" -lt 1 ] || [ "$target_idx" -gt "${#valid_backups[@]}" ]; then
        msg delete_invalid_num
        return 1
    fi

    local selected="${valid_backups[$((target_idx-1))]}"
    local selected_name
    selected_name=$(basename "$selected")

    msg delete_confirm "$selected_name"
    local confirm=""
    if [ -t 0 ] && [ -c /dev/tty ]; then
        read -p "$(msg delete_prompt)" confirm < /dev/tty || confirm="n"
    fi
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        msg delete_cancelled
        return 0
    fi

    rm -rf "$selected" 2>/dev/null || true
    msg delete_done "$selected_name" "$(( ${#valid_backups[@]} - 1 ))"
}

uninstall_nyxniri() {
    local mode="${1:-}"
    if [ -z "$mode" ]; then
        msg uninstall_title
        msg uninstall_opt1
        msg uninstall_opt2
        msg uninstall_opt3
        msg uninstall_opt4
        echo ""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "$(msg uninstall_prompt)" mode < /dev/tty || mode=""
        fi
    fi

    case "$mode" in
        1|safe|--safe)
            local ts
            ts=$(date +%Y%m%d_%H%M%S)
            local archive_file="$HOME/.config/NyxNiri_final_backup_$ts.tar.gz"
            local temp_stage
            temp_stage=$(mktemp -d)
            register_temp_path "$temp_stage"
            for item in "${CONFIG_ITEMS[@]}"; do
                if [ -e "$HOME/.config/$item" ]; then
                    cp -rP "$HOME/.config/$item" "$temp_stage/"
                fi
            done
            tar -czf "$archive_file" -C "$temp_stage" . 2>/dev/null || true
            rm -rf "$temp_stage" 2>/dev/null || true
            msg uninstall_archived "$archive_file"

            for item in "${CONFIG_ITEMS[@]}"; do
                if [ -e "$HOME/.config/$item" ] && [ "$HOME/.config/$item" != "$HOME" ]; then
                    rm -rf "$HOME/.config/$item"
                    echo "  Removed: ~/.config/$item"
                fi
            done
            [ -L "$HOME/.local/bin/nyxniri" ] && rm -f "$HOME/.local/bin/nyxniri"
            fcitx_uninstall || true
            msg uninstall_done
            ;;
        2|restore|--restore)
            get_all_backups
            if [ ${#ALL_BACKUPS[@]} -gt 0 ] && [ -n "${ALL_BACKUPS[0]:-}" ] && [ -d "${ALL_BACKUPS[0]}" ]; then
                local earliest="${ALL_BACKUPS[0]}"
                local earliest_name
                earliest_name=$(basename "$earliest")
                echo "Restoring earliest pre-install configuration from: $earliest_name"
                for item in "${CONFIG_ITEMS[@]}"; do
                    if [ -e "$earliest/$item" ]; then
                        atomic_replace_dir "$earliest/$item" "$HOME/.config/$item"
                        echo "  Restored: ~/.config/$item"
                    fi
                done
                [ -L "$HOME/.local/bin/nyxniri" ] && rm -f "$HOME/.local/bin/nyxniri"
                msg restore_origin_done
            else
                msg no_backups_found
            fi
            ;;
        3|purge|--purge)
            for item in "${CONFIG_ITEMS[@]}"; do
                if [ -e "$HOME/.config/$item" ] && [ "$HOME/.config/$item" != "$HOME" ]; then
                    rm -rf "$HOME/.config/$item"
                fi
            done
            [ -L "$HOME/.local/bin/nyxniri" ] && rm -f "$HOME/.local/bin/nyxniri"
            [ -d "$HOME/.cache/NyxNiri" ] && rm -rf "$HOME/.cache/NyxNiri"
            [ -d "$HOME/.config/NyxNiri" ] && rm -rf "$HOME/.config/NyxNiri"
            fcitx_uninstall || true
            local pics_dir
            pics_dir="$(get_pics_dir)"
            [ -d "$pics_dir/Wallpapers" ] && rm -rf "$pics_dir/Wallpapers"
            msg purge_done
            ;;
        *)
            echo "Uninstall cancelled."
            return 0
            ;;
    esac
}
