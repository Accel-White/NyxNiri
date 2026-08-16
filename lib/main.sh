#!/usr/bin/env bash

# ==============================================================================
# NyxNiri — Noctalia V5 & Niri Dotfiles Installer & Toolbox (Main Entrypoint)
# Bilingual (English/中文), menu-driven operations, config backup, doctor & update.
# ==============================================================================

set -euo pipefail

# Resolve script directory & source library modules
REAL_SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
LIB_DIR="$(cd "$(dirname "$REAL_SCRIPT_PATH")" 2>/dev/null && pwd)"

# Source all sibling lib modules
source "$LIB_DIR/core.sh"
source "$LIB_DIR/i18n.sh"
source "$LIB_DIR/network.sh"
source "$LIB_DIR/deps.sh"
source "$LIB_DIR/backup.sh"
source "$LIB_DIR/deploy.sh"
source "$LIB_DIR/doctor.sh"
source "$LIB_DIR/greeter.sh"
source "$LIB_DIR/fcitx.sh"

init_environment_paths

# ==============================================================================
# Command Menu & Entrypoint Loop
# ==============================================================================
press_any_key() {
    if [ -t 0 ] && [ -c /dev/tty ]; then
        # shellcheck disable=SC2034  # read key is intentionally discarded
        read -r -p "$(msg press_any_key)" -n 1 _k < /dev/tty || sleep 1
    fi
}

snapshot_menu() {
    local cur_focus=0
    clear 2>/dev/null || true

    while true; do
        printf '\e[?25l\e[H'
        show_logo
        msg snapshot_menu_title

        _render_menu_item 0 "$(msg snapshot_sub_create)" "$cur_focus"
        _render_menu_item 1 "$(msg snapshot_sub_list)" "$cur_focus"
        _render_menu_item 2 "$(msg snapshot_sub_delete)" "$cur_focus" "warn"
        _render_menu_item 3 "$(msg snapshot_sub_rollback)" "$cur_focus"
        _render_menu_item 4 "$(msg snapshot_sub_back)" "$cur_focus" "subtle"

        echo ""
        msg submenu_hint
        echo ""
        printf '\e[J'

        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            break
        fi

        local key
        key=$(read_key) || break

        local act=-1
        case "$key" in
            UP|[kK])
                cur_focus=$((cur_focus - 1))
                [ "$cur_focus" -lt 0 ] && cur_focus=4
                ;;
            DOWN|[jJ])
                cur_focus=$((cur_focus + 1))
                [ "$cur_focus" -gt 4 ] && cur_focus=0
                ;;
            ENTER|SPACE)
                act=$cur_focus
                ;;
            [1-4])
                cur_focus=$((key - 1))
                act=$cur_focus
                ;;
            0|[qQ]|ESC)
                cur_focus=4
                act=4
                ;;
        esac

        if [ "$act" -ne -1 ]; then
            printf '\e[?25h'
            case "$act" in
                0)
                    discover_config_items
                    local note_in=""
                    read -r -p "$(msg snapshot_note_prompt)" note_in < /dev/tty || note_in=""
                    backup_configs "$note_in"
                    press_any_key
                    ;;
                1)
                    list_backups
                    press_any_key
                    ;;
                2)
                    discover_config_items
                    delete_backup ""
                    press_any_key
                    ;;
                3)
                    discover_config_items
                    rollback_configs ""
                    press_any_key
                    ;;
                4)
                    return 0
                    ;;
            esac
            clear 2>/dev/null || true
        fi
    done
    printf '\e[?25h'
}

