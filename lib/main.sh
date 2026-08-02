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

init_environment_paths

# ==============================================================================
# Command Menu & Entrypoint Loop
# ==============================================================================
main_menu() {
    while true; do
        clear 2>/dev/null || true
        show_logo
        msg welcome
        msg menu_title

        msg menu_group_deploy
        msg menu_opt1
        msg menu_opt2
        msg menu_opt3

        msg menu_group_backup
        msg menu_opt4
        msg menu_opt5

        msg menu_group_maint
        msg menu_opt6
        msg menu_opt7
        msg menu_opt8

        msg menu_group_system
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
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    local k=""
                    read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
                fi
                ;;
            2)
                run_dep_menu_loop
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    local k=""
                    read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
                fi
                ;;
            3)
                install_configs "config_only"
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    local k=""
                    read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
                fi
                ;;
            4)
                local note_in=""
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    read -p "$(msg snapshot_note_prompt)" note_in < /dev/tty || note_in=""
                fi
                backup_configs "$note_in"
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    local k=""
                    read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
                fi
                ;;
            5)
                rollback_configs ""
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    local k=""
                    read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
                fi
                ;;
            6)
                update_repo_and_script ""
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    local k=""
                    read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
                fi
                ;;
            7)
                run_doctor
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    local k=""
                    read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
                fi
                ;;
            8)
                generate_bug_report
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    local k=""
                    read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
                fi
                ;;
            9)
                uninstall_nyxniri ""
                if [ -t 0 ] && [ -c /dev/tty ]; then
                    local k=""
                    read -p "$(msg press_any_key)" -n 1 k < /dev/tty || sleep 1
                fi
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
                backup_configs "$*" "non_interactive"
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
                echo "  rollback [index]     Rollback configuration to a historical snapshot"
                echo "  list                 List all available configuration snapshots"
                echo "  uninstall            Safely uninstall NyxNiri (with auto config archive)"
                echo "  purge                Deep purge all NyxNiri configs, cache & wallpapers"
                echo "  doctor               Run System Doctor diagnostics"
                echo "  greeter [install|status|uninstall]  Optional Noctalia Greeter (greetd login) setup"
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
