#!/usr/bin/env bash

# ==============================================================================
# NyxNiri Translations & Internationalization (I18n)
# ==============================================================================

set -euo pipefail

show_logo() {
    echo -e "\e[1;35m"
    echo " ███╗   ██╗██╗   ██╗██╗  ██╗    ███╗   ██╗██╗██████╗ ██╗"
    echo " ████╗  ██║╚██╗ ██╔╝╚██╗██╔╝    ████╗  ██║██║██╔══██╗██║"
    echo " ██╔██╗ ██║ ╚████╔╝  ╚███╔╝     ██╔██╗ ██║██║██████╔╝██║"
    echo " ██║╚██╗██║  ╚██╔╝   ██╔██╗     ██║╚██╗██║██║██╔══██╗██║"
    echo " ██║ ╚████║   ██║   ██╔╝ ██╗    ██║ ╚████║██║██║  ██║██║"
    echo " ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝╚═╝"
    echo -e "\e[0m"
    echo -e "       \e[1;36mNoctalia V5 & Niri Desktop Environment Setup ${CURRENT_VERSION:-v2.x}\e[0m"
    echo -e "       \e[1;30m----------------------------------------------------\e[0m"
    echo -e "       \e[1;33mMode: ${MODE_LABEL:-Local Path} (${REPO_DIR:-.})\e[0m\n"
}