greeter_menu() {
    local cur_focus=0
    clear 2>/dev/null || true

    while true; do
        printf '\e[?25l\e[H'
        show_logo
        msg greeter_menu_title

        _render_menu_item 0 "$(msg greeter_sub_install)" "$cur_focus"
        _render_menu_item 1 "$(msg greeter_sub_status)" "$cur_focus"
        _render_menu_item 2 "$(msg greeter_sub_uninstall)" "$cur_focus" "warn"
        _render_menu_item 3 "$(msg greeter_sub_back)" "$cur_focus" "subtle"

        echo ""
        msg submenu_hint
        echo ""
        printf '\e[J'

        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            break
        fi

        local key
        key=$(read_key) || break

        local act=-1
        case "$key" in
            UP|[kK])
                cur_focus=$((cur_focus - 1))
                [ "$cur_focus" -lt 0 ] && cur_focus=3
                ;;
            DOWN|[jJ])
                cur_focus=$((cur_focus + 1))
                [ "$cur_focus" -gt 3 ] && cur_focus=0
                ;;
            ENTER|SPACE)
                act=$cur_focus
                ;;
            [1-3])
                cur_focus=$((key - 1))
                act=$cur_focus
                ;;
            0|[qQ]|ESC)
                cur_focus=3
                act=3
                ;;
        esac

        if [ "$act" -ne -1 ]; then
            printf '\e[?25h'
            case "$act" in
                0) greeter_install; press_any_key ;;
                1) greeter_status; press_any_key ;;
                2) greeter_uninstall; press_any_key ;;
                3) return 0 ;;
            esac
            clear 2>/dev/null || true
        fi
    done
    printf '\e[?25h'
}

fcitx_menu() {
    local cur_focus=0
    clear 2>/dev/null || true

    while true; do
        printf '\e[?25l\e[H'
        show_logo
        msg fcitx_menu_title

        _render_menu_item 0 "$(msg fcitx_sub_install)" "$cur_focus"
        _render_menu_item 1 "$(msg fcitx_sub_status)" "$cur_focus"
        _render_menu_item 2 "$(msg fcitx_sub_uninstall)" "$cur_focus" "warn"
        _render_menu_item 3 "$(msg fcitx_sub_back)" "$cur_focus" "subtle"

        echo ""
        msg submenu_hint
        echo ""
        printf '\e[J'

        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            break
        fi

        local key
        key=$(read_key) || break

        local act=-1
        case "$key" in
            UP|[kK])
                cur_focus=$((cur_focus - 1))
                [ "$cur_focus" -lt 0 ] && cur_focus=3
                ;;
            DOWN|[jJ])
                cur_focus=$((cur_focus + 1))
                [ "$cur_focus" -gt 3 ] && cur_focus=0
                ;;
            ENTER|SPACE)
                act=$cur_focus
                ;;
            [1-3])
                cur_focus=$((key - 1))
                act=$cur_focus
                ;;
            0|[qQ]|ESC)
                cur_focus=3
                act=3
                ;;
        esac

        if [ "$act" -ne -1 ]; then
            printf '\e[?25h'
            case "$act" in
                0) fcitx_install; press_any_key ;;
                1) fcitx_status; press_any_key ;;
                2) fcitx_uninstall; press_any_key ;;
                3) return 0 ;;
            esac
            clear 2>/dev/null || true
        fi
    done
    printf '\e[?25h'
}

