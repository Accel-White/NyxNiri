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

# Pad a string to a target display width, counting wide (CJK) characters as
# two columns so mixed zh/en labels right-align cleanly in menus.
_disp_pad() {
    local s="$1" width="${2:-20}"
    local len=0 i c cp
    for ((i = 0; i < ${#s}; i++)); do
        c="${s:i:1}"
        cp=$(printf '%d' "'$c")
        if [ "$cp" -ge $((0x4e00)) ] && [ "$cp" -le $((0x9fff)) ]; then
            len=$((len + 2))
        else
            len=$((len + 1))
        fi
    done
    local pad=$((width - len))
    [ "$pad" -lt 0 ] && pad=0
    printf '%s%*s' "$s" "$pad" ""
}

msg() {
    local key="$1"
    shift || true
    local p1="${1:-}"
    local p2="${2:-}"

    if [ "${LANG_MODE:-en}" = "zh" ]; then
        case "$key" in
            lang_select) echo -e "\n\e[1;36m:: 请选择语言 / Select Language:\e[0m" ;;
            installed) echo -e "\e[1;32m[已安装]\e[0m" ;;
            missing) echo -e "\e[1;31m[未安装]\e[0m" ;;

            # Main Menu
            menu_title) echo -e "\n\e[1;35m=== $PROJECT_NAME 控制面板 ===\e[0m" ;;
            menu_group_deploy) echo -e "  \e[1;36m[ 部署与安装 ]\e[0m" ;;
            menu_opt1) echo -e "  \e[1;32m1)\e[0m 快速部署 (自动)" ;;
            menu_opt2) echo -e "  \e[1;32m2)\e[0m 自定义部署" ;;
            menu_opt3) echo -e "  \e[1;32m3)\e[0m 检查与安装依赖" ;;

            menu_group_backup) echo -e "\n  \e[1;36m[ 快照与恢复 ]\e[0m" ;;
            menu_opt4) echo -e "  \e[1;32m4)\e[0m 快照管理" ;;

            menu_group_maint) echo -e "\n  \e[1;36m[ 运维与诊断 ]\e[0m" ;;
            menu_opt5) echo -e "  \e[1;32m5)\e[0m 检查更新与配置覆盖" ;;
            menu_opt6) echo -e "  \e[1;32m6)\e[0m 系统诊断" ;;
            menu_opt7) echo -e "  \e[1;32m7)\e[0m 导出诊断报告 (Bug Report)" ;;

            menu_group_system) echo -e "\n  \e[1;36m[ 系统管理 ]\e[0m" ;;
            menu_opt8) echo -e "  \e[1;31m8)\e[0m 卸载与环境复原" ;;
            menu_opt9) echo -e "  \e[1;32m9)\e[0m 可选模块 (Greeter / fcitx5 / 深度清理)" ;;
            menu_opt0) echo -e "  \e[1;30m0)\e[0m 退出" ;;

            # Snapshot Management Submenu
            snapshot_menu_title) echo -e "\n\e[1;35m=== 快照管理 ===\e[0m" ;;
            snapshot_sub_create) echo -e "  \e[1;32m1)\e[0m 创建快照" ;;
            snapshot_sub_list) echo -e "  \e[1;32m2)\e[0m 查看快照列表" ;;
            snapshot_sub_delete) echo -e "  \e[1;31m3)\e[0m 删除快照" ;;
            snapshot_sub_rollback) echo -e "  \e[1;32m4)\e[0m 回滚快照" ;;
            snapshot_sub_back) echo -e "  \e[1;30m0)\e[0m 返回主菜单" ;;

            # Optional Modules Submenu
            optmod_menu_title) echo -e "\n\e[1;35m=== 可选模块 ===\e[0m" ;;
            optmod_purge) echo -e "  \e[1;31m4)\e[0m 深度清理 (配置 / 快照 / 缓存 / 壁纸)" ;;
            optmod_back) echo -e "  \e[1;30m0)\e[0m 返回主菜单" ;;

            # Greeter Submenu
            greeter_menu_title) echo -e "\n\e[1;35m=== Noctalia Greeter ===\e[0m" ;;
            greeter_sub_install) echo -e "  \e[1;32m1)\e[0m 安装与配置" ;;
            greeter_sub_status) echo -e "  \e[1;32m2)\e[0m 查看状态" ;;
            greeter_sub_uninstall) echo -e "  \e[1;31m3)\e[0m 卸载配置" ;;
            greeter_sub_back) echo -e "  \e[1;30m0)\e[0m 返回" ;;

            # Fcitx Submenu
            fcitx_menu_title) echo -e "\n\e[1;35m=== NyxMellow fcitx5 皮肤 ===\e[0m" ;;
            fcitx_sub_install) echo -e "  \e[1;32m1)\e[0m 安装皮肤" ;;
            fcitx_sub_status) echo -e "  \e[1;32m2)\e[0m 查看状态" ;;
            fcitx_sub_uninstall) echo -e "  \e[1;31m3)\e[0m 卸载皮肤" ;;
            fcitx_sub_back) echo -e "  \e[1;30m0)\e[0m 返回" ;;

            # Module Status Labels
            status_installed_enabled) echo -e "\e[1;32m[已安装+已启用]\e[0m" ;;
            status_installed) echo -e "\e[1;33m[已安装]\e[0m" ;;
            status_not_installed) echo -e "\e[1;31m[未安装]\e[0m" ;;
            status_enabled) echo -e "\e[1;32m[已启用]\e[0m" ;;
            status_disabled) echo -e "\e[1;33m[未启用]\e[0m" ;;
            status_fcitx5_missing) echo -e "\e[1;31m[fcitx5 未安装]\e[0m" ;;
            status_wallpapers_installed) echo -e "\e[1;32m[已下载]\e[0m" ;;
            status_wallpapers_missing) echo -e "\e[1;33m[未下载]\e[0m" ;;

            # Optional Modules Menu Labels & Wallpapers (External Pack)
            optmod_sub_fcitx) echo -e "NyxMellow fcitx5 皮肤" ;;
            optmod_sub_wallpapers) echo -e "下载壁纸包 (~100MB)" ;;
            msg_downloading_wallpapers) echo -e "\n\e[1;34m:: 从外部仓库拉取壁纸包…\e[0m" ;;
            msg_downloading_wallpapers_node) echo -e "  [$p1] 从 [$p2] 节点拉取壁纸仓库…" ;;
            msg_wallpapers_download_success) echo -e "\e[1;32m[+] 壁纸包部署完成\e[0m" ;;
            msg_wallpapers_download_failed) echo -e "\e[1;31m[-] 壁纸包下载失败，跳过\e[0m" ;;

            # Install Flow
            fcitx_skipped_not_installed) echo -e "\e[1;33m  [跳过]\e[0m 未检测到 fcitx5，跳过 NyxMellow 皮肤 (安装 fcitx5 后可用: nyxniri fcitx install)" ;;
            install_cancelled) echo -e "\e[1;34m已取消安装\e[0m" ;;
            install_step_configs) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 部署配置…\e[0m" ;;
            install_step_wallpapers) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 同步壁纸…\e[0m" ;;
            install_step_deps) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 检查与安装依赖…\e[0m" ;;
            install_step_fcitx) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 配置 fcitx5 皮肤…\e[0m" ;;
            install_step_greeter) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 配置 Noctalia Greeter…\e[0m" ;;
            install_summary_title) echo -e "\n\e[1;35m=== 安装汇总 ===\e[0m" ;;
            summary_configs) echo -e "  \e[1;32m✓\e[0m 配置文件: 已部署" ;;
            summary_wallpapers) echo -e "  \e[1;32m✓\e[0m 壁纸: 已同步" ;;
            summary_wallpapers_pack) echo -e "  \e[1;32m✓\e[0m 壁纸: 已同步 (含动态视频)" ;;
            summary_deps_ok) echo -e "  \e[1;32m✓\e[0m 依赖: 已就绪" ;;
            summary_deps_skip) echo -e "  \e[1;33m·\e[0m 依赖: 已跳过 (稍后运行: nyxniri deps)" ;;
            summary_fcitx_on) echo -e "  \e[1;32m✓\e[0m NyxMellow fcitx5 皮肤: 已应用" ;;
            summary_fcitx_off) echo -e "  \e[1;33m·\e[0m NyxMellow fcitx5 皮肤: 已跳过" ;;
            summary_greeter_on) echo -e "  \e[1;32m✓\e[0m Noctalia Greeter: 已配置" ;;
            summary_greeter_off) echo -e "  \e[1;33m·\e[0m Noctalia Greeter: 已跳过" ;;

            # Test Deploy
            test_start) echo -e "\n\e[1;34m:: [test] 幂等重放配置 (不备份 / 保留 monitor.kdl / 跳过可选模块与依赖)…\e[0m" ;;
            test_done) echo -e "\n\e[1;32m[+] 测试部署完成\e[0m" ;;

            menu_prompt) echo -e ":: 请选择操作 [0-9]: " ;;
            invalid_opt) echo -e "\e[1;31m[-] 无效选项，请重新选择\e[0m" ;;
            press_any_key) echo -e "\n按任意键继续…" ;;
            generating_report) echo -e "\n\e[1;34m:: 正在收集诊断数据并导出报告…\e[0m" ;;
            report_done) echo -e "\e[1;32m[+] 诊断报告已导出至:\e[0m $p1\n\e[1;36m提示: 提交 Issue 请附带此文件\nQQ 群: 631425889 | 开发者 QQ: 2040244628 | Telegram: @Echoes678\e[0m" ;;

            # Optional Overwrite Upgrade Strings
            overwrite_title) echo -e "\n\e[1;35m────────────────────────────────────────────────────────────────\e[0m\n \e[1;36m:: NyxNiri 配置覆盖升级\e[0m\n\e[1;35m────────────────────────────────────────────────────────────────\e[0m" ;;
            overwrite_opt1) echo -e "  \e[1;32m1)\e[0m 自动覆盖升级 (自动备份)" ;;
            overwrite_opt2) echo -e "  \e[1;36m2)\e[0m 自定义覆盖" ;;
            overwrite_opt3) echo -e "  \e[1;33m3)\e[0m 查看配置差异 (Diff)" ;;
            overwrite_opt4) echo -e "  \e[1;30m4)\e[0m 仅更新脚本" ;;
            overwrite_prompt) echo -e ":: 请选择覆盖模式 [1-4] (默认 1): " ;;
            selective_title) echo -e "\n\e[1;33m:: 请选择要覆盖升级的组件 (按数字切换，回车开始)：\e[0m" ;;
            selective_hint) echo -e "输入空格分隔的序号切换 (如 1 3)，回车开始：" ;;
            upgrading_selected) echo -e "\n\e[1;34m:: 正在部署选中组件…\e[0m" ;;
            overwrite_done) echo -e "\e[1;32m[+] 选中组件已部署\e[0m" ;;
            
            # Master Component Menu
            master_menu_title) echo -e "\n\e[1;33m:: 请确认部署清单 (按数字切换状态，回车开始)：\e[0m" ;;
            master_item_config) echo -e "核心配置: $p1" ;;
            master_item_module) echo -e "可选模块: $p1" ;;
            master_item_asset) echo -e "重型资源: $p1" ;;
            master_item_behavior) echo -e "--- 部署行为 ---" ;;
            master_item_backup) echo -e "部署前自动创建快照 (Backup)" ;;
            master_item_monitor) echo -e "保留硬件显示器配置 (Keep monitor.kdl)" ;;
            diff_viewer_title) echo -e "\n\e[1;36m:: 配置差异对比 (按 q 退出)\e[0m" ;;

            # Uninstall Strings
            uninstall_title) echo -e "\n\e[1;31m────────────────────────────────────────────────────────────────\e[0m\n \e[1;31m:: NyxNiri 卸载与环境复原\e[0m\n\e[1;31m────────────────────────────────────────────────────────────────\e[0m" ;;
            uninstall_opt1) echo -e "  \e[1;32m1)\e[0m 标准卸载 (归档当前配置并移除文件与 CLI)" ;;
            uninstall_opt2) echo -e "  \e[1;36m2)\e[0m 环境复原 (恢复至初始备份)" ;;
            uninstall_opt3) echo -e "  \e[1;31m3)\e[0m 深度清理 (清除所有配置、快照、缓存与壁纸)" ;;
            uninstall_opt4) echo -e "  \e[1;30m4)\e[0m 取消返回" ;;
            uninstall_prompt) echo -e ":: 请选择卸载模式 [1-4]: " ;;
            uninstall_archived) echo -e "\e[1;32m[+] 当前配置已归档至:\e[0m $p1" ;;
            uninstall_done) echo -e "\e[1;32m[+] NyxNiri 卸载完成\e[0m" ;;
            purge_done) echo -e "\e[1;32m[+] 深度清理完成\e[0m" ;;
            restore_origin_done) echo -e "\e[1;32m[+] 已恢复至初始环境\e[0m" ;;

            # Rollback Strings
            no_backups_found) echo -e "\e[1;33m[!] 未找到可用快照\e[0m" ;;
            available_backups) echo -e "\n\e[1;36m:: 可用快照列表\e[0m" ;;
            select_rollback_target) echo -e ":: 请选择要恢复的快照序号 (Ctrl+C 取消): " ;;
            rollback_invalid_num) echo -e "\e[1;31m[-] 无效序号，已取消回滚\e[0m" ;;
            rolling_back) echo -e "\n\e[1;34m:: 正在从快照 [$p1] 恢复配置…\e[0m" ;;
            pre_rollback_backup) echo -e "\e[1;30m[安全防护] 回滚前已自动为当前配置创建快照: $p1\e[0m" ;;
            rollback_done) echo -e "\e[1;32m[+] 已恢复至快照: $p1\e[0m" ;;
            snapshot_note_prompt) echo -e ":: 请输入快照备注 (直接回车跳过): " ;;

            # Snapshot Delete Strings
            delete_confirm) echo -e "\n\e[1;31m[!] 将删除快照: $p1\e[0m" ;;
            delete_prompt) echo -e ":: 确认删除该快照？[y/N]: " ;;
            delete_cancelled) echo -e "\e[1;34m已取消删除\e[0m" ;;
            delete_done) echo -e "\e[1;32m[+] 已删除快照 [$p1]，剩余 $p2 个\e[0m" ;;
            delete_invalid_num) echo -e "\e[1;31m[-] 无效序号，已取消删除\e[0m" ;;

            # Dependency Menu
            dep_menu_title) echo -e "\n\e[1;33m:: 请选择要安装的依赖 (按数字切换，回车开始安装)：\e[0m" ;;
            dep_menu_hint) echo -e "按数字切换，或热键 [\e[1;32ma\e[0m]全选 [\e[1;32mn\e[0m]全取消 [\e[1;32mi\e[0m/回车]开始安装: " ;;
            installing_selected) echo -e "\n\e[1;34m:: 正在安装选中依赖…\e[0m" ;;

            # Optional Greeter Module
            greeter_install_title) echo -e "\n\e[1;35m[ 可选模块 ] Noctalia Greeter 安装与配置\e[0m" ;;
            greeter_install_pkgs) echo -e "\n\e[1;34m:: 正在安装 greetd 与 noctalia-greeter…\e[0m" ;;
            greeter_aur_required) echo -e "\e[1;33m[!] noctalia-greeter (AUR) 需要 paru 或 yay。请先安装 AUR helper。\e[0m" ;;
            greeter_pkg_failed) echo -e "\e[1;31m[!] 软件包 $p1 安装失败，继续后续步骤…\e[0m" ;;
            greeter_install_failed) echo -e "\e[1;31m[!] noctalia-greeter 安装失败。稍后运行 nyxniri greeter install 重试。\e[0m" ;;
            greeter_dm_conflict) echo -e "\e[1;33m[!] 检测到其他显示管理器: $p1。须手动禁用 (如 sudo systemctl disable $p1)。\e[0m" ;;
            greeter_config_skip) echo -e "\e[1;32m[+] greetd 已配置为使用 noctalia-greeter，跳过\e[0m" ;;
            greeter_config_written) echo -e "\e[1;32m[+] 已写入 greetd 配置: $p1 (原配置已备份)\e[0m" ;;
            greeter_config_failed) echo -e "\e[1;31m[!] 写入 greetd 配置失败: $p1 (需要 sudo 权限)\e[0m" ;;
            greeter_state_dir_created) echo -e "\e[1;32m[+] 已创建状态目录 /var/lib/noctalia-greeter\e[0m" ;;
            greeter_cmd_failed) echo -e "\e[1;31m[!] 特权命令执行失败: $p1 (需要 sudo 权限)\e[0m" ;;
            greeter_polkit_skip) echo -e "\e[1;32m[+] polkit 规则已存在，跳过\e[0m" ;;
            greeter_polkit_written) echo -e "\e[1;32m[+] 已写入 polkit 免密规则: $p1\e[0m" ;;
            greeter_polkit_failed) echo -e "\e[1;31m[!] 写入 polkit 规则失败\e[0m" ;;
            greeter_enabled) echo -e "\e[1;32m[+] 已启用 greetd 服务 (重启生效)\e[0m" ;;
            greeter_enabled_skip) echo -e "\e[1;32m[+] greetd 服务已启用\e[0m" ;;
            greeter_enable_failed) echo -e "\e[1;31m[!] 启用 greetd 服务失败。请手动运行: sudo systemctl enable greetd\e[0m" ;;
            greeter_reboot_hint) echo -e "\e[1;36m提示: 重启后登录界面生效。主题同步路径: Noctalia 设置 → 安全 → Noctalia Greeter → Sync Now\e[0m" ;;
            greeter_status_title) echo -e "\n\e[1;36m:: Noctalia Greeter 状态检查\e[0m" ;;
            greeter_status_ok) echo -e "\e[1;32m[+] Greeter 已就绪\e[0m" ;;
            greeter_status_hint) echo -e "\e[1;36m提示: 运行 nyxniri greeter install 完成配置\e[0m" ;;
            greeter_uninstall_title) echo -e "\n\e[1;33m:: Noctalia Greeter 卸载 (保留软件包)\e[0m" ;;
            greeter_uninstall_restored) echo -e "\e[1;32m[+] 已还原 greetd 配置: $p1\e[0m" ;;
            greeter_uninstall_nobackup) echo -e "\e[1;33m[!] 未找到 greetd 配置备份，保留当前配置\e[0m" ;;
            greeter_uninstall_polkit) echo -e "\e[1;32m[+] 已移除 polkit 免密规则\e[0m" ;;
            greeter_uninstall_done) echo -e "\e[1;32m[+] Greeter 卸载完成。若需移除软件包: paru -R noctalia-greeter greetd\e[0m" ;;

            # Optional Fcitx5 Dynamic Theme Module
            fcitx_install_title) echo -e "\n\e[1;35m[ 可选模块 ] NyxMellow 动态 fcitx5 皮肤配置\e[0m" ;;
            fcitx_skip_no_fcitx5) echo -e "\e[1;33m[!] 未检测到 fcitx5，跳过皮肤激活 (模板已部署；安装 fcitx5 后运行 nyxniri fcitx install 启用)。\e[0m" ;;
            fcitx_templates_deployed) echo -e "\e[1;32m[+] 主题模板已部署: ~/.local/share/fcitx5/themes/nyxmellow/templates/\e[0m" ;;
            fcitx_render_ok) echo -e "\e[1;32m[+] Noctalia 已按当前主题渲染 nyxmellow 皮肤\e[0m" ;;
            fcitx_render_pending) echo -e "\e[1;33m[!] noctalia 未运行，模板将在下次主题切换时生效 (可手动运行 nyxniri fcitx install)。\e[0m" ;;
            fcitx_theme_set) echo -e "\e[1;32m[+] fcitx5 已切换主题: nyxmellow ($p1)\e[0m" ;;
            fcitx_restarted) echo -e "\e[1;32m[+] fcitx5 已重启以加载新皮肤\e[0m" ;;
            fcitx_status_title) echo -e "\n\e[1;36m:: NyxMellow 动态 fcitx5 皮肤状态\e[0m" ;;
            fcitx_uninstall_title) echo -e "\n\e[1;33m:: NyxMellow 动态 fcitx5 皮肤卸载\e[0m" ;;
            fcitx_uninstall_done) echo -e "\e[1;32m[+] NyxMellow 皮肤已卸载，fcitx5 主题已还原\e[0m" ;;
            fcitx_registered) echo -e "\e[1;32m[+] Noctalia 模板已注册 ($p1)\e[0m" ;;
            fcitx_not_registered) echo -e "\e[1;33m[!] Noctalia 模板未注册 ($p1)\e[0m" ;;

            # Deployment & Backup
            backing_up) echo -e "\n\e[1;34m:: 正在创建配置快照…\e[0m" ;;
            backup_done) echo -e "\e[1;32m[+] 快照创建成功: $p1\e[0m" ;;
            copying_configs) echo -e "\n\e[1;34m:: 正在部署配置文件…\e[0m" ;;
            copy_done) echo -e "\e[1;32m[+] 配置文件部署完成\e[0m" ;;

            # System Doctor
            running_doctor) echo -e "\n\e[1;35m:: 正在运行 System Doctor 进行系统诊断…\e[0m" ;;
            doctor_ok) echo -e "\e[1;32m[  OK  ]\e[0m $p1" ;;
            doctor_warn) echo -e "\e[1;33m[ WARN ]\e[0m $p1" ;;
            doctor_err) echo -e "\e[1;31m[ FAIL ]\e[0m $p1" ;;
            all_done) echo -e "\n\e[1;32m[+] 部署与诊断检查完成\e[0m" ;;
            reboot_hint) echo -e "\e[1;36m提示: 建议重启 Noctalia 或重新加载 Niri 以使配置生效\e[0m" ;;

            # Standalone & Update Strings
            git_required) echo -e "\e[1;31m[-] 未安装 git。请先安装 git\e[0m" ;;
            cloning_repo) echo -e "\n\e[1;34m:: 正在克隆 NyxNiri 仓库至缓存目录 ($CACHE_DIR)…\e[0m" ;;
            checking_updates) echo -e "\n\e[1;34m:: 正在检查仓库与脚本更新…\e[0m" ;;
            updating_done) echo -e "\e[1;32m[+] 更新与重载成功，正在重启脚本…\e[0m" ;;
            updating_failed) echo -e "\e[1;31m[-] 更新失败。请检查网络与 Git 状态。\e[0m" ;;
            dirty_tree_warn) echo -e "\e[1;33m[!] 检测到 $p1 存在未提交改动，继续更新将覆盖此改动。\e[0m" ;;
            dirty_tree_confirm) echo -e ":: 是否丢弃本地改动并继续？[y/N]: " ;;
            update_cancelled_dirty) echo -e "\e[1;34m已取消更新，本地改动已保留\e[0m" ;;

            # AUR & mpvpaper
            aur_skip) echo -e "\e[1;33m[!] AUR 软件包 ($p1) 需要 AUR helper (paru/yay)，跳过安装\e[0m" ;;
            aur_helper_required) echo -e "\e[1;33m    请先安装 paru 或 yay，而后重新运行依赖安装。\e[0m" ;;
            aur_bootstrap_prompt) echo -e "未检测到 AUR helper (paru/yay)。自动安装 paru？[Y/n]: " ;;
            aur_bootstrap_start) echo -e "\n\e[1;34m:: 准备 paru (AUR helper)：优先官方源，其次源码构建…\e[0m" ;;
            aur_bootstrap_cleanup) echo -e ":: 移除残留 paru-bin 包…\e[0m" ;;
            aur_bootstrap_repo) echo -e ":: 从官方源安装 paru…\e[0m" ;;
            aur_bootstrap_source) echo -e ":: 本机源码构建 paru (约 1-3 分钟)…\e[0m" ;;
            aur_bootstrap_ok) echo -e "\e[1;32m[+] paru 安装成功\e[0m" ;;
            aur_bootstrap_failed) echo -e "\e[1;31m[!] paru 安装失败，已跳过 AUR 依赖。请手动安装 paru 后重试。\e[0m" ;;
            aur_bootstrap_skip) echo -e "\e[1;33m[!] 已取消自动安装 paru，跳过 AUR 依赖\e[0m" ;;
            checking_mpvpaper) echo -e "\n\e[1;34m:: 检查 mpvpaper 版本…\e[0m" ;;
            mpvpaper_version_ok) echo -e "\e[1;32m[  OK  ]\e[0m mpvpaper $p1 >= 1.9，无已知内存泄漏" ;;
            mpvpaper_leak_warn) echo -e "\e[1;31m[ WARN ]\e[0m mpvpaper $p1 在默认硬解配置下存在 OpenGL 内存泄漏，建议升级至 1.9+ 或 mpvpaper-git\n   (参见: https://github.com/GhostNaN/mpvpaper/issues/127)" ;;
            mpvpaper_upgrade_prompt) echo -e ":: 是否安装 mpvpaper-git (AUR) 替代当前 mpvpaper $p1？[y/N]: " ;;
            mpvpaper_upgrade_done) echo -e "\e[1;32m[+] mpvpaper-git 安装完成\e[0m" ;;
            mpvpaper_upgrade_skip) echo -e "手动升级命令: paru -S mpvpaper-git 或 yay -S mpvpaper-git" ;;

            # Alerts / Prompts
            preflight_express_summary) echo -e "\n\e[1;34m:: 即将安装以下组件:\e[0m" ;;
            warn_deps_missing) echo -e "\n\e[1;33m[!] 缺失运行依赖\e[0m" ;;
            ask_install_now) echo -e ":: 是否检查并安装缺失依赖？[Y/n]: " ;;
            preflight_sudo_prompt) echo -e "\n\e[1;34m:: 部分步骤需要管理员权限。请输入 sudo 密码：\e[0m" ;;
        esac
    else
        case "$key" in
            lang_select) echo -e "\n\e[1;36m:: Select Language / 请选择语言:\e[0m" ;;
            installed) echo -e "\e[1;32m[Installed]\e[0m" ;;
            missing) echo -e "\e[1;31m[Missing]\e[0m" ;;

            # Main Menu
            menu_title) echo -e "\n\e[1;35m=== $PROJECT_NAME Control Panel ===\e[0m" ;;
            menu_group_deploy) echo -e "  \e[1;36m[ Deployment & Setup ]\e[0m" ;;
            menu_opt1) echo -e "  \e[1;32m1)\e[0m Express Deploy (Auto)" ;;
            menu_opt2) echo -e "  \e[1;32m2)\e[0m Custom Deploy" ;;
            menu_opt3) echo -e "  \e[1;32m3)\e[0m Check & Install Dependencies" ;;

            menu_group_backup) echo -e "\n  \e[1;36m[ Snapshots & Recovery ]\e[0m" ;;
            menu_opt4) echo -e "  \e[1;32m4)\e[0m Snapshot Management" ;;

            menu_group_maint) echo -e "\n  \e[1;36m[ Maintenance & Diagnostics ]\e[0m" ;;
            menu_opt5) echo -e "  \e[1;32m5)\e[0m Check Updates & Overwrite" ;;
            menu_opt6) echo -e "  \e[1;32m6)\e[0m System Doctor Diagnostics" ;;
            menu_opt7) echo -e "  \e[1;32m7)\e[0m Export Diagnostic Report (Bug Report)" ;;

            menu_group_system) echo -e "\n  \e[1;36m[ System Management ]\e[0m" ;;
            menu_opt8) echo -e "  \e[1;31m8)\e[0m Uninstall & Restore" ;;
            menu_opt9) echo -e "  \e[1;32m9)\e[0m Optional Modules (Greeter / fcitx5 / Purge)" ;;
            menu_opt0) echo -e "  \e[1;30m0)\e[0m Exit" ;;

            # Snapshot Management Submenu
            snapshot_menu_title) echo -e "\n\e[1;35m=== Snapshot Management ===\e[0m" ;;
            snapshot_sub_create) echo -e "  \e[1;32m1)\e[0m Create Snapshot" ;;
            snapshot_sub_list) echo -e "  \e[1;32m2)\e[0m List Snapshots" ;;
            snapshot_sub_delete) echo -e "  \e[1;31m3)\e[0m Delete Snapshot" ;;
            snapshot_sub_rollback) echo -e "  \e[1;32m4)\e[0m Rollback Snapshot" ;;
            snapshot_sub_back) echo -e "  \e[1;30m0)\e[0m Back to Main Menu" ;;

            # Optional Modules Submenu
            optmod_menu_title) echo -e "\n\e[1;35m=== Optional Modules ===\e[0m" ;;
            optmod_purge) echo -e "  \e[1;31m4)\e[0m Deep Purge (configs / snapshots / cache / wallpapers)" ;;
            optmod_back) echo -e "  \e[1;30m0)\e[0m Back to Main Menu" ;;

            # Greeter Submenu
            greeter_menu_title) echo -e "\n\e[1;35m=== Noctalia Greeter ===\e[0m" ;;
            greeter_sub_install) echo -e "  \e[1;32m1)\e[0m Install & Configure" ;;
            greeter_sub_status) echo -e "  \e[1;32m2)\e[0m Show Status" ;;
            greeter_sub_uninstall) echo -e "  \e[1;31m3)\e[0m Uninstall Config" ;;
            greeter_sub_back) echo -e "  \e[1;30m0)\e[0m Back" ;;

            # Fcitx Submenu
            fcitx_menu_title) echo -e "\n\e[1;35m=== NyxMellow fcitx5 Skin ===\e[0m" ;;
            fcitx_sub_install) echo -e "  \e[1;32m1)\e[0m Install Skin" ;;
            fcitx_sub_status) echo -e "  \e[1;32m2)\e[0m Show Status" ;;
            fcitx_sub_uninstall) echo -e "  \e[1;31m3)\e[0m Uninstall Skin" ;;
            fcitx_sub_back) echo -e "  \e[1;30m0)\e[0m Back" ;;

            # Module Status Labels
            status_installed_enabled) echo -e "\e[1;32m[Installed + Enabled]\e[0m" ;;
            status_installed) echo -e "\e[1;33m[Installed]\e[0m" ;;
            status_not_installed) echo -e "\e[1;31m[Not Installed]\e[0m" ;;
            status_enabled) echo -e "\e[1;32m[Enabled]\e[0m" ;;
            status_disabled) echo -e "\e[1;33m[Not Enabled]\e[0m" ;;
            status_fcitx5_missing) echo -e "\e[1;31m[fcitx5 Missing]\e[0m" ;;
            status_wallpapers_installed) echo -e "\e[1;32m[Downloaded]\e[0m" ;;
            status_wallpapers_missing) echo -e "\e[1;33m[Not Downloaded]\e[0m" ;;

            # Optional Modules Menu Labels & Wallpapers (External Pack)
            optmod_sub_fcitx) echo -e "NyxMellow fcitx5 Skin" ;;
            optmod_sub_wallpapers) echo -e "Wallpaper Pack (~100MB)" ;;
            msg_downloading_wallpapers) echo -e "\n\e[1;34m:: Downloading wallpapers from external repository…\e[0m" ;;
            msg_downloading_wallpapers_node) echo -e "  [$p1] Pulling wallpapers from [$p2]…" ;;
            msg_wallpapers_download_success) echo -e "\e[1;32m[+] Wallpapers deployed\e[0m" ;;
            msg_wallpapers_download_failed) echo -e "\e[1;31m[-] Failed to download wallpapers, skipping\e[0m" ;;

            # Install Flow
            fcitx_skipped_not_installed) echo -e "\e[1;33m  [skip]\e[0m fcitx5 not detected; skipping NyxMellow skin (run later: nyxniri fcitx install)" ;;
            install_cancelled) echo -e "\e[1;34mInstallation cancelled\e[0m" ;;
            install_step_configs) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Deploying config files…\e[0m" ;;
            install_step_wallpapers) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Syncing wallpapers…\e[0m" ;;
            install_step_deps) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Checking & installing dependencies…\e[0m" ;;
            install_step_fcitx) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Configuring fcitx5 skin…\e[0m" ;;
            install_step_greeter) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Configuring Noctalia Greeter…\e[0m" ;;
            install_summary_title) echo -e "\n\e[1;35m=== Install Summary ===\e[0m" ;;
            summary_configs) echo -e "  \e[1;32m✓\e[0m Config files: deployed" ;;
            summary_wallpapers) echo -e "  \e[1;32m✓\e[0m Wallpapers: synced" ;;
            summary_wallpapers_pack) echo -e "  \e[1;32m✓\e[0m Wallpapers: synced (with videos)" ;;
            summary_deps_ok) echo -e "  \e[1;32m✓\e[0m Dependencies: ready" ;;
            summary_deps_skip) echo -e "  \e[1;33m·\e[0m Dependencies: skipped (run later: nyxniri deps)" ;;
            summary_fcitx_on) echo -e "  \e[1;32m✓\e[0m NyxMellow fcitx5 skin: applied" ;;
            summary_fcitx_off) echo -e "  \e[1;33m·\e[0m NyxMellow fcitx5 skin: skipped" ;;
            summary_greeter_on) echo -e "  \e[1;32m✓\e[0m Noctalia Greeter: configured" ;;
            summary_greeter_off) echo -e "  \e[1;33m·\e[0m Noctalia Greeter: skipped" ;;

            # Test Deploy
            test_start) echo -e "\n\e[1;34m:: [test] Idempotent re-deploy (no backup / keep monitor.kdl / skip optional & deps)…\e[0m" ;;
            test_done) echo -e "\n\e[1;32m[+] Test deploy complete\e[0m" ;;

            menu_prompt) echo -e ":: Please select an option [0-9]: " ;;
            invalid_opt) echo -e "\e[1;31m[-] Invalid option, please try again\e[0m" ;;
            press_any_key) echo -e "\nPress any key to continue…" ;;
            generating_report) echo -e "\n\e[1;34m:: Collecting diagnostic data and exporting Bug Report…\e[0m" ;;
            report_done) echo -e "\e[1;32m[+] Bug Report exported to:\e[0m $p1\n\e[1;36mHint: Please attach this file when opening an issue\nQQ Group: 631425889 | Developer QQ: 2040244628 | Telegram: @Echoes678\e[0m" ;;

            # Optional Overwrite Upgrade Strings
            overwrite_title) echo -e "\n\e[1;35m────────────────────────────────────────────────────────────────\e[0m\n \e[1;36m:: NyxNiri Config Overwrite Upgrade\e[0m\n\e[1;35m────────────────────────────────────────────────────────────────\e[0m" ;;
            overwrite_opt1) echo -e "  \e[1;32m1)\e[0m Auto Overwrite Upgrade (with safe backup)" ;;
            overwrite_opt2) echo -e "  \e[1;36m2)\e[0m Custom Selective Overwrite" ;;
            overwrite_opt3) echo -e "  \e[1;33m3)\e[0m View Configuration Differences (Diff)" ;;
            overwrite_opt4) echo -e "  \e[1;30m4)\e[0m Skip Config Overwrite (Keep current ~/.config)" ;;
            overwrite_prompt) echo -e ":: Select overwrite mode [1-4] (default 1): " ;;
            selective_title) echo -e "\n\e[1;33m:: Select components to overwrite (type numbers to toggle, press Enter to confirm):\e[0m" ;;
            selective_hint) echo -e "Type space-separated numbers (e.g. 1 3) to toggle, then press Enter to confirm:" ;;
            upgrading_selected) echo -e "\n\e[1;34m:: Applying selected components…\e[0m" ;;
            overwrite_done) echo -e "\e[1;32m[+] Selected components deployed\e[0m" ;;
            
            # Master Component Menu
            master_menu_title) echo -e "\n\e[1;33m:: Confirm deployment checklist (press Enter to deploy, or type numbers to toggle):\e[0m" ;;
            master_item_config) echo -e "Core Config: $p1" ;;
            master_item_module) echo -e "Optional Module: $p1" ;;
            master_item_asset) echo -e "Heavy Asset: $p1" ;;
            master_item_behavior) echo -e "--- Deployment Behaviors ---" ;;
            master_item_backup) echo -e "Auto-create safe snapshot before deploy (Backup)" ;;
            master_item_monitor) echo -e "Keep existing monitor hardware config (Keep monitor.kdl)" ;;
            diff_viewer_title) echo -e "\n\e[1;36m:: Configuration Differences (Press 'q' to quit pager)\e[0m" ;;

            # Uninstall Strings
            uninstall_title) echo -e "\n\e[1;31m────────────────────────────────────────────────────────────────\e[0m\n \e[1;31m:: NyxNiri Uninstall & Environment Restoration Tool\e[0m\n\e[1;31m────────────────────────────────────────────────────────────────\e[0m" ;;
            uninstall_opt1) echo -e "  \e[1;32m1)\e[0m Standard Uninstall (Archive current configs, remove CLI)" ;;
            uninstall_opt2) echo -e "  \e[1;36m2)\e[0m Restore to Original State (Restore earliest pre-install backup)" ;;
            uninstall_opt3) echo -e "  \e[1;31m3)\e[0m Deep Purge (Remove all configs, snapshots, cache & wallpapers)" ;;
            uninstall_opt4) echo -e "  \e[1;30m4)\e[0m Cancel & Return" ;;
            uninstall_prompt) echo -e ":: Select uninstall mode [1-4]: " ;;
            uninstall_archived) echo -e "\e[1;32m[+] Archived current configs to:\e[0m $p1" ;;
            uninstall_done) echo -e "\e[1;32m[+] NyxNiri uninstalled successfully\e[0m" ;;
            purge_done) echo -e "\e[1;32m[+] Deep purge complete\e[0m" ;;
            restore_origin_done) echo -e "\e[1;32m[+] Restored system to original pre-install state\e[0m" ;;

            # Rollback Strings
            no_backups_found) echo -e "\e[1;33m[!] No configuration snapshots found\e[0m" ;;
            available_backups) echo -e "\n\e[1;36m:: Available NyxNiri Snapshots\e[0m" ;;
            select_rollback_target) echo -e ":: Select snapshot number to restore (or press Ctrl+C to cancel): " ;;
            rollback_invalid_num) echo -e "\e[1;31m[-] Invalid selection, rollback cancelled\e[0m" ;;
            rolling_back) echo -e "\n\e[1;34m:: Restoring configuration from snapshot [$p1]…\e[0m" ;;
            pre_rollback_backup) echo -e "\e[1;30m[Safety] Auto-saved pre-rollback snapshot of current configs: $p1\e[0m" ;;
            rollback_done) echo -e "\e[1;32m[+] Rollback complete! Restored to snapshot: $p1\e[0m" ;;
            snapshot_note_prompt) echo -e ":: Enter snapshot note (press Enter to skip): " ;;

            # Snapshot Delete Strings
            delete_confirm) echo -e "\n\e[1;31m[!] Will delete snapshot: $p1\e[0m" ;;
            delete_prompt) echo -e ":: Confirm deleting this snapshot? [y/N]: " ;;
            delete_cancelled) echo -e "\e[1;34mDeletion cancelled\e[0m" ;;
            delete_done) echo -e "\e[1;32m[+] Deleted snapshot [$p1], $p2 snapshot(s) remaining\e[0m" ;;
            delete_invalid_num) echo -e "\e[1;31m[-] Invalid selection, deletion cancelled\e[0m" ;;

            # Dependency Menu
            dep_menu_title) echo -e "\n\e[1;33m:: Select dependencies to install (type numbers to toggle, press Enter to confirm):\e[0m" ;;
            dep_menu_hint) echo -e "Type numbers to toggle, or hotkeys [\e[1;32ma\e[0m]All [\e[1;32mn\e[0m]None [\e[1;32mi\e[0m/Enter]Install: " ;;
            copy_done) echo -e "\e[1;32mConfigurations deployed successfully\e[0m" ;;

            # Optional Greeter Module
            greeter_install_title) echo -e "\n\e[1;35m[ Optional Module ] Noctalia Greeter login setup\e[0m" ;;
            greeter_install_pkgs) echo -e "\n\e[1;34m:: Installing greetd and noctalia-greeter…\e[0m" ;;
            greeter_aur_required) echo -e "\e[1;33m[!] noctalia-greeter (AUR) requires paru/yay. Install an AUR helper and retry.\e[0m" ;;
            greeter_pkg_failed) echo -e "\e[1;31m[!] Failed to install $p1; continuing…\e[0m" ;;
            greeter_install_failed) echo -e "\e[1;31m[!] noctalia-greeter not installed; aborted. Retry later with: nyxniri greeter install\e[0m" ;;
            greeter_dm_conflict) echo -e "\e[1;33m[!] Other display managers detected: $p1. Disable them manually (e.g. sudo systemctl disable $p1).\e[0m" ;;
            greeter_config_skip) echo -e "\e[1;32m[+] greetd already configured to use noctalia-greeter; skipped\e[0m" ;;
            greeter_config_written) echo -e "\e[1;32m[+] greetd config written: $p1 (previous config backed up)\e[0m" ;;
            greeter_config_failed) echo -e "\e[1;31m[!] Failed to write greetd config: $p1 (requires sudo)\e[0m" ;;
            greeter_state_dir_created) echo -e "\e[1;32m[+] Created state dir /var/lib/noctalia-greeter\e[0m" ;;
            greeter_cmd_failed) echo -e "\e[1;31m[!] Privileged command failed: $p1 (requires sudo)\e[0m" ;;
            greeter_polkit_skip) echo -e "\e[1;32m[+] polkit rule already present; skipped\e[0m" ;;
            greeter_polkit_written) echo -e "\e[1;32m[+] polkit rule written: $p1\e[0m" ;;
            greeter_polkit_failed) echo -e "\e[1;31m[!] Failed to write polkit rule\e[0m" ;;
            greeter_enabled) echo -e "\e[1;32m[+] greetd service enabled (takes effect after reboot)\e[0m" ;;
            greeter_enabled_skip) echo -e "\e[1;32m[+] greetd service already enabled\e[0m" ;;
            greeter_enable_failed) echo -e "\e[1;31m[!] Failed to enable greetd. Run manually: sudo systemctl enable greetd\e[0m" ;;
            greeter_reboot_hint) echo -e "\e[1;36mHint: After reboot the login screen becomes Noctalia Greeter. Sync theme via Noctalia Settings → Security → Noctalia Greeter → Sync Now.\e[0m" ;;
            greeter_status_title) echo -e "\n\e[1;36m:: Noctalia Greeter status\e[0m" ;;
            greeter_status_ok) echo -e "\e[1;32m[+] Greeter ready\e[0m" ;;
            greeter_status_hint) echo -e "\e[1;36mHint: Run nyxniri greeter install to set up.\e[0m" ;;
            greeter_uninstall_title) echo -e "\n\e[1;33m:: Noctalia Greeter uninstall (keeps installed packages)\e[0m" ;;
            greeter_uninstall_restored) echo -e "\e[1;32m[+] Restored greetd config: $p1\e[0m" ;;
            greeter_uninstall_nobackup) echo -e "\e[1;33m[!] No greetd config backup found; kept current config\e[0m" ;;
            greeter_uninstall_polkit) echo -e "\e[1;32m[+] polkit rule removed\e[0m" ;;
            greeter_uninstall_done) echo -e "\e[1;32m[+] Greeter uninstalled. To remove packages: paru -R noctalia-greeter greetd\e[0m" ;;

            # Optional Fcitx5 Dynamic Theme Module
            fcitx_install_title) echo -e "\n\e[1;35m[ Optional Module ] NyxMellow dynamic fcitx5 skin setup\e[0m" ;;
            fcitx_skip_no_fcitx5) echo -e "\e[1;33m[!] fcitx5 not detected; skipped skin activation (theme templates deployed; run nyxniri fcitx install after installing fcitx5).\e[0m" ;;
            fcitx_templates_deployed) echo -e "\e[1;32m[+] Theme templates deployed: ~/.local/share/fcitx5/themes/nyxmellow/templates/\e[0m" ;;
            fcitx_render_ok) echo -e "\e[1;32m[+] Noctalia rendered the nyxmellow skin with the current theme\e[0m" ;;
            fcitx_render_pending) echo -e "\e[1;33m[!] noctalia not running; templates will apply on next theme change (or run nyxniri fcitx install).\e[0m" ;;
            fcitx_theme_set) echo -e "\e[1;32m[+] fcitx5 switched to theme: nyxmellow ($p1)\e[0m" ;;
            fcitx_restarted) echo -e "\e[1;32m[+] fcitx5 restarted to load new skin\e[0m" ;;
            fcitx_status_title) echo -e "\n\e[1;36m:: NyxMellow dynamic fcitx5 skin status\e[0m" ;;
            fcitx_uninstall_title) echo -e "\n\e[1;33m:: NyxMellow dynamic fcitx5 skin uninstall\e[0m" ;;
            fcitx_uninstall_done) echo -e "\e[1;32m[+] NyxMellow skin uninstalled; fcitx5 theme reverted\e[0m" ;;
            fcitx_registered) echo -e "\e[1;32m[+] Noctalia templates registered ($p1)\e[0m" ;;
            fcitx_not_registered) echo -e "\e[1;33m[!] Noctalia templates not registered ($p1)\e[0m" ;;

            # System Doctor
            running_doctor) echo -e "\n\e[1;35mRunning System Doctor for diagnostics…\e[0m" ;;
            doctor_ok) echo -e "\e[1;32m[  OK  ]\e[0m $p1" ;;
            doctor_warn) echo -e "\e[1;33m[ WARN ]\e[0m $p1" ;;
            doctor_err) echo -e "\e[1;31m[ FAIL ]\e[0m $p1" ;;
            all_done) echo -e "\n\e[1;32m[+] All deployment and diagnostics completed\e[0m" ;;
            reboot_hint) echo -e "\e[1;36mHint: Recommended to restart Noctalia or reload Niri for settings to take effect\e[0m" ;;

            # Standalone & Update Strings
            git_required) echo -e "\e[1;31m[-] Error: git is required to download or update the repository\e[0m" ;;
            cloning_repo) echo -e "\n\e[1;34m:: Standalone mode detected. Cloning repository to cache ($CACHE_DIR)…\e[0m" ;;
            checking_updates) echo -e "\n\e[1;34m:: Checking for repository and script updates…\e[0m" ;;
            updating_done) echo -e "\e[1;32m[+] Update successful. Restarting script…\e[0m" ;;
            updating_failed) echo -e "\e[1;31m[-] Update failed. Please check network connection or git status.\e[0m" ;;
            dirty_tree_warn) echo -e "\e[1;33m[!] Uncommitted local changes detected in $p1; continuing will discard them.\e[0m" ;;
            dirty_tree_confirm) echo -e ":: Continue and discard local changes? [y/N]: " ;;
            update_cancelled_dirty) echo -e "\e[1;34mUpdate cancelled; local changes preserved\e[0m" ;;

            # AUR & mpvpaper
            aur_skip) echo -e "\e[1;33m[!] AUR packages ($p1) require an AUR helper (paru/yay). Skipping.\e[0m" ;;
            aur_helper_required) echo -e "\e[1;33m    Install paru or yay first, then re-run dependency installation.\e[0m" ;;
            aur_bootstrap_prompt) echo -e "No AUR helper (paru/yay) detected. Auto-install paru? [Y/n]: " ;;
            aur_bootstrap_start) echo -e "\n\e[1;34m:: Setting up paru (AUR helper): official repo first, then local source build…\e[0m" ;;
            aur_bootstrap_cleanup) echo -e ":: Removing stale paru-bin packages…\e[0m" ;;
            aur_bootstrap_repo) echo -e ":: Installing paru from official repos…\e[0m" ;;
            aur_bootstrap_source) echo -e ":: paru not in official repos; building from source (~1-3 min)…\e[0m" ;;
            aur_bootstrap_ok) echo -e "\e[1;32m[+] paru installed successfully\e[0m" ;;
            aur_bootstrap_failed) echo -e "\e[1;31m[!] paru bootstrap failed; skipped AUR packages. Install paru manually and retry.\e[0m" ;;
            aur_bootstrap_skip) echo -e "\e[1;33m[!] Auto-install of paru cancelled; skipped AUR packages\e[0m" ;;
            checking_mpvpaper) echo -e "\n\e[1;34m:: Checking mpvpaper version…\e[0m" ;;
            mpvpaper_version_ok) echo -e "\e[1;32m[  OK  ]\e[0m mpvpaper $p1 >= 1.9, no known memory leak" ;;
            mpvpaper_leak_warn) echo -e "\e[1;31m[ WARN ]\e[0m mpvpaper $p1 has a known OpenGL memory leak with hwdec enabled. Upgrade to 1.9+ or install mpvpaper-git!\n   (See: https://github.com/GhostNaN/mpvpaper/issues/127)" ;;
            mpvpaper_upgrade_prompt) echo -e ":: Install mpvpaper-git (AUR) to replace mpvpaper $p1 and fix leak? [y/N]: " ;;
            mpvpaper_upgrade_done) echo -e "\e[1;32m[+] mpvpaper-git installed, memory leak fixed\e[0m" ;;
            mpvpaper_upgrade_skip) echo -e "To manually upgrade: paru -S mpvpaper-git or yay -S mpvpaper-git" ;;

            # Alerts / Prompts
            preflight_express_summary) echo -e "\n\e[1;34m:: Preparing to install the following components:\e[0m" ;;
            warn_deps_missing) echo -e "\n\e[1;33m[!] Missing required dependencies\e[0m" ;;
            ask_install_now) echo -e ":: Check and install missing dependencies? [Y/n]: " ;;
            preflight_sudo_prompt) echo -e "\n\e[1;34m:: Administrator privileges required. Please enter sudo password:\e[0m" ;;
        esac
    fi
}

select_language() {
    local lang_cache_file="$HOME/.local/state/NyxNiri/lang"
    if [ -f "$lang_cache_file" ]; then
        LANG_MODE="$(cat "$lang_cache_file")"
        return 0
    fi

    clear 2>/dev/null || true
    show_logo
    echo ""
    msg lang_select
    echo -e "  \e[1;32m1)\e[0m English"
    echo -e "  \e[1;32m2)\e[0m 简体中文 (Simplified Chinese)"
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

    mkdir -p "$(dirname "$lang_cache_file")"
    echo "$LANG_MODE" > "$lang_cache_file"
}

# General bilingual prompt confirmation helper.
# Returns 0 for Yes (y/Y), 1 for No.
prompt_confirm() {
    local msg_key="$1" default="${2:-n}"
    [ "${NYXNIRI_AUTO_YES:-0}" = "1" ] && return 0
    if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
        [[ "$default" =~ ^[Yy]$ ]] && return 0 || return 1
    fi
    local choice=""
    read -r -p "$(msg "$msg_key")" choice < /dev/tty || choice="$default"
    [[ "$choice" =~ ^[Yy]$ ]]
}
