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
        local k=""
        read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
    fi
}

snapshot_menu() {
    while true; do
        clear 2>/dev/null || true
        show_logo
        msg snapshot_menu_title
        msg snapshot_sub_create
        msg snapshot_sub_list
        msg snapshot_sub_delete
        msg snapshot_sub_rollback
        msg snapshot_sub_back
        echo ""
        local opt=""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "> " opt < /dev/tty || opt=""
        else
            break
        fi
        case "$opt" in
            1)
                discover_config_items
                local note_in=""
                read -p "$(msg snapshot_note_prompt)" note_in < /dev/tty || note_in=""
                backup_configs "$note_in"
                ;;
            2)
                list_backups
                ;;
            3)
                discover_config_items
                delete_backup ""
                ;;
            4)
                discover_config_items
                rollback_configs ""
                ;;
            0|q)
                return 0
                ;;
            *)
                msg invalid_opt
                sleep 1
                ;;
        esac
        press_any_key
    done
}

greeter_menu() {
    while true; do
        clear 2>/dev/null || true
        show_logo
        msg greeter_menu_title
        msg greeter_sub_install
        msg greeter_sub_status
        msg greeter_sub_uninstall
        msg greeter_sub_back
        echo ""
        local opt=""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "> " opt < /dev/tty || opt=""
        else
            break
        fi
        case "$opt" in
            1) greeter_install ;;
            2) greeter_status ;;
            3) greeter_uninstall ;;
            0|q) return 0 ;;
            *) msg invalid_opt; sleep 1 ;;
        esac
        press_any_key
    done
}

fcitx_menu() {
    while true; do
        clear 2>/dev/null || true
        show_logo
        msg fcitx_menu_title
        msg fcitx_sub_install
        msg fcitx_sub_status
        msg fcitx_sub_uninstall
        msg fcitx_sub_back
        echo ""
        local opt=""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "> " opt < /dev/tty || opt=""
        else
            break
        fi
        case "$opt" in
            1) fcitx_install ;;
            2) fcitx_status ;;
            3) fcitx_uninstall ;;
            0|q) return 0 ;;
            *) msg invalid_opt; sleep 1 ;;
        esac
        press_any_key
    done
}

optional_modules_menu() {
    while true; do
        clear 2>/dev/null || true
        show_logo
        msg optmod_menu_title
        printf "  \e[1;32m1)\e[0m %s %s\n" "$(_disp_pad "Noctalia Greeter" 22)" "$(greeter_status_label)"
        printf "  \e[1;32m2)\e[0m %s %s\n" "$(_disp_pad "NyxMellow fcitx5 皮肤" 22)" "$(fcitx_status_label)"
        msg optmod_purge
        msg optmod_back
        echo ""
        local opt=""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "> " opt < /dev/tty || opt=""
        else
            break
        fi
        case "$opt" in
            1) greeter_menu ;;
            2) fcitx_menu ;;
            3) discover_config_items; uninstall_nyxniri "purge" ;;
            0|q) return 0 ;;
            *) msg invalid_opt; sleep 1 ;;
        esac
        press_any_key
    done
}

main_menu() {
    while true; do
        clear 2>/dev/null || true
        show_logo
        msg menu_title

        msg menu_group_deploy
        msg menu_opt1
        msg menu_opt2
        msg menu_opt3

        msg menu_group_backup
        msg menu_opt4

        msg menu_group_maint
        msg menu_opt5
        msg menu_opt6
        msg menu_opt7

        msg menu_group_system
        msg menu_opt8
        msg menu_opt9
        msg menu_opt0

        echo ""
        local opt=""
        if [ -t 0 ] && [ -c /dev/tty ]; then
            read -p "$(msg menu_prompt)" opt < /dev/tty || opt="0"
        else
            break
        fi

        case "$opt" in
            1)
                install_configs "full"
                press_any_key
                ;;
            2)
                install_configs "config_only"
                press_any_key
                ;;
            3)
                run_dep_menu_loop
                press_any_key
                ;;
            4)
                snapshot_menu
                ;;
            5)
                update_repo_and_script ""
                press_any_key
                ;;
            6)
                run_doctor
                press_any_key
                ;;
            7)
                generate_bug_report
                press_any_key
                ;;
            8)
                uninstall_nyxniri ""
                press_any_key
                ;;
            9)
                optional_modules_menu
                ;;
            0|q|exit)
                exit 0
                ;;
            *)
                msg invalid_opt
                sleep 1.5
                ;;
        esac
    done
}

main() {
    if [ "$(id -u)" -eq 0 ]; then
        echo -e "\n\e[1;31m[-] 错误: 请勿使用 root (或 sudo) 权限运行此脚本！\e[0m"
        echo -e "    NyxNiri Dotfiles 必须安装部署在普通用户账户下。"
        echo -e "    Error: Do NOT run this installer as root or with sudo!"
        echo -e "    Please re-run as normal user: ./install.sh\n"
        exit 1
    fi

    init_logger
    log_msg "INFO" "NyxNiri CLI launched in $RUN_MODE mode ($MODE_LABEL)"
    ensure_nyxniri_symlink

    if [ $# -gt 0 ]; then
        case "$1" in
            install|deploy)
                shift
                discover_config_items
                install_configs "${1:-full}"
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
                run_dep_menu_loop
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
                exit 0
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
                exit 0
                ;;
            update)
                shift
                update_repo_and_script "${1:-}"
                exit 0
                ;;
            help|-h|--help)
                echo "NyxNiri Dotfiles Management Tool (nyxniri)"
                echo "Usage: nyxniri [command] [args]"
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
                echo "  deps                 Open the dependency check & install menu"
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