optional_modules_menu() {
    local cur_focus=0
    clear 2>/dev/null || true

    while true; do
        printf '\e[?25l\e[H'
        show_logo
        msg optmod_menu_title

        local label0 label1 label2 label3
        label0="$(_disp_pad "$(msg optmod_sub_apps)" 26)"
        label1="$(_disp_pad "Noctalia Greeter" 26)$(greeter_status_label)"
        label2="$(_disp_pad "$(msg optmod_sub_fcitx)" 26)$(fcitx_status_label)"
        label3="$(_disp_pad "$(msg optmod_sub_wallpapers)" 26)$(wallpapers_status_label)"

        _render_menu_item 0 "$label0" "$cur_focus"
        _render_menu_item 1 "$label1" "$cur_focus"
        _render_menu_item 2 "$label2" "$cur_focus"
        _render_menu_item 3 "$label3" "$cur_focus"
        _render_menu_item 4 "$(msg optmod_purge)" "$cur_focus" "warn"
        _render_menu_item 5 "$(msg optmod_back)" "$cur_focus" "subtle"

        echo ""
        msg submenu_hint
        echo ""
        printf '\e[J'

        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            break
        fi

        local key
        key=$(read_key) || break

        local act=-1
        case "$key" in
            UP|[kK])
                cur_focus=$((cur_focus - 1))
                [ "$cur_focus" -lt 0 ] && cur_focus=5
                ;;
            DOWN|[jJ])
                cur_focus=$((cur_focus + 1))
                [ "$cur_focus" -gt 5 ] && cur_focus=0
                ;;
            ENTER|SPACE)
                act=$cur_focus
                ;;
            [1-5])
                cur_focus=$((key - 1))
                act=$cur_focus
                ;;
            0|[qQ]|ESC)
                cur_focus=5
                act=5
                ;;
        esac

        if [ "$act" -ne -1 ]; then
            printf '\e[?25h'
            case "$act" in
                0) run_optional_apps_menu_loop || true ;;
                1) greeter_menu ;;
                2) fcitx_menu ;;
                3) deploy_wallpapers "y"; press_any_key ;;
                4) discover_config_items; uninstall_nyxniri "purge"; press_any_key ;;
                5) return 0 ;;
            esac
            clear 2>/dev/null || true
        fi
    done
    printf '\e[?25h'
}

main_menu() {
    local cur_focus=0
    clear 2>/dev/null || true

    while true; do
        printf '\e[?25l\e[H'
        show_logo
        msg menu_title

        msg menu_group_deploy
        _render_menu_item 0 "$(msg menu_opt1)" "$cur_focus"
        _render_menu_item 1 "$(msg menu_opt2)" "$cur_focus"

        msg menu_group_maint
        _render_menu_item 2 "$(msg menu_opt3)" "$cur_focus"
        _render_menu_item 3 "$(msg menu_opt4)" "$cur_focus"
        _render_menu_item 4 "$(msg menu_opt5)" "$cur_focus"
        _render_menu_item 5 "$(msg menu_opt6)" "$cur_focus"

        msg menu_group_system
        _render_menu_item 6 "$(msg menu_opt7)" "$cur_focus" "warn"
        _render_menu_item 7 "$(msg menu_opt8)" "$cur_focus"
        _render_menu_item 8 "$(msg menu_opt0)" "$cur_focus" "subtle"

        echo ""
        msg menu_hint
        echo ""
        printf '\e[J'

        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            break
        fi

        local key
        key=$(read_key) || break

        local action_item=-1
        case "$key" in
            UP|[kK])
                cur_focus=$((cur_focus - 1))
                [ "$cur_focus" -lt 0 ] && cur_focus=8
                ;;
            DOWN|[jJ])
                cur_focus=$((cur_focus + 1))
                [ "$cur_focus" -gt 8 ] && cur_focus=0
                ;;
            ENTER|SPACE)
                action_item=$cur_focus
                ;;
            [1-8])
                cur_focus=$((key - 1))
                action_item=$cur_focus
                ;;
            0|[qQ]|exit|ESC)
                cur_focus=8
                action_item=8
                ;;
        esac

        if [ "$action_item" -ne -1 ]; then
            printf '\e[?25h'
            case "$action_item" in
                0) install_configs "full" || true ;;
                1) deps_menu || true ;;
                2) snapshot_menu ;;
                3) RUN_FROM_MENU=1 update_repo_and_script "" || true; press_any_key ;;
                4) run_doctor; press_any_key ;;
                5) generate_bug_report; press_any_key ;;
                6) uninstall_nyxniri ""; press_any_key ;;
                7) optional_modules_menu ;;
                8) exit 0 ;;
            esac
            clear 2>/dev/null || true
        fi
    done
    printf '\e[?25h'
}