msg() {
    local key="$1"
    shift || true
    local p1="${1:-}"

    if [ "${LANG_MODE:-en}" = "zh" ]; then
        case "$key" in
            welcome) echo -e "\e[1;36m:: 欢迎使用 $PROJECT_NAME Dotfiles 桌面工具箱\e[0m" ;;
            lang_select) echo -e "请选择语言 / Select Language:" ;;
            checking_dep) echo -e "\n\e[1;34m:: 正在检查系统依赖项...\e[0m" ;;
            installed) echo -e "\e[1;32m[已安装]\e[0m" ;;
            missing) echo -e "\e[1;31m[未安装]\e[0m" ;;

            # Main Menu
            menu_title) echo -e "\n\e[1;35m=== $PROJECT_NAME 控制面板与工具箱 ===\e[0m" ;;
            menu_group_deploy) echo -e "  \e[1;36m[ 部署与安装 ]\e[0m" ;;
            menu_opt1) echo -e "  \e[1;32m1)\e[0m 一键完整部署 (依赖 + 配置)" ;;
            menu_opt2) echo -e "  \e[1;32m2)\e[0m 检查与安装依赖项" ;;
            menu_opt3) echo -e "  \e[1;32m3)\e[0m 仅部署配置文件" ;;

            menu_group_backup) echo -e "\n  \e[1;36m[ 备份与恢复 ]\e[0m" ;;
            menu_opt4) echo -e "  \e[1;32m4)\e[0m 创建配置安全快照" ;;
            menu_opt5) echo -e "  \e[1;32m5)\e[0m 一键回滚配置" ;;

            menu_group_maint) echo -e "\n  \e[1;36m[ 运维与诊断 ]\e[0m" ;;
            menu_opt6) echo -e "  \e[1;32m6)\e[0m 检查更新与可选覆盖" ;;
            menu_opt7) echo -e "  \e[1;32m7)\e[0m 运行 System Doctor 健康诊断" ;;
            menu_opt8) echo -e "  \e[1;32m8)\e[0m 生成 Bug Report 诊断报告" ;;

            menu_group_system) echo -e "\n  \e[1;36m[ 系统管理 ]\e[0m" ;;
            menu_opt9) echo -e "  \e[1;31m9)\e[0m 卸载与复原环境" ;;
            menu_opt0) echo -e "  \e[1;30m0)\e[0m 退出" ;;

            menu_prompt) echo -e ":: 请选择操作 [0-9]: " ;;
            invalid_opt) echo -e "\e[1;31m[-] 无效的选项，请重新选择。\e[0m" ;;
            press_any_key) echo -e "\n按任意键返回主菜单..." ;;
            generating_report) echo -e "\n\e[1;34m:: 正在收集系统诊断数据并生成 Bug Report 报告...\e[0m" ;;
            report_done) echo -e "\e[1;32m[+] Bug Report 报告已成功导出至:\e[0m $p1\n\e[1;36m提示: 提交 Issue 时请直接附上该文件或其内容！\nQQ 交流群: 631425889 | 开发者 QQ: 2040244628 | Telegram: @Echoes678\e[0m" ;;

            # Optional Overwrite Upgrade Strings
            overwrite_title) echo -e "\n\e[1;35m────────────────────────────────────────────────────────────────\e[0m\n \e[1;36m:: NyxNiri 配置覆盖升级\e[0m\n\e[1;35m────────────────────────────────────────────────────────────────\e[0m" ;;
            overwrite_opt1) echo -e "  \e[1;32m1)\e[0m 极速直接覆盖 (不建立备份，直接应用最新配置)" ;;
            overwrite_opt2) echo -e "  \e[1;36m2)\e[0m 安全备份覆盖 (先自动打安全快照，再应用配置)" ;;
            overwrite_opt3) echo -e "  \e[1;33m3)\e[0m 选择性/逐组件覆盖 (自由勾选要更新的组件)" ;;
            overwrite_opt4) echo -e "  \e[1;30m4)\e[0m 仅更新仓库与脚本 (保持当前 ~/.config 不变)" ;;
            overwrite_prompt) echo -e ":: 请选择覆盖模式 [1-4] (默认 1): " ;;
            selective_title) echo -e "\n\e[1;33m:: 请选择要覆盖升级的组件（输入数字切换，直接回车开始升级）：\e[0m" ;;
            selective_hint) echo -e "输入空格分隔的序列号（如 1 3）来勾选/取消，直接回车开始升级选中组件：" ;;
            upgrading_selected) echo -e "\n\e[1;34m:: 正在覆盖升级选中的组件配置...\e[0m" ;;
            overwrite_done) echo -e "\e[1;32m[+] 选中的配置文件已成功覆盖升级！\e[0m" ;;

            # Uninstall Strings
            uninstall_title) echo -e "\n\e[1;31m────────────────────────────────────────────────────────────────\e[0m\n \e[1;31m:: NyxNiri 卸载与复原工具\e[0m\n\e[1;31m────────────────────────────────────────────────────────────────\e[0m" ;;
            uninstall_opt1) echo -e "  \e[1;32m1)\e[0m 标准安全卸载 (推荐 - 打包备份当前配置，移除配置与 CLI)" ;;
            uninstall_opt2) echo -e "  \e[1;36m2)\e[0m 原路复原 (一键恢复安装 NyxNiri 之前的初始配置)" ;;
            uninstall_opt3) echo -e "  \e[1;31m3)\e[0m 彻底粉碎模式 (清除所有配置、快照、缓存与壁纸)" ;;
            uninstall_opt4) echo -e "  \e[1;30m4)\e[0m 取消返回" ;;
            uninstall_prompt) echo -e ":: 请选择卸载模式 [1-4]: " ;;
            uninstall_archived) echo -e "\e[1;32m[+] 已将当前配置成功归档保存至:\e[0m $p1" ;;
            uninstall_done) echo -e "\e[1;32m[+] NyxNiri 卸载完成！感谢您的使用。\e[0m" ;;
            purge_done) echo -e "\e[1;32m[+] 深度清理完毕，所有 NyxNiri 相关配置与缓存已完全粉碎。\e[0m" ;;
            restore_origin_done) echo -e "\e[1;32m[+] 已成功将您的电脑环境原路复原至安装前状态！\e[0m" ;;

            # Rollback Strings
            no_backups_found) echo -e "\e[1;33m[!] 未找到任何可用的配置快照！\e[0m" ;;
            available_backups) echo -e "\n\e[1;36m:: 可用的 NyxNiri 配置快照列表\e[0m" ;;
            select_rollback_target) echo -e ":: 请选择要回滚恢复的快照序号 (或按 Ctrl+C 取消): " ;;
            rollback_invalid_num) echo -e "\e[1;31m[-] 无效的序号，取消回滚操作。\e[0m" ;;
            rolling_back) echo -e "\n\e[1;34m:: 正在从快照 [$p1] 恢复配置...\e[0m" ;;
            pre_rollback_backup) echo -e "\e[1;30m[安全防护] 回滚前已自动为当前配置创建安全快照: $p1\e[0m" ;;
            rollback_done) echo -e "\e[1;32m[+] 配置回滚成功！已恢复至快照: $p1\e[0m" ;;
            snapshot_note_prompt) echo -e ":: 请输入快照备注 (直接回车跳过): " ;;

            # Dependency Menu
            dep_menu_title) echo -e "\n\e[1;33m:: 请选择要安装的依赖（输入数字切换，直接回车开始安装）：\e[0m" ;;
            dep_menu_hint) echo -e "输入空格分隔的序列号（如 1 3 5）来勾选/取消，直接回车开始安装选中包：" ;;
            installing_selected) echo -e "\n\e[1;34m:: 正在通过包管理器安装选中的依赖...\e[0m" ;;

            # Deployment & Backup
            backing_up) echo -e "\n\e[1;34m:: 正在创建配置快照...\e[0m" ;;
            backup_done) echo -e "\e[1;32m[+] 快照创建成功！保存路径: $p1\e[0m" ;;
            copying_configs) echo -e "\n\e[1;34m:: 正在部署 dotfiles 配置文件...\e[0m" ;;
            copy_done) echo -e "\e[1;32m[+] 配置文件部署与复制成功！\e[0m" ;;

            # System Doctor
            running_doctor) echo -e "\n\e[1;35m:: 正在运行 System Doctor 进行系统诊断...\e[0m" ;;
            doctor_ok) echo -e "\e[1;32m[  OK  ]\e[0m $p1" ;;
            doctor_warn) echo -e "\e[1;33m[ WARN ]\e[0m $p1" ;;
            doctor_err) echo -e "\e[1;31m[ FAIL ]\e[0m $p1" ;;
            all_done) echo -e "\n\e[1;32m[+] 所有的部署和诊断检查已全部完成！\e[0m" ;;
            reboot_hint) echo -e "\e[1;36m提示: 建议重启 Noctalia 或重新加载 Niri 使得所有新配置完全生效。\e[0m" ;;

            # Standalone & Update Strings
            git_required) echo -e "\e[1;31m[-] 错误: 需要安装 git 才能下载或更新配置仓库。\e[0m" ;;
            cloning_repo) echo -e "\n\e[1;34m:: 检测到独立运行模式。正在克隆 NyxNiri 仓库到缓存目录 ($CACHE_DIR)... \e[0m" ;;
            checking_updates) echo -e "\n\e[1;34m:: 正在检查配置仓库及脚本更新...\e[0m" ;;
            updating_done) echo -e "\e[1;32m[+] 更新与重载成功！正在重新启动脚本...\e[0m" ;;
            updating_failed) echo -e "\e[1;31m[-] 更新失败，请检查您的网络连接或 Git 仓库状态。\e[0m" ;;
            mirror_fallback_confirm) echo -e "\e[1;33m[!] 连接 github.com 失败，是否切换到国内镜像 (gh-proxy) 继续克隆? [Y/n] \e[0m" ;;
            mirror_declined) echo -e "\e[1;31m[-] 已取消克隆（拒绝使用非官方镜像）。\e[0m" ;;
            dirty_tree_warn) echo -e "\e[1;33m[!] 检测到 $p1 中存在未提交的本地改动，继续更新将丢弃这些改动。\e[0m" ;;
            dirty_tree_confirm) echo -e ":: 是否继续并丢弃本地改动? [y/N] " ;;
            update_cancelled_dirty) echo -e "\e[1;34m已取消更新，本地改动已保留。\e[0m" ;;
            syntax_check_failed) echo -e "\e[1;31m[-] 下载的新版本脚本语法校验失败，可能下载不完整，已中止自更新。\e[0m\n请手动检查: $p1" ;;

            # AUR & mpvpaper
            aur_skip) echo -e "\e[1;33m[!] AUR 包 ($p1) 需要 AUR helper (paru/yay)，跳过安装。\e[0m" ;;
            aur_helper_required) echo -e "\e[1;33m    请先安装 paru 或 yay，然后重新运行依赖安装。\e[0m" ;;
            checking_mpvpaper) echo -e "\n\e[1;34m:: 检查 mpvpaper 版本...\e[0m" ;;
            mpvpaper_version_ok) echo -e "\e[1;32m[  OK  ]\e[0m mpvpaper $p1 >= 1.9，无已知内存泄漏问题。" ;;
            mpvpaper_leak_warn) echo -e "\e[1;31m[ WARN ]\e[0m mpvpaper $p1 在默认硬件解码配置下存在已知 OpenGL 内存泄漏，建议升级至 1.9+ 或安装 mpvpaper-git！\n   (参见: https://github.com/GhostNaN/mpvpaper/issues/127)" ;;
            mpvpaper_upgrade_prompt) echo -e ":: 是否安装 mpvpaper-git（AUR）替代当前 mpvpaper $p1 以修复泄漏？[y/N]: " ;;
            mpvpaper_upgrade_done) echo -e "\e[1;32m[+] mpvpaper-git 安装完成，内存泄漏问题已修复。\e[0m" ;;
            mpvpaper_upgrade_skip) echo -e "如需手动升级，请运行: paru -S mpvpaper-git 或 yay -S mpvpaper-git" ;;

            # Alerts / Prompts
            warn_deps_missing) echo -e "\n\e[1;33m[!] 警告: 检测到你缺少一些运行所需的依赖组件！\e[0m" ;;
            ask_install_now) echo -e ":: 是否现在检查并进入依赖安装菜单？[Y/n]: " ;;
            ask_backup_again) echo -e ":: 检测到今天已备份过配置，是否重新备份？[y/N]: " ;;
            ask_backup_before_deploy) echo -e ":: 是否在部署前备份当前配置？[y/N] (默认直接部署不备份): " ;;
            ask_keep_monitor) echo -e "\n\e[1;36m:: 检测到已存在显示配置 ~/.config/niri/monitor.kdl (包含针对您个人硬件的配置)。\e[0m\n:: 是否保留您当前的显示器配置？[Y/n]: " ;;
            ask_keep_wallpapers) echo -e "\n\e[1;36m:: 检测到已存在壁纸目录。\e[0m\n:: 是否保留您当前的壁纸？（选择\"否\"将替换为 NyxNiri 默认壁纸）[Y/n]: " ;;
        esac
    else
        case "$key" in
            welcome) echo -e "\e[1;36m:: Welcome to $PROJECT_NAME Dotfiles Toolbox\e[0m" ;;
            lang_select) echo -e "Select Language / 请选择语言:" ;;
            checking_dep) echo -e "\n\e[1;34m:: Checking system dependencies...\e[0m" ;;
            installed) echo -e "\e[1;32m[Installed]\e[0m" ;;
            missing) echo -e "\e[1;31m[Missing]\e[0m" ;;

            # Main Menu
            menu_title) echo -e "\n\e[1;35m=== $PROJECT_NAME Control Panel & Toolbox ===\e[0m" ;;
            menu_group_deploy) echo -e "  \e[1;36m[ Deployment & Setup ]\e[0m" ;;
            menu_opt1) echo -e "  \e[1;32m1)\e[0m Full Setup (Install Dependencies + Deploy Configs)" ;;
            menu_opt2) echo -e "  \e[1;32m2)\e[0m Check & Install Dependencies Only" ;;
            menu_opt3) echo -e "  \e[1;32m3)\e[0m Deploy Configurations Only" ;;

            menu_group_backup) echo -e "\n  \e[1;36m[ Snapshots & Recovery ]\e[0m" ;;
            menu_opt4) echo -e "  \e[1;32m4)\e[0m Snapshot Configurations" ;;
            menu_opt5) echo -e "  \e[1;32m5)\e[0m Rollback Configurations" ;;

            menu_group_maint) echo -e "\n  \e[1;36m[ Maintenance & Diagnostics ]\e[0m" ;;
            menu_opt6) echo -e "  \e[1;32m6)\e[0m Update Repo & Optional Overwrite" ;;
            menu_opt7) echo -e "  \e[1;32m7)\e[0m Run System Doctor Diagnostics" ;;
            menu_opt8) echo -e "  \e[1;32m8)\e[0m Generate Bug Report" ;;

            menu_group_system) echo -e "\n  \e[1;36m[ System Management ]\e[0m" ;;
            menu_opt9) echo -e "  \e[1;31m9)\e[0m Uninstall NyxNiri" ;;
            menu_opt0) echo -e "  \e[1;30m0)\e[0m Exit" ;;

            menu_prompt) echo -e ":: Please select an option [0-9]: " ;;
            invalid_opt) echo -e "\e[1;31m[-] Invalid option, please try again.\e[0m" ;;
            press_any_key) echo -e "\nPress any key to return to main menu..." ;;
            generating_report) echo -e "\n\e[1;34m:: Collecting system diagnostic data and generating Bug Report...\e[0m" ;;
            report_done) echo -e "\e[1;32m[+] Bug Report successfully exported to:\e[0m $p1\n\e[1;36mHint: Please attach this file when opening a GitHub Issue!\nQQ Group: 631425889 | Developer QQ: 2040244628 | Telegram: @Echoes678\e[0m" ;;

            # Optional Overwrite Upgrade Strings
            overwrite_title) echo -e "\n\e[1;35m────────────────────────────────────────────────────────────────\e[0m\n \e[1;36m:: NyxNiri Config Overwrite Upgrade\e[0m\n\e[1;35m────────────────────────────────────────────────────────────────\e[0m" ;;
            overwrite_opt1) echo -e "  \e[1;32m1)\e[0m Direct Overwrite (Skip backup, deploy latest configs immediately)" ;;
            overwrite_opt2) echo -e "  \e[1;36m2)\e[0m Safe Overwrite (Create auto snapshot before deploying)" ;;
            overwrite_opt3) echo -e "  \e[1;33m3)\e[0m Selective Overwrite (Choose specific components to update)" ;;
            overwrite_opt4) echo -e "  \e[1;30m4)\e[0m Skip Config Overwrite (Keep current ~/.config untouched)" ;;
            overwrite_prompt) echo -e ":: Select overwrite mode [1-4] (default 1): " ;;
            selective_title) echo -e "\n\e[1;33m:: Select components to overwrite (type numbers to toggle, press Enter to confirm):\e[0m" ;;
            selective_hint) echo -e "Type space-separated numbers (e.g. 1 3) to toggle, then press Enter to upgrade:" ;;
            upgrading_selected) echo -e "\n\e[1;34m:: Overwrite upgrading selected components...\e[0m" ;;
            overwrite_done) echo -e "\e[1;32m[+] Selected configurations overwritten and upgraded successfully!\e[0m" ;;

            # Uninstall Strings
            uninstall_title) echo -e "\n\e[1;31m────────────────────────────────────────────────────────────────\e[0m\n \e[1;31m:: NyxNiri Uninstall & Environment Restoration Tool\e[0m\n\e[1;31m────────────────────────────────────────────────────────────────\e[0m" ;;
            uninstall_opt1) echo -e "  \e[1;32m1)\e[0m Standard Safe Uninstall (Archive current configs, remove CLI)" ;;
            uninstall_opt2) echo -e "  \e[1;36m2)\e[0m Restore to Original State (Restore earliest pre-install backup)" ;;
            uninstall_opt3) echo -e "  \e[1;31m3)\e[0m Purge Everything (Remove all configs, snapshots, cache & wallpapers)" ;;
            uninstall_opt4) echo -e "  \e[1;30m4)\e[0m Cancel & Return" ;;
            uninstall_prompt) echo -e ":: Select uninstall mode [1-4]: " ;;
            uninstall_archived) echo -e "\e[1;32m[+] Archived current configs to:\e[0m $p1" ;;
            uninstall_done) echo -e "\e[1;32m[+] NyxNiri uninstalled successfully! Thank you for using.\e[0m" ;;
            purge_done) echo -e "\e[1;32m[+] Deep purge complete. All NyxNiri configs and caches purged.\e[0m" ;;
            restore_origin_done) echo -e "\e[1;32m[+] Successfully restored your system to its original pre-install state!\e[0m" ;;

            # Rollback Strings
            no_backups_found) echo -e "\e[1;33m[!] No configuration snapshots found!\e[0m" ;;
            available_backups) echo -e "\n\e[1;36m:: Available NyxNiri Snapshots\e[0m" ;;
            select_rollback_target) echo -e ":: Select snapshot number to restore (or press Ctrl+C to cancel): " ;;
            rollback_invalid_num) echo -e "\e[1;31m[-] Invalid selection, rollback cancelled.\e[0m" ;;
            rolling_back) echo -e "\n\e[1;34m:: Restoring configuration from snapshot [$p1]...\e[0m" ;;
            pre_rollback_backup) echo -e "\e[1;30m[Safety] Auto-saved pre-rollback snapshot of current configs: $p1\e[0m" ;;
            rollback_done) echo -e "\e[1;32m[+] Rollback complete! Restored to snapshot: $p1\e[0m" ;;
            snapshot_note_prompt) echo -e ":: Enter snapshot note (press Enter to skip): " ;;

            # Dependency Menu
            dep_menu_title) echo -e "\n\e[1;33m:: Select dependencies to install (type numbers to toggle, press Enter to confirm):\e[0m" ;;
            dep_menu_hint) echo -e "Type space-separated numbers (e.g. 1 3 5) to toggle, then press Enter to install:" ;;
            copy_done) echo -e "\e[1;32mConfigurations deployed and copied successfully!\e[0m" ;;

            # System Doctor
            running_doctor) echo -e "\n\e[1;35mRunning System Doctor for diagnostics...\e[0m" ;;
            doctor_ok) echo -e "\e[1;32m[  OK  ]\e[0m $p1" ;;
            doctor_warn) echo -e "\e[1;33m[ WARN ]\e[0m $p1" ;;
            doctor_err) echo -e "\e[1;31m[ FAIL ]\e[0m $p1" ;;
            all_done) echo -e "\n\e[1;32m[+] All deployment and diagnostics completed successfully!\e[0m" ;;
            reboot_hint) echo -e "\e[1;36mHint: It is recommended to restart Noctalia or reload Niri for all settings to take effect.\e[0m" ;;

            # Standalone & Update Strings
            git_required) echo -e "\e[1;31m[-] Error: git is required to download or update the repository.\e[0m" ;;
            cloning_repo) echo -e "\n\e[1;34m:: Standalone mode detected. Cloning NyxNiri repository to cache ($CACHE_DIR)... \e[0m" ;;
            checking_updates) echo -e "\n\e[1;34m:: Checking for repository and script updates...\e[0m" ;;
            updating_done) echo -e "\e[1;32m[+] Update and reload successful! Restarting script...\e[0m" ;;
            updating_failed) echo -e "\e[1;31m[-] Update failed. Please check your network connection or git status.\e[0m" ;;
            mirror_fallback_confirm) echo -e "\e[1;33m[!] Connection to github.com failed. Switch to the domestic mirror (gh-proxy) and continue cloning? [Y/n] \e[0m" ;;
            mirror_declined) echo -e "\e[1;31m[-] Clone cancelled (declined the unofficial mirror).\e[0m" ;;
            dirty_tree_warn) echo -e "\e[1;33m[!] Uncommitted local changes detected in $p1; continuing will discard them.\e[0m" ;;
            dirty_tree_confirm) echo -e ":: Continue and discard local changes? [y/N] " ;;
            update_cancelled_dirty) echo -e "\e[1;34mUpdate cancelled; local changes preserved.\e[0m" ;;
            syntax_check_failed) echo -e "\e[1;31m[-] Syntax check failed on the downloaded script; the download may be incomplete. Self-update aborted.\e[0m\nPlease check manually: $p1" ;;

            # AUR & mpvpaper
            aur_skip) echo -e "\e[1;33m[!] AUR packages ($p1) require an AUR helper (paru/yay). Skipping.\e[0m" ;;
            aur_helper_required) echo -e "\e[1;33m    Install paru or yay first, then re-run dependency installation.\e[0m" ;;
            checking_mpvpaper) echo -e "\n\e[1;34m:: Checking mpvpaper version...\e[0m" ;;
            mpvpaper_version_ok) echo -e "\e[1;32m[  OK  ]\e[0m mpvpaper $p1 >= 1.9, no known memory leak." ;;
            mpvpaper_leak_warn) echo -e "\e[1;31m[ WARN ]\e[0m mpvpaper $p1 has a known OpenGL memory leak with hwdec enabled. Upgrade to 1.9+ or install mpvpaper-git!\n   (See: https://github.com/GhostNaN/mpvpaper/issues/127)" ;;
            mpvpaper_upgrade_prompt) echo -e ":: Install mpvpaper-git (AUR) to replace mpvpaper $p1 and fix the leak? [y/N]: " ;;
            mpvpaper_upgrade_done) echo -e "\e[1;32m[+] mpvpaper-git installed, memory leak fixed.\e[0m" ;;
            mpvpaper_upgrade_skip) echo -e "To manually upgrade, run: paru -S mpvpaper-git or yay -S mpvpaper-git" ;;

            # Alerts / Prompts
            warn_deps_missing) echo -e "\n\e[1;33m[!] Warning: Some required dependencies are missing on your system!\e[0m" ;;
            ask_install_now) echo -e ":: Would you like to check and install missing dependencies now? [Y/n]: " ;;
            ask_backup_again) echo -e ":: A backup has already been made today. Do you want to back up again? [y/N]: " ;;
            ask_backup_before_deploy) echo -e ":: Do you want to back up current configs before deploying? [y/N] (Default direct deploy without backup): " ;;
            ask_keep_monitor) echo -e "\n\e[1;36m:: Existing monitor config ~/.config/niri/monitor.kdl detected (contains resolution/layout settings specific to your personal hardware).\e[0m\n:: Preserve your current monitor settings? [Y/n]: " ;;
            ask_keep_wallpapers) echo -e "\n\e[1;36m:: Existing wallpaper directory detected.\e[0m\n:: Keep your current wallpapers? (Choosing \"No\" will replace with NyxNiri defaults) [Y/n]: " ;;
        esac
    fi
}

select_language() {
    clear 2>/dev/null || true
    show_logo
    echo ""
    echo "  1) English"
    echo "  2) 简体中文 (Simplified Chinese)"
    echo ""
    local lang_choice=""
    if [ -t 0 ] && [ -c /dev/tty ]; then
        read -p "Select Language / 请选择语言 [1/2]: " lang_choice < /dev/tty || lang_choice="2"
    fi
    if [ "$lang_choice" = "1" ]; then
        LANG_MODE="en"
    else
        LANG_MODE="zh"
    fi
}