main() {
    if [ "$(id -u)" -eq 0 ]; then
        msg err_root_denied
        echo -e "[✗] Do not run as root. Re-run as normal user: ./install.sh\n"
        exit 1
    fi

    acquire_lock
    init_logger
    log_msg "INFO" "NyxNiri CLI launched in $RUN_MODE mode ($MODE_LABEL)"
    ensure_nyxniri_symlink

    if [ $# -gt 0 ]; then
        case "$1" in
            install|deploy)
                shift
                discover_config_items
                install_configs "full"
                exit 0
                ;;
            snapshot|backup)
                shift
                discover_config_items
                if [ "${1:-}" = "delete" ] || [ "${1:-}" = "rm" ]; then
                    shift || true
                    delete_backup "${1:-}"
                else
                    backup_configs "$*" "non_interactive"
                fi
                exit 0
                ;;
            rollback|restore)
                shift
                discover_config_items
                rollback_configs "${1:-}"
                exit 0
                ;;
            list)
                list_backups
                exit 0
                ;;
            uninstall|remove)
                shift
                discover_config_items
                uninstall_nyxniri "${1:-}"
                exit 0
                ;;
            purge)
                discover_config_items
                uninstall_nyxniri "purge"
                exit 0
                ;;
            doctor)
                run_doctor
                exit 0
                ;;
            deps)
                shift
                case "${1:-}" in
                    core)
                        run_dep_menu_loop
                        exit 0
                        ;;
                    apps|opt|optional)
                        run_optional_apps_menu_loop
                        exit 0
                        ;;
                    *)
                        deps_menu
                        exit 0
                        ;;
                esac
                ;;
            apps|recommended)
                run_optional_apps_menu_loop
                exit 0
                ;;
            wallpapers|wp)
                deploy_wallpapers "y"
                exit 0
                ;;
            bug|report)
                generate_bug_report
                exit 0
                ;;
            test)
                discover_config_items
                test_deploy
                exit 0
                ;;
            greeter)
                shift
                case "${1:-}" in
                    install|setup)
                        greeter_install
                        exit $?
                        ;;
                    uninstall|remove)
                        greeter_uninstall
                        exit $?
                        ;;
                    *)
                        greeter_status
                        exit $?
                        ;;
                esac
                ;;
            fcitx)
                shift
                case "${1:-}" in
                    install|setup)
                        fcitx_install
                        exit $?
                        ;;
                    uninstall|remove)
                        fcitx_uninstall
                        exit $?
                        ;;
                    status)
                        fcitx_status
                        exit $?
                        ;;
                    *)
                        fcitx_usage
                        exit 0
                        ;;
                esac
                ;;
            update)
                shift
                update_repo_and_script "${1:-}"
                exit 0
                ;;
            help|-h|--help)
                echo "$PROJECT_NAME Dotfiles Management Tool ($CLI_CMD)"
                echo "Usage: $CLI_CMD [command] [args]"
                echo ""
                echo "Commands:"
                echo "  install [full|config] Deploy dotfiles and install dependencies"
                echo "  snapshot [note]      Create a snapshot of current dotfiles config"
                echo "  snapshot delete [idx] Delete a snapshot (interactive if no index)"
                echo "  rollback [index]     Rollback configuration to a historical snapshot"
                echo "  list                 List all available configuration snapshots"
                echo "  uninstall            Safely uninstall NyxNiri (with auto config archive)"
                echo "  purge                Deep purge all NyxNiri configs, cache & wallpapers"
                echo "  doctor               Run System Doctor diagnostics"
                echo "  deps [core|apps]     Open dependency or recommended apps menu"
                echo "  apps                 Open recommended software installer (Nautilus, Mission Center, Fcitx5)"
                echo "  wallpapers           Download the full wallpaper & video pack from the external repo"
                echo "  bug|report           Generate a diagnostic bug report"
                echo "  test                 Test deploy (no backup, keep monitor.kdl, idempotent)"
                echo "  greeter [install|status|uninstall]  Optional Noctalia Greeter (greetd login) setup"
                echo "  fcitx [install|status|uninstall]    Optional NyxMellow dynamic fcitx5 skin (Noctalia colors)"
                echo "  update [--force]     Update repository and optionally overwrite configs"
                echo "  help                 Show this help message"
                echo "  (no arguments)       Open interactive control panel menu"
                exit 0
                ;;
        esac
    fi

    select_language
    ensure_repo
    discover_config_items
    main_menu
}

main "$@"
