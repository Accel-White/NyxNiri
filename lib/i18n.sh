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
    echo -e "  \e[1;36mNoctalia V5 & Niri Desktop Environment Setup\e[0m \e[90m|\e[0m \e[1;37m${CURRENT_VERSION:-v2.x}\e[0m"
    echo -e "  \e[90mMode: ${MODE_LABEL:-Local Path} (${REPO_DIR:-.})\e[0m\n"
}

# Pad a string to a target display width cleanly and efficiently.
# Count characters (wc -m), not bytes, so CJK strings align correctly.
_disp_pad() {
    local s="$1" width="${2:-24}"
    local len
    len=$(printf '%s' "$s" | wc -m)
    local pad=$((width - len))
    [ "$pad" -lt 0 ] && pad=0
    printf '%s%*s' "$s" "$pad" ""
}

# Render one checkbox row (prefix + check mark + label) consistently.
# Shared by the master component menu and the dependency menu.
_render_check_row() {
    local is_focus="$1" check="$2" label="$3"
    if [ "$is_focus" = "1" ]; then
        printf "  \e[1;36m❯ \e[0m%b \e[1;37m%s\e[0m\n" "$check" "$label"
    else
        printf "    %b %s\n" "$check" "$label"
    fi
}

msg() {
    local key="$1"
    shift || true
    local p1="${1:-}"
    local p2="${2:-}"
    local p3="${3:-}"

    if [ "${LANG_MODE:-en}" = "zh" ]; then
        case "$key" in
            lang_select) echo -e "\n\e[1;36m:: 请选择语言 / Select Language:\e[0m" ;;
            installed) echo -e "\e[1;32m[已安装]\e[0m" ;;
            missing) echo -e "\e[1;31m[未安装]\e[0m" ;;

            # Main Menu
            menu_title) echo -e "\n  \e[1;36m── $PROJECT_NAME 控制面板 ──\e[0m\n" ;;
            menu_group_deploy) echo -e "  \e[1;34m部署与安装\e[0m" ;;
            menu_opt1) echo -e "部署组件" ;;
            menu_opt2) echo -e "检查与安装依赖" ;;
            menu_group_maint) echo -e "\n  \e[1;34m运维与诊断\e[0m" ;;
            menu_group_system) echo -e "\n  \e[1;34m系统管理\e[0m" ;;
            menu_opt3) echo -e "快照管理" ;;
            menu_opt4) echo -e "检查更新" ;;
            menu_opt5) echo -e "系统诊断" ;;
            menu_opt6) echo -e "导出诊断报告" ;;
            menu_opt7) echo -e "卸载" ;;
            menu_opt8) echo -e "可选模块" ;;
            menu_opt0) echo -e "退出" ;;

            # Snapshot Management Submenu
            snapshot_menu_title) echo -e "\n  \e[1;36m── 快照管理 ──\e[0m\n" ;;
            snapshot_sub_create) echo -e "创建快照" ;;
            snapshot_sub_list) echo -e "查看快照列表" ;;
            snapshot_sub_delete) echo -e "删除快照" ;;
            snapshot_sub_rollback) echo -e "回滚快照" ;;
            snapshot_sub_back) echo -e "返回主菜单" ;;

            # Optional Modules Submenu
            optmod_menu_title) echo -e "\n  \e[1;36m── 可选模块 ──\e[0m\n" ;;
            optmod_purge) echo -e "深度清理" ;;
            optmod_back) echo -e "返回主菜单" ;;

            # Greeter Submenu
            greeter_menu_title) echo -e "\n  \e[1;36m── Noctalia Greeter ──\e[0m\n" ;;
            greeter_sub_install) echo -e "安装与配置" ;;
            greeter_sub_status) echo -e "查看状态" ;;
            greeter_sub_uninstall) echo -e "卸载配置" ;;
            greeter_sub_back) echo -e "返回" ;;

            # Fcitx Submenu
            fcitx_menu_title) echo -e "\n  \e[1;36m── NyxMellow fcitx5 皮肤 ──\e[0m\n" ;;
            fcitx_sub_install) echo -e "安装皮肤" ;;
            fcitx_sub_status) echo -e "查看状态" ;;
            fcitx_sub_uninstall) echo -e "卸载皮肤" ;;
            fcitx_sub_back) echo -e "返回" ;;

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
            optmod_sub_wallpapers) echo -e "下载壁纸包（约 100MB）" ;;
            msg_downloading_wallpapers) echo -e "\n\e[1;34m:: 拉取壁纸包…\e[0m" ;;
            msg_downloading_wallpapers_node) echo -e "  [$p1] 从 [$p2] 节点拉取壁纸仓库…" ;;
            msg_wallpapers_download_success) echo -e "\e[1;32m[✓] 壁纸包已部署\e[0m" ;;
            msg_wallpapers_download_failed) echo -e "\e[1;31m[!] 壁纸包下载失败，已跳过\e[0m" ;;

            # Install Flow
            fcitx_skipped_not_installed) echo -e "\e[1;33m[!] 未检测到 fcitx5，已跳过皮肤激活。安装后运行: nyxniri fcitx install\e[0m" ;;
            install_cancelled) echo -e "\e[1;34m已取消安装\e[0m" ;;
            install_step_configs) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 部署配置…\e[0m" ;;
            install_step_wallpapers) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 同步壁纸…\e[0m" ;;
            install_step_deps) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 检查与安装依赖…\e[0m" ;;
            install_step_fcitx) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 配置 fcitx5 皮肤…\e[0m" ;;
            install_step_greeter) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] 配置 Noctalia Greeter…\e[0m" ;;
            install_summary_title) echo -e "部署完成" ;;
            summary_title_install) echo -e "部署完成" ;;
            summary_title_update) echo -e "更新完成" ;;
            summary_title_test) echo -e "测试部署完成" ;;
            summary_section_details) echo -e "部署明细" ;;
            summary_item_configs_ok) echo -e "核心配置:   部署成功 ($p1)" ;;
            summary_item_configs_skip) echo -e "核心配置:   已跳过" ;;
            summary_item_wallpapers_ok) echo -e "壁纸图包:   已同步" ;;
            summary_item_wallpapers_skip) echo -e "壁纸图包:   已跳过" ;;
            summary_item_fcitx_ok) echo -e "输入法:     NyxMellow fcitx5 skin" ;;
            summary_item_fcitx_skip) echo -e "输入法:     已跳过" ;;
            summary_item_deps_ok) echo -e "系统依赖:   环境已就绪" ;;
            summary_item_deps_skip) echo -e "系统依赖:   未完全满足" ;;
            summary_item_greeter_ok) echo -e "登录器:     Noctalia Greeter" ;;
            summary_item_greeter_skip) echo -e "登录器:     已跳过" ;;
            summary_section_preserved) echo -e "保留的配置清单 (自动继承)" ;;
            summary_section_next) echo -e "下一步" ;;
            summary_next_start) echo -e "启动桌面 : 运行 niri-session" ;;
            summary_next_manual) echo -e "速查手册 : 运行 nyxhelp" ;;
            summary_next_panel) echo -e "控制面板 : 运行 nyxniri" ;;

            # Test Deploy
            test_start) echo -e "\n\e[1;34m:: [test] 幂等测试部署 (跳过备份与依赖检查)…\e[0m" ;;
            test_done) echo -e "\n\e[1;32m[✓] 测试部署完成\e[0m" ;;

            menu_hint) echo -e "\n  \e[90m[↑/↓/j/k] 移动焦点  [Enter/Space] 选择  [0/q] 退出\e[0m" ;;
            submenu_hint) echo -e "\n  \e[90m[↑/↓/j/k] 移动焦点  [Enter/Space] 选择  [0/q] 返回\e[0m" ;;
            menu_prompt) echo -e "\n▸ 请选择 [0-9]: " ;;
            invalid_opt) echo -e "\e[1;31m[✗] 无效选项，请重新选择\e[0m" ;;
            press_any_key) echo -e "\n按任意键继续…" ;;
            generating_report) echo -e "\n\e[1;34m:: 正在收集诊断数据…\e[0m" ;;
            report_done) echo -e "\e[1;32m[✓] 诊断报告已导出至:\e[0m $p1\n\e[1;36m提示: 提交 Issue 请附带此文件\e[0m\n\e[90mQQ 群: 631425889 | Telegram: @Echoes678\e[0m" ;;

            # Optional Overwrite Upgrade Strings
            overwrite_title) echo -e "\n  \e[1;36m── NyxNiri 配置更新 ──\e[0m\n" ;;
            overwrite_opt1) echo -e "覆盖/更新组件" ;;
            overwrite_opt2) echo -e "查看配置差异" ;;
            overwrite_opt3) echo -e "仅更新脚本代码" ;;

            selective_hint) echo -e "  \e[90m[↑/↓/j/k] 移动焦点  [Space] 切换  [a] 全选  [n] 清空  [Enter] 确认\e[0m" ;;
            upgrading_selected) echo -e "\n\e[1;34m:: 正在部署选中组件…\e[0m" ;;
            overwrite_done) echo -e "\e[1;32m[✓] 选中组件已部署\e[0m" ;;
            
            # Master Component Menu
            master_menu_title) echo -e "\n  \e[1;36m── 组件部署清单 ──\e[0m\n" ;;
            master_item_config) echo -e "核心配置: $p1" ;;
            master_item_module) echo -e "可选模块: $p1" ;;
            master_item_asset) echo -e "重型资源: $p1" ;;
            master_item_behavior) echo -e "\n  ── 部署行为 ──" ;;
            master_item_backup) echo -e "部署前自动创建快照" ;;
            master_item_monitor) echo -e "保留当前显示器配置 (monitor.kdl)" ;;
            diff_viewer_title) echo -e "\n\e[1;36m:: 配置差异对比 (按 q 退出)\e[0m" ;;

            # Uninstallation & Restore
            uninstall_title) echo -e "\n  \e[1;36m── 卸载与复原 ──\e[0m\n" ;;
            uninstall_opt1) echo -e "标准卸载 (归档当前配置并移除文件与 CLI)" ;;
            uninstall_opt2) echo -e "环境复原 (恢复至初始备份)" ;;
            uninstall_opt3) echo -e "深度清理 (清除所有配置、快照、缓存与壁纸)" ;;
            uninstall_opt4) echo -e "取消返回" ;;
            uninstall_prompt) echo -e "▸ 请选择卸载模式 [1-4]: " ;;
            uninstall_archived) echo -e "\e[1;32m[✓] 当前配置已归档至:\e[0m $p1" ;;
            uninstall_done) echo -e "\e[1;32m[✓] NyxNiri 卸载完成\e[0m" ;;
            purge_done) echo -e "\e[1;32m[✓] 深度清理完成\e[0m" ;;
            restore_origin_done) echo -e "\e[1;32m[✓] 已恢复至初始环境\e[0m" ;;

            # Rollback Strings
            no_backups_found) echo -e "\e[1;33m[!] 未找到可用快照\e[0m" ;;
            available_backups) echo -e "\n\e[1;36m:: 可用快照列表\e[0m" ;;
            select_rollback_target) echo -e "▸ 请选择要恢复的快照序号 (Ctrl+C 取消): " ;;
            rollback_invalid_num) echo -e "\e[1;31m[✗] 无效序号，已取消回滚\e[0m" ;;
            rolling_back) echo -e "\n\e[1;34m:: 正在从快照 [$p1] 恢复配置…\e[0m" ;;
            pre_rollback_backup) echo -e "\e[90m[✓] 已自动为当前配置创建回滚前快照: $p1\e[0m" ;;
            rollback_done) echo -e "\e[1;32m[✓] 已恢复至快照: $p1\e[0m" ;;
            snapshot_note_prompt) echo -e "▸ 请输入快照备注 (直接回车跳过): " ;;

            # Snapshot Delete Strings
            delete_confirm) echo -e "\n\e[1;31m[!] 将删除快照: $p1\e[0m" ;;
            delete_prompt) echo -e "▸ 确认删除该快照？[y/N]: " ;;
            delete_cancelled) echo -e "\e[1;34m已取消删除\e[0m" ;;
            delete_done) echo -e "\e[1;32m[✓] 已删除快照 [$p1]，剩余 $p2 个\e[0m" ;;
            delete_invalid_num) echo -e "\e[1;31m[✗] 无效序号，已取消删除\e[0m" ;;

            # Dependency Menu
            dep_menu_title) echo -e "\n  \e[1;36m── 系统依赖检查与安装 ──\e[0m\n" ;;
            dep_menu_hint) echo -e "  \e[90m[↑/↓/j/k] 移动焦点  [Space] 切换  [a] 全选  [n] 清空  [Enter] 开始安装\e[0m" ;;
            installing_selected) echo -e "\n\e[1;34m:: 正在安装选中依赖…\e[0m" ;;

            # Optional Greeter Module
            greeter_install_title) echo -e "\n\e[1;35m[ 可选模块 ] Noctalia Greeter 安装与配置\e[0m" ;;
            greeter_install_pkgs) echo -e "\n\e[1;34m:: 正在安装 greetd 与 noctalia-greeter…\e[0m" ;;
            greeter_aur_required) echo -e "\e[1;33m[!] noctalia-greeter (AUR) 需要 paru 或 yay。请先安装 AUR helper。\e[0m" ;;
            greeter_pkg_failed) echo -e "\e[1;31m[!] 软件包 $p1 安装失败，继续后续步骤…\e[0m" ;;
            greeter_install_failed) echo -e "\e[1;31m[!] noctalia-greeter 安装失败。稍后运行 nyxniri greeter install 重试。\e[0m" ;;
            greeter_install_skipped) echo -e "\e[1;33m[!] 已跳过 Noctalia Greeter 配置\e[0m" ;;
            greeter_dm_conflict) echo -e "\e[1;33m[!] 存在冲突的显示管理器 ($p1)，请先手动将其禁用。\e[0m" ;;
            greeter_config_written) echo -e "\e[1;32m[✓] 已写入 greetd 配置: $p1 (原配置已备份)\e[0m" ;;
            greeter_config_failed) echo -e "\e[1;31m[!] 写入 greetd 配置失败: $p1 (需要 sudo 权限)\e[0m" ;;
            greeter_state_dir_created) echo -e "\e[1;32m[✓] 已创建状态目录 /var/lib/noctalia-greeter\e[0m" ;;
            greeter_cmd_failed) echo -e "\e[1;31m[!] 特权命令执行失败: $p1 (需要 sudo 权限)\e[0m" ;;
            greeter_polkit_skip) echo -e "\e[1;32m[✓] polkit 规则已存在，跳过\e[0m" ;;
            greeter_polkit_written) echo -e "\e[1;32m[✓] 已写入 polkit 免密规则: $p1\e[0m" ;;
            greeter_polkit_failed) echo -e "\e[1;31m[!] 写入 polkit 规则失败\e[0m" ;;
            greeter_enabled) echo -e "\e[1;32m[✓] 已启用 greetd 服务 (重启生效)\e[0m" ;;
            greeter_enabled_skip) echo -e "\e[1;32m[✓] greetd 服务已启用\e[0m" ;;
            greeter_enable_failed) echo -e "\e[1;31m[!] 启用 greetd 服务失败。请手动运行: sudo systemctl enable greetd\e[0m" ;;
            greeter_reboot_hint) echo -e "\e[1;36m提示: 重启后登录界面生效。主题同步路径: Noctalia 设置 → 安全 → Noctalia Greeter → Sync Now\e[0m" ;;
            greeter_status_title) echo -e "\n\e[1;36m:: Noctalia Greeter 状态检查\e[0m" ;;
            greeter_status_ok) echo -e "\e[1;32m[✓] Greeter 已就绪\e[0m" ;;
            greeter_status_hint) echo -e "\e[1;36m提示: 运行 nyxniri greeter install 完成配置\e[0m" ;;
            greeter_uninstall_title) echo -e "\n\e[1;33m:: Noctalia Greeter 卸载 (保留软件包)\e[0m" ;;
            greeter_uninstall_restored) echo -e "\e[1;32m[✓] 已还原 greetd 配置: $p1\e[0m" ;;
            greeter_uninstall_nobackup) echo -e "\e[1;33m[!] 未找到 greetd 配置备份，已保留当前配置\e[0m" ;;
            greeter_uninstall_polkit) echo -e "\e[1;32m[✓] 已移除 polkit 免密规则\e[0m" ;;
            greeter_uninstall_done) echo -e "\e[1;32m[✓] Greeter 卸载完成。若需移除软件包: paru -R noctalia-greeter greetd\e[0m" ;;

            # Optional Fcitx5 Dynamic Theme Module
            fcitx_install_title) echo -e "\n\e[1;35m[ 可选模块 ] NyxMellow 动态 fcitx5 皮肤配置\e[0m" ;;
            fcitx_skip_no_fcitx5) echo -e "\e[1;33m[!] 未找到 fcitx5，已跳过皮肤激活 (安装后运行 nyxniri fcitx install 即可)\e[0m" ;;
            fcitx_templates_deployed) echo -e "\e[1;32m[✓] 主题模板已部署: ~/.local/share/fcitx5/themes/nyxmellow/templates/\e[0m" ;;
            fcitx_render_ok) echo -e "\e[1;32m[✓] Noctalia 已按当前主题渲染 nyxmellow 皮肤\e[0m" ;;
            fcitx_render_pending) echo -e "\e[1;33m[!] noctalia 未运行，模板将在下次主题切换时生效\e[0m" ;;
            fcitx_theme_set) echo -e "\e[1;32m[✓] fcitx5 已切换主题: nyxmellow ($p1)\e[0m" ;;
            fcitx_restarted) echo -e "\e[1;32m[✓] fcitx5 已重启以加载新皮肤\e[0m" ;;
            fcitx_status_title) echo -e "\n\e[1;36m:: NyxMellow 动态 fcitx5 皮肤状态\e[0m" ;;
            fcitx_uninstall_title) echo -e "\n\e[1;33m:: NyxMellow 动态 fcitx5 皮肤卸载\e[0m" ;;
            fcitx_uninstall_done) echo -e "\e[1;32m[✓] NyxMellow 皮肤已卸载，fcitx5 主题已还原\e[0m" ;;
            fcitx_registered) echo -e "\e[1;32m[✓] Noctalia 模板已注册 ($p1)\e[0m" ;;
            fcitx_not_registered) echo -e "\e[1;33m[!] Noctalia 模板未注册 ($p1)\e[0m" ;;

            # Deployment & Backup
            backing_up) echo -e "\n\e[1;34m:: 正在创建配置快照…\e[0m" ;;
            backup_done) echo -e "\e[1;32m[✓] 已创建快照: $p1\e[0m" ;;
            copying_configs) echo -e "\n\e[1;34m:: 正在部署配置…\e[0m" ;;
            copy_done) echo -e "\e[1;32m[✓] 配置已部署\e[0m" ;;

            # System Doctor
            running_doctor) echo -e "\n\e[1;35m:: 正在运行 System Doctor 进行系统诊断…\e[0m" ;;
            doctor_ok) echo -e "\e[1;32m[✓]\e[0m $p1" ;;
            doctor_warn) echo -e "\e[1;33m[!]\e[0m $p1" ;;
            doctor_err) echo -e "\e[1;31m[✗]\e[0m $p1" ;;
            all_done) echo -e "\n\e[1;32m[✓] 部署与诊断检查完成\e[0m" ;;
            reboot_hint) echo -e "\e[1;36m提示: 建议重启 Noctalia 或重新加载 Niri 以使配置生效\e[0m" ;;

            # Standalone & Update Strings
            git_required) echo -e "\e[1;31m[✗] 未找到 git。请先安装。\e[0m" ;;
            cloning_repo) echo -e "\n\e[1;34m:: 拉取仓库至缓存 ($CACHE_DIR)…\e[0m" ;;
            checking_updates) echo -e "\n\e[1;34m:: 检查更新…\e[0m" ;;
            updating_done) echo -e "\e[1;32m[✓] 更新完成，正在重启…\e[0m" ;;
            updating_failed) echo -e "\e[1;31m[✗] 更新失败，请检查网络与 Git 状态。\e[0m" ;;
            dirty_tree_warn) echo -e "\e[1;33m[!] $p1 存在未提交的改动。\e[0m" ;;
            dirty_tree_confirm) echo -e ":: 继续将丢弃这些改动。是否继续？[y/N]: " ;;
            update_cancelled_dirty) echo -e "\e[1;34m已取消更新，改动已保留。\e[0m" ;;
            update_skipped_dev_repo) echo -e "\n\e[1;33m[!] 本地仓库 ($p1) 有未提交的改动或分支偏离。\e[0m\n\e[1;36m已跳过源码更新，不影响后续配置部署。\e[0m\n" ;;

            # AUR & mpvpaper
            aur_skip) echo -e "\e[1;33m[!] AUR 软件包 ($p1) 需要 paru 或 yay，已跳过。\e[0m" ;;
            aur_helper_required) echo -e "\e[1;33m    请先安装 paru 或 yay，而后重新运行依赖安装。\e[0m" ;;
            aur_bootstrap_start) echo -e "\n\e[1;34m:: 正在准备 paru…\e[0m" ;;
            aur_bootstrap_cleanup) echo -e ":: 移除残留 paru-bin 包…\e[0m" ;;
            aur_bootstrap_repo) echo -e ":: 从官方源安装 paru…\e[0m" ;;
            aur_bootstrap_source) echo -e ":: 源码构建 paru (约 1-3 分钟)…\e[0m" ;;
            aur_bootstrap_ok) echo -e "\e[1;32m[✓] paru 安装成功\e[0m" ;;
            aur_bootstrap_failed) echo -e "\e[1;31m[!] paru 安装失败，已跳过 AUR 依赖。请手动安装后重试。\e[0m" ;;
            aur_bootstrap_skip) echo -e "\e[1;33m[!] 已取消安装 paru，跳过 AUR 依赖\e[0m" ;;
            checking_mpvpaper) echo -e "\n\e[1;34m:: 检查 mpvpaper 版本…\e[0m" ;;
            mpvpaper_version_ok) echo -e "\e[1;32m[✓]\e[0m mpvpaper $p1 >= 1.9，无已知内存泄漏" ;;
            mpvpaper_leak_warn) echo -e "\e[1;33m[!]\e[0m mpvpaper $p1 在默认硬解配置下存在 OpenGL 内存泄漏，建议升级至 1.9+ 或 mpvpaper-git\n   (参见: https://github.com/GhostNaN/mpvpaper/issues/127)" ;;
            mpvpaper_upgrade_done) echo -e "\e[1;32m[✓] mpvpaper-git 已安装\e[0m" ;;
            mpvpaper_upgrade_skip) echo -e "手动升级命令: paru -S mpvpaper-git 或 yay -S mpvpaper-git" ;;

            # Alerts / Prompts
            preflight_express_summary) echo -e "\n\e[1;34m:: 即将安装以下组件:\e[0m" ;;

            # Log & Internal Engine Strings
            # Core, Main, Network & Preflight Strings
            preflight_comp_config) echo -e "  \e[1;36m- 配置组件:\e[0m $p1 项" ;;
            preflight_comp_assets) echo -e "  \e[1;36m- 重型资源:\e[0m 全套壁纸包" ;;
            preflight_comp_module_fcitx) echo -e "  \e[1;36m- 可选模块:\e[0m $p1 fcitx5 皮肤" ;;
            preflight_comp_module_greeter) echo -e "  \e[1;36m- 可选模块:\e[0m $p1" ;;
            preflight_comp_deps) echo -e "  \e[1;36m- 系统依赖:\e[0m 检查与补全缺失依赖" ;;
            preflight_custom_config_kept) echo -e "\e[1;36m[ 保留了自定义配置 ]\e[0m" ;;
            err_sudo_aborted) echo -e "\n\e[1;31m[✗] 缺少管理员权限。已中止。\e[0m" ;;
            err_aborted_code) echo -e "\n\e[1;31m[✗] 异常终止 (退出码: $p1)\e[0m" ;;
            err_already_running) echo -e "\n\e[1;33m[!] 进程已在运行 (PID: $p1)\e[0m" ;;
            err_root_denied) echo -e "\n\e[1;31m[✗] 拒绝 root。请以普通用户身份运行。\e[0m" ;;
            net_pull_repo) echo -e "\e[1;34m:: 拉取仓库 (官方 -> gh-proxy)…\e[0m" >&2 ;;
            net_pull_node) echo -e "\n  \e[1;36m[$p1/$p2] 从 [$p3] 节点拉取…\e[0m" >&2 ;;
            net_pull_node_ok) echo -e "\e[1;32m[✓] 已从 [$p1] 拉取\e[0m\n" >&2 ;;
            net_pull_node_fail) echo -e "\e[1;31m[!] 从 [$p1] 拉取失败，尝试下一节点…\e[0m" >&2 ;;
            net_pull_all_fail) echo -e "\e[1;31m[✗] 所有镜像节点均拉取失败。请检查网络。\e[0m\n" >&2 ;;
            net_download_asset) echo -e "\e[1;34m:: 下载资源 ($p1/$p2)…\e[0m" ;;
            net_download_ok) echo -e "\e[1;32m[✓] 成功 (HTTP 200, ${p1}ms)\e[0m" ;;
            net_download_node_ok) echo -e "\e[1;32m[✓] 已通过 [$p1] 拉取\e[0m\n" ;;
            net_download_fail) echo -e "\e[1;31m[✗] 失败 (HTTP ${p1})\e[0m" ;;
            net_download_all_fail) echo -e "\e[1;31m[✗] 所有镜像节点均拉取失败\e[0m\n" ;;
            net_changelog_title) echo -e "最新更新日志" ;;
            err_mpvpaper_git_failed) echo -e "\e[1;31m[✗] mpvpaper-git 安装失败\e[0m" ;;
            log_keep_custom_file) echo -e "  \e[1;32m[✓]\e[0m 保留自定义文件: ~/.config/$p1" ;;
            log_keep_custom_dir) echo -e "  \e[1;32m[✓]\e[0m 保留自定义目录: ~/.config/$p1" ;;
            log_keep_monitor_config) echo -e "  \e[1;32m[✓]\e[0m 保留显示器配置: ~/.config/$p1/$p2" ;;
            log_deploy_config_item) echo -e "  \e[1;32m[✓]\e[0m 部署配置: ~/.config/$p1" ;;
            log_nvidia_gpu_detected) echo -e ":: 检测到 NVIDIA 显卡，已启用相应环境变量" ;;
            log_nvidia_gpu_not_detected) echo -e ":: 未发现 NVIDIA GPU (保持默认)" ;;
            log_gtk_theme_init) echo -e "  \e[1;32m[✓]\e[0m 初始化主题与 GTK 同步" ;;
            log_enable_mpvpaper) echo -e ":: 启用 mpvpaper 插件" ;;
            log_check_fisher) echo -e "\e[1;34m:: 检查 Fisher…\e[0m" ;;
            log_install_fish_plugins) echo -e ":: 安装 fish_plugins 插件…" ;;
            log_fisher_update_skipped) echo -e "[!] Fisher 更新跳过 (网络受限)" ;;
            log_fisher_install_skipped) echo -e "[!] Fisher 安装跳过 (网络受限)" ;;
            log_sync_wallpapers) echo -e "  \e[1;32m[✓]\e[0m 同步壁纸库: $p1" ;;
            log_no_components_selected) echo -e "未选择任何组件" ;;
            log_config_deploy_skipped) echo -e "已跳过配置部署" ;;
            log_backup_item) echo -e "  \e[1;32m[✓]\e[0m 已备份: ~/.config/$p1" ;;
            log_restore_item) echo -e "  \e[1;32m[✓]\e[0m 已恢复: ~/.config/$p1" ;;
            log_remove_item) echo -e "  \e[1;31m[✗]\e[0m 已移除: ~/.config/$p1" ;;
            log_restoring_origin_config) echo -e ":: 正在恢复初始配置: $p1…" ;;
            log_uninstall_cancelled) echo -e "已取消卸载" ;;
            log_fcitx_template_missing) echo -e "  \e[1;33m[!]\e[0m 仓库缺失主题模板源码: $p1" ;;
            log_fcitx_template_unregistered) echo -e "  \e[1;31m[✗]\e[0m $p1 模板注册已移除" ;;
            log_fcitx_theme_dir_removed) echo -e "  \e[1;31m[✗]\e[0m 已删除主题目录: $p1" ;;
            log_official_pkgs_partial_fail) echo -e "\e[1;31m[!]\e[0m 部分官方源软件包安装失败，继续后续步骤…" ;;
            log_aur_pkgs_partial_fail) echo -e "\e[1;31m[!]\e[0m 部分 AUR 软件包安装失败，继续后续步骤…" ;;
            preflight_sudo_prompt) echo -e "\n\e[1;34m:: 正在提权，请输入 sudo 密码：\e[0m" ;;
        esac
    else
        case "$key" in
            lang_select) echo -e "\n\e[1;36m:: Select Language / 请选择语言:\e[0m" ;;
            installed) echo -e "\e[1;32m[Installed]\e[0m" ;;
            missing) echo -e "\e[1;31m[Missing]\e[0m" ;;

            # Main Menu
            menu_title) echo -e "\n  \e[1;36m── $PROJECT_NAME Control Panel ──\e[0m\n" ;;
            menu_group_deploy) echo -e "  \e[1;34mDeployment & Setup\e[0m" ;;
            menu_opt1) echo -e "Deploy Components (Configs / Wallpapers / Modules)" ;;
            menu_opt2) echo -e "Check & Install Dependencies" ;;
            menu_group_maint) echo -e "\n  \e[1;34mMaintenance\e[0m" ;;
            menu_group_system) echo -e "\n  \e[1;34mSystem\e[0m" ;;
            menu_opt3) echo -e "Snapshot Management" ;;
            menu_opt4) echo -e "Check Updates & Overwrite" ;;
            menu_opt5) echo -e "System Doctor Diagnostics" ;;
            menu_opt6) echo -e "Export Diagnostic Report (Bug Report)" ;;
            menu_opt7) echo -e "Uninstall & Restore" ;;
            menu_opt8) echo -e "Optional Modules (Greeter / fcitx5 / Purge)" ;;
            menu_opt0) echo -e "Exit" ;;

            # Snapshot Management Submenu
            snapshot_menu_title) echo -e "\n  \e[1;36m── Snapshot Management ──\e[0m\n" ;;
            snapshot_sub_create) echo -e "Create Snapshot" ;;
            snapshot_sub_list) echo -e "List Snapshots" ;;
            snapshot_sub_delete) echo -e "Delete Snapshot" ;;
            snapshot_sub_rollback) echo -e "Rollback Snapshot" ;;
            snapshot_sub_back) echo -e "Back to Main Menu" ;;

            # Optional Modules Submenu
            optmod_menu_title) echo -e "\n  \e[1;36m── Optional Modules ──\e[0m\n" ;;
            optmod_purge) echo -e "Deep Purge (configs / snapshots / cache / wallpapers)" ;;
            optmod_back) echo -e "Back to Main Menu" ;;

            # Greeter Submenu
            greeter_menu_title) echo -e "\n  \e[1;36m── Noctalia Greeter ──\e[0m\n" ;;
            greeter_sub_install) echo -e "Install & Configure" ;;
            greeter_sub_status) echo -e "Show Status" ;;
            greeter_sub_uninstall) echo -e "Uninstall Config" ;;
            greeter_sub_back) echo -e "Back" ;;

            # Fcitx Submenu
            fcitx_menu_title) echo -e "\n  \e[1;36m── NyxMellow fcitx5 Skin ──\e[0m\n" ;;
            fcitx_sub_install) echo -e "Install Skin" ;;
            fcitx_sub_status) echo -e "Show Status" ;;
            fcitx_sub_uninstall) echo -e "Uninstall Skin" ;;
            fcitx_sub_back) echo -e "Back" ;;

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
            msg_downloading_wallpapers) echo -e "\n\e[1;34m:: Downloading wallpapers…\e[0m" ;;
            msg_downloading_wallpapers_node) echo -e "  [$p1] Pulling from [$p2]…" ;;
            msg_wallpapers_download_success) echo -e "\e[1;32m[✓] Wallpapers deployed\e[0m" ;;
            msg_wallpapers_download_failed) echo -e "\e[1;31m[✗] Download failed (skipped)\e[0m" ;;

            # Install Flow
            fcitx_skipped_not_installed) echo -e "\e[1;33m[!] fcitx5 not detected; skin activation skipped. Run: nyxniri fcitx install\e[0m" ;;
            install_cancelled) echo -e "\e[1;34mInstallation cancelled\e[0m" ;;
            install_step_configs) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Deploying configs…\e[0m" ;;
            install_step_wallpapers) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Syncing wallpapers…\e[0m" ;;
            install_step_deps) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Checking dependencies…\e[0m" ;;
            install_step_fcitx) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Configuring fcitx5 skin…\e[0m" ;;
            install_step_greeter) echo -e "\n\e[1;34m:: [\e[1;36m$p1\e[0m] Configuring Noctalia Greeter…\e[0m" ;;
            install_summary_title) echo -e "Deployment Complete" ;;
            summary_title_install) echo -e "Deployment Complete" ;;
            summary_title_update) echo -e "Update Complete" ;;
            summary_title_test) echo -e "Test Deployment Complete" ;;
            summary_section_details) echo -e "Deployment Details" ;;
            summary_item_configs_ok) echo -e "Core Config:    Deployment Succeeded ($p1)" ;;
            summary_item_configs_skip) echo -e "Core Config:    Skipped" ;;
            summary_item_wallpapers_ok) echo -e "Wallpapers:     Synced" ;;
            summary_item_wallpapers_skip) echo -e "Wallpapers:     Skipped" ;;
            summary_item_fcitx_ok) echo -e "Input Method:   NyxMellow fcitx5 skin" ;;
            summary_item_fcitx_skip) echo -e "Input Method:   Skipped" ;;
            summary_item_deps_ok) echo -e "System Deps:    Environment Ready" ;;
            summary_item_deps_skip) echo -e "System Deps:    Incomplete" ;;
            summary_item_greeter_ok) echo -e "Greeter:        Noctalia Greeter" ;;
            summary_item_greeter_skip) echo -e "Greeter:        Skipped" ;;
            summary_section_preserved) echo -e "Preserved Configurations (Auto-inherited)" ;;
            summary_section_next) echo -e "Next Steps" ;;
            summary_next_start) echo -e "Start Desktop : Run niri-session" ;;
            summary_next_manual) echo -e "Quick Manual  : Run nyxhelp" ;;
            summary_next_panel) echo -e "Control Panel : Run nyxniri" ;;

            # Test Deploy
            test_start) echo -e "\n\e[1;34m:: [test] Idempotent test deploy (skipped backup & deps)…\e[0m" ;;
            test_done) echo -e "\n\e[1;32m[✓] Test deploy complete\e[0m" ;;

            menu_hint) echo -e "\n  \e[90m[↑/↓/j/k] Move  [Enter/Space] Select  [0/q] Exit\e[0m" ;;
            submenu_hint) echo -e "\n  \e[90m[↑/↓/j/k] Move  [Enter/Space] Select  [0/q] Back\e[0m" ;;
            menu_prompt) echo -e "\n▸ Select option [0-9]: " ;;
            invalid_opt) echo -e "\e[1;31m[✗] Invalid option\e[0m" ;;
            press_any_key) echo -e "\nPress any key to continue…" ;;
            generating_report) echo -e "\n\e[1;34m:: Collecting diagnostic data…\e[0m" ;;
            report_done) echo -e "\e[1;32m[✓] Bug Report exported to:\e[0m $p1\n\e[1;36mHint: Please attach this file when opening an issue\e[0m\n\e[90mQQ Group: 631425889 | Telegram: @Echoes678\e[0m" ;;

            # Optional Overwrite Upgrade Strings
            overwrite_title) echo -e "\n  \e[1;36m── NyxNiri Config Update ──\e[0m\n" ;;
            overwrite_opt1) echo -e "Overwrite / Update Components" ;;
            overwrite_opt2) echo -e "View Config Diff" ;;
            overwrite_opt3) echo -e "Code Update Only" ;;
            selective_hint) echo -e "  \e[90m[↑/↓/j/k] Move  [Space] Toggle  [a] All  [n] None  [Enter] Confirm\e[0m" ;;
            upgrading_selected) echo -e "\n\e[1;34m:: Applying selected components…\e[0m" ;;
            overwrite_done) echo -e "\e[1;32m[✓] Selected components deployed\e[0m" ;;
            
            # Master Component Menu
            master_menu_title) echo -e "\n  \e[1;36m── Deployment Checklist ──\e[0m\n" ;;
            master_item_config) echo -e "Core Config: $p1" ;;
            master_item_module) echo -e "Optional Module: $p1" ;;
            master_item_asset) echo -e "Heavy Asset: $p1" ;;
            master_item_behavior) echo -e "\n  ── Deployment Behaviors ──" ;;
            master_item_backup) echo -e "Auto-create safe snapshot before deploy" ;;
            master_item_monitor) echo -e "Keep existing monitor hardware config (monitor.kdl)" ;;
            diff_viewer_title) echo -e "\n\e[1;36m:: Configuration Diff (Press \'q\' to quit)\e[0m" ;;

            # Uninstall Strings
            uninstall_title) echo -e "\n  \e[1;31m── NyxNiri Uninstall & Environment Restoration ──\e[0m\n" ;;
            uninstall_opt1) echo -e "  \e[1;32m1)\e[0m Standard Uninstall (Archive configs, remove CLI)" ;;
            uninstall_opt2) echo -e "  \e[1;36m2)\e[0m Restore to Original State" ;;
            uninstall_opt3) echo -e "  \e[1;31m3)\e[0m Deep Purge (Remove configs, snapshots, cache & wallpapers)" ;;
            uninstall_opt4) echo -e "  \e[90m4)\e[0m Cancel" ;;
            uninstall_prompt) echo -e "▸ Select uninstall mode [1-4]: " ;;
            uninstall_archived) echo -e "\e[1;32m[✓] Configs archived to:\e[0m $p1" ;;
            uninstall_done) echo -e "\e[1;32m[✓] Uninstall complete\e[0m" ;;
            purge_done) echo -e "\e[1;32m[✓] Deep purge complete\e[0m" ;;
            restore_origin_done) echo -e "\e[1;32m[✓] Restored system to original state\e[0m" ;;

            # Rollback Strings
            no_backups_found) echo -e "\e[1;33m[!] No configuration snapshots found\e[0m" ;;
            available_backups) echo -e "\n\e[1;36m:: Available NyxNiri Snapshots\e[0m" ;;
            select_rollback_target) echo -e "▸ Select snapshot to restore (Ctrl+C to cancel): " ;;
            rollback_invalid_num) echo -e "\e[1;31m[✗] Invalid selection\e[0m" ;;
            rolling_back) echo -e "\n\e[1;34m:: Restoring from snapshot [$p1]…\e[0m" ;;
            pre_rollback_backup) echo -e "\e[90m[✓] Auto-saved pre-rollback snapshot: $p1\e[0m" ;;
            rollback_done) echo -e "\e[1;32m[✓] Restored to snapshot: $p1\e[0m" ;;
            snapshot_note_prompt) echo -e "▸ Enter snapshot note (press Enter to skip): " ;;

            # Snapshot Delete Strings
            delete_confirm) echo -e "\n\e[1;31m[!] Will delete snapshot: $p1\e[0m" ;;
            delete_prompt) echo -e "▸ Confirm deletion? [y/N]: " ;;
            delete_cancelled) echo -e "\e[1;34mDeletion cancelled\e[0m" ;;
            delete_done) echo -e "\e[1;32m[✓] Deleted snapshot [$p1], $p2 snapshot(s) remaining\e[0m" ;;
            delete_invalid_num) echo -e "\e[1;31m[✗] Invalid selection\e[0m" ;;

            # Dependency Menu
            dep_menu_title) echo -e "\n  \e[1;36m── Dependency Selection ──\e[0m\n" ;;
            dep_menu_hint) echo -e "  \e[90m[↑/↓/j/k] Move  [Space] Toggle  [a] All  [n] None  [Enter] Install\e[0m" ;;
            copy_done) echo -e "\e[1;32mConfigurations deployed\e[0m" ;;

            # Optional Greeter Module
            greeter_install_title) echo -e "\n\e[1;35m[ Optional Module ] Noctalia Greeter\e[0m" ;;
            greeter_install_pkgs) echo -e "\n\e[1;34m:: Installing greetd & noctalia-greeter…\e[0m" ;;
            greeter_aur_required) echo -e "\e[1;33m[!] noctalia-greeter (AUR) requires paru/yay. Install an AUR helper first.\e[0m" ;;
            greeter_pkg_failed) echo -e "\e[1;31m[!] Failed to install $p1; continuing…\e[0m" ;;
            greeter_install_failed) echo -e "\e[1;31m[!] Install failed. Retry later with: nyxniri greeter install\e[0m" ;;
            greeter_install_skipped) echo -e "\e[1;33m[!] Noctalia Greeter setup skipped\e[0m" ;;
            greeter_dm_conflict) echo -e "\e[1;33m[!] Conflicting display manager detected ($p1). Please disable it manually.\e[0m" ;;
            greeter_config_written) echo -e "\e[1;32m[✓] greetd config written: $p1 (previous config backed up)\e[0m" ;;
            greeter_config_failed) echo -e "\e[1;31m[!] Failed to write greetd config: $p1 (requires sudo)\e[0m" ;;
            greeter_state_dir_created) echo -e "\e[1;32m[✓] Created state dir /var/lib/noctalia-greeter\e[0m" ;;
            greeter_cmd_failed) echo -e "\e[1;31m[!] Privileged command failed: $p1 (requires sudo)\e[0m" ;;
            greeter_polkit_skip) echo -e "\e[1;32m[✓] polkit rule already present; skipped\e[0m" ;;
            greeter_polkit_written) echo -e "\e[1;32m[✓] polkit rule written: $p1\e[0m" ;;
            greeter_polkit_failed) echo -e "\e[1;31m[!] Failed to write polkit rule\e[0m" ;;
            greeter_enabled) echo -e "\e[1;32m[✓] greetd service enabled (takes effect after reboot)\e[0m" ;;
            greeter_enabled_skip) echo -e "\e[1;32m[✓] greetd service already enabled\e[0m" ;;
            greeter_enable_failed) echo -e "\e[1;31m[!] Failed to enable greetd. Run manually: sudo systemctl enable greetd\e[0m" ;;
            greeter_reboot_hint) echo -e "\e[1;36mHint: Active after reboot. Sync theme via Noctalia Settings → Security → Noctalia Greeter → Sync Now.\e[0m" ;;
            greeter_status_title) echo -e "\n\e[1;36m:: Noctalia Greeter status\e[0m" ;;
            greeter_status_ok) echo -e "\e[1;32m[✓] Greeter ready\e[0m" ;;
            greeter_status_hint) echo -e "\e[1;36mHint: Run nyxniri greeter install to set up.\e[0m" ;;
            greeter_uninstall_title) echo -e "\n\e[1;33m:: Noctalia Greeter uninstall (keeps packages)\e[0m" ;;
            greeter_uninstall_restored) echo -e "\e[1;32m[✓] Restored greetd config: $p1\e[0m" ;;
            greeter_uninstall_nobackup) echo -e "\e[1;33m[!] No greetd backup found; kept current config\e[0m" ;;
            greeter_uninstall_polkit) echo -e "\e[1;32m[✓] polkit rule removed\e[0m" ;;
            greeter_uninstall_done) echo -e "\e[1;32m[✓] Greeter uninstalled. To remove packages: paru -R noctalia-greeter greetd\e[0m" ;;

            # Optional Fcitx5 Dynamic Theme Module
            fcitx_install_title) echo -e "\n\e[1;35m[ Optional Module ] NyxMellow fcitx5 skin\e[0m" ;;
            fcitx_skip_no_fcitx5) echo -e "\e[1;33m[!] fcitx5 not detected; skipped skin activation (theme templates deployed; run nyxniri fcitx install after installing fcitx5).\e[0m" ;;
            fcitx_templates_deployed) echo -e "\e[1;32m[✓] Theme templates deployed: ~/.local/share/fcitx5/themes/nyxmellow/templates/\e[0m" ;;
            fcitx_render_ok) echo -e "\e[1;32m[✓] Noctalia rendered skin with current theme\e[0m" ;;
            fcitx_render_pending) echo -e "\e[1;33m[!] noctalia not running; templates will apply on next theme change\e[0m" ;;
            fcitx_theme_set) echo -e "\e[1;32m[✓] fcitx5 switched to theme: nyxmellow ($p1)\e[0m" ;;
            fcitx_restarted) echo -e "\e[1;32m[✓] fcitx5 restarted\e[0m" ;;
            fcitx_status_title) echo -e "\n\e[1;36m:: NyxMellow dynamic fcitx5 skin status\e[0m" ;;
            fcitx_uninstall_title) echo -e "\n\e[1;33m:: NyxMellow dynamic fcitx5 skin uninstall\e[0m" ;;
            fcitx_uninstall_done) echo -e "\e[1;32m[✓] NyxMellow skin uninstalled; fcitx5 theme reverted\e[0m" ;;
            fcitx_registered) echo -e "\e[1;32m[✓] Noctalia templates registered ($p1)\e[0m" ;;
            fcitx_not_registered) echo -e "\e[1;33m[!] Noctalia templates not registered ($p1)\e[0m" ;;

            # System Doctor
            running_doctor) echo -e "\n\e[1;35mRunning System Doctor…\e[0m" ;;
            doctor_ok) echo -e "\e[1;32m[✓]\e[0m $p1" ;;
            doctor_warn) echo -e "\e[1;33m[!]\e[0m $p1" ;;
            doctor_err) echo -e "\e[1;31m[✗]\e[0m $p1" ;;
            all_done) echo -e "\n\e[1;32m[✓] Deployment & diagnostics complete\e[0m" ;;
            reboot_hint) echo -e "\e[1;36mHint: Restart Noctalia or reload Niri for settings to take effect\e[0m" ;;

            # Standalone & Update Strings
            git_required) echo -e "\e[1;31m[✗] git is missing. Please install it first.\e[0m" ;;
            cloning_repo) echo -e "\n\e[1;34m:: Pulling repository to cache ($CACHE_DIR)…\e[0m" ;;
            checking_updates) echo -e "\n\e[1;34m:: Checking for updates…\e[0m" ;;
            updating_done) echo -e "\e[1;32m[✓] Update complete. Restarting…\e[0m" ;;
            updating_failed) echo -e "\e[1;31m[✗] Update failed (check network and git status)\e[0m" ;;
            dirty_tree_warn) echo -e "\e[1;33m[!] Uncommitted local changes detected in $p1.\e[0m" ;;
            dirty_tree_confirm) echo -e ":: Continuing will discard these changes. Continue? [y/N]: " ;;
            update_cancelled_dirty) echo -e "\e[1;34mUpdate cancelled; local changes preserved.\e[0m" ;;
            update_skipped_dev_repo) echo -e "\n\e[1;33m[!] Local repo ($p1) has uncommitted changes or diverged.\e[0m\n\e[1;36mSkipped source update; config deployment is unaffected.\e[0m\n" ;;

            # AUR & mpvpaper
            aur_skip) echo -e "\e[1;33m[!] AUR packages ($p1) require paru/yay; skipped.\e[0m" ;;
            aur_helper_required) echo -e "\e[1;33m    Install paru or yay first, then retry.\e[0m" ;;
            aur_bootstrap_start) echo -e "\n\e[1;34m:: Setting up paru…\e[0m" ;;
            aur_bootstrap_cleanup) echo -e ":: Removing stale paru-bin packages…\e[0m" ;;
            aur_bootstrap_repo) echo -e ":: Installing paru from official repos…\e[0m" ;;
            aur_bootstrap_source) echo -e ":: Building paru from source (~1-3 min)…\e[0m" ;;
            aur_bootstrap_ok) echo -e "\e[1;32m[✓] paru installed successfully\e[0m" ;;
            aur_bootstrap_failed) echo -e "\e[1;31m[!] paru bootstrap failed; skipped AUR packages. Install manually and retry.\e[0m" ;;
            aur_bootstrap_skip) echo -e "\e[1;33m[!] Auto-install of paru cancelled; skipped AUR packages\e[0m" ;;
            checking_mpvpaper) echo -e "\n\e[1;34m:: Checking mpvpaper version…\e[0m" ;;
            mpvpaper_version_ok) echo -e "\e[1;32m[✓]\e[0m mpvpaper $p1 >= 1.9, no known memory leak" ;;
            mpvpaper_leak_warn) echo -e "\e[1;33m[!]\e[0m mpvpaper $p1 has an OpenGL memory leak. Upgrade to 1.9+ or install mpvpaper-git\n   (See: https://github.com/GhostNaN/mpvpaper/issues/127)" ;;
            mpvpaper_upgrade_done) echo -e "\e[1;32m[✓] mpvpaper-git installed\e[0m" ;;
            mpvpaper_upgrade_skip) echo -e "Manual upgrade: paru -S mpvpaper-git or yay -S mpvpaper-git" ;;

            # Alerts / Prompts
            preflight_express_summary) echo -e "\n\e[1;34m:: Preparing to install:\e[0m" ;;
            installing_selected) echo -e "\n\e[1;34m:: Installing selected dependencies…\e[0m" ;;
            backing_up) echo -e "\n\e[1;34m:: Creating configuration snapshot…\e[0m" ;;
            backup_done) echo -e "\e[1;32m[✓] Snapshot created: $p1\e[0m" ;;
            copying_configs) echo -e "\n\e[1;34m:: Deploying configurations…\e[0m" ;;

            # Log & Internal Engine Strings
            # Core, Main, Network & Preflight Strings
            preflight_comp_config) echo -e "  \e[1;36m- Core Config:\e[0m $p1 items" ;;
            preflight_comp_assets) echo -e "  \e[1;36m- Heavy Asset:\e[0m Full Wallpaper Pack" ;;
            preflight_comp_module_fcitx) echo -e "  \e[1;36m- Optional Module:\e[0m $p1 fcitx5 Skin" ;;
            preflight_comp_module_greeter) echo -e "  \e[1;36m- Optional Module:\e[0m $p1" ;;
            preflight_comp_deps) echo -e "  \e[1;36m- Dependencies:\e[0m Check & Install missing dependencies" ;;
            preflight_custom_config_kept) echo -e "\e[1;36m[ Preserved custom configurations ]\e[0m" ;;
            err_sudo_aborted) echo -e "\n\e[1;31m[✗] Administrator privileges required. Aborted.\e[0m" ;;
            err_aborted_code) echo -e "\n\e[1;31m[✗] Aborted with exit code: $p1\e[0m" ;;
            err_already_running) echo -e "\n\e[1;33m[!] Process already running (PID: $p1)\e[0m" ;;
            err_root_denied) echo -e "\n\e[1;31m[✗] Running as root is denied. Please run as a normal user.\e[0m" ;;
            net_pull_repo) echo -e "\e[1;34m:: Pulling repository (Official -> gh-proxy)…\e[0m" >&2 ;;
            net_pull_node) echo -e "\n  \e[1;36m[$p1/$p2] Pulling from [$p3]…\e[0m" >&2 ;;
            net_pull_node_ok) echo -e "\e[1;32m[✓] Pulled from [$p1]\e[0m\n" >&2 ;;
            net_pull_node_fail) echo -e "\e[1;31m[!] Pull from [$p1] failed, trying next…\e[0m" >&2 ;;
            net_pull_all_fail) echo -e "\e[1;31m[✗] All mirror nodes failed. Please check network.\e[0m\n" >&2 ;;
            net_download_asset) echo -e "\e[1;34m:: Downloading asset ($p1/$p2)…\e[0m" ;;
            net_download_ok) echo -e "\e[1;32m[✓] Success (HTTP 200, ${p1}ms)\e[0m" ;;
            net_download_node_ok) echo -e "\e[1;32m[✓] Downloaded via [$p1]\e[0m\n" ;;
            net_download_fail) echo -e "\e[1;31m[✗] Failed (HTTP ${p1})\e[0m" ;;
            net_download_all_fail) echo -e "\e[1;31m[✗] All mirror nodes failed\e[0m\n" ;;
            net_changelog_title) echo -e "Latest Changelog" ;;
            err_mpvpaper_git_failed) echo -e "\e[1;31m[✗] Failed to install mpvpaper-git\e[0m" ;;
            log_keep_custom_file) echo -e "  \e[1;32m[✓]\e[0m Preserved custom file: ~/.config/$p1" ;;
            log_keep_custom_dir) echo -e "  \e[1;32m[✓]\e[0m Preserved custom dir: ~/.config/$p1" ;;
            log_keep_monitor_config) echo -e "  \e[1;32m[✓]\e[0m Preserved monitor config: ~/.config/$p1/$p2" ;;
            log_deploy_config_item) echo -e "  \e[1;32m[✓]\e[0m Deployed config: ~/.config/$p1" ;;
            log_nvidia_gpu_detected) echo -e ":: NVIDIA GPU detected (env enabled)" ;;
            log_nvidia_gpu_not_detected) echo -e ":: No NVIDIA GPU detected (kept default env)" ;;
            log_gtk_theme_init) echo -e "  \e[1;32m[✓]\e[0m Initializing theme & GTK sync" ;;
            log_enable_mpvpaper) echo -e ":: Enabling mpvpaper plugin" ;;
            log_check_fisher) echo -e "\e[1;34m:: Checking Fisher…\e[0m" ;;
            log_install_fish_plugins) echo -e ":: Installing fish_plugins…" ;;
            log_fisher_update_skipped) echo -e "[!] Fisher update skipped (network restricted)" ;;
            log_fisher_install_skipped) echo -e "[!] Fisher install skipped (network restricted)" ;;
            log_sync_wallpapers) echo -e "  \e[1;32m[✓]\e[0m Syncing wallpapers: $p1" ;;
            log_no_components_selected) echo -e "No components selected" ;;
            log_config_deploy_skipped) echo -e "Config deployment skipped" ;;
            log_backup_item) echo -e "  \e[1;32m[✓]\e[0m Backed up: ~/.config/$p1" ;;
            log_restore_item) echo -e "  \e[1;32m[✓]\e[0m Restored: ~/.config/$p1" ;;
            log_remove_item) echo -e "  \e[1;31m[✗]\e[0m Removed: ~/.config/$p1" ;;
            log_restoring_origin_config) echo -e ":: Restoring initial backup: $p1…" ;;
            log_uninstall_cancelled) echo -e "Uninstall cancelled" ;;
            log_fcitx_template_missing) echo -e "  \e[1;33m[!]\e[0m Theme template source missing: $p1" ;;
            log_fcitx_template_unregistered) echo -e "  \e[1;31m[✗]\e[0m $p1 template registration removed" ;;
            log_fcitx_theme_dir_removed) echo -e "  \e[1;31m[✗]\e[0m Removed theme dir: $p1" ;;
            log_official_pkgs_partial_fail) echo -e "\e[1;31m[!]\e[0m Some official packages failed to install; continuing…" ;;
            log_aur_pkgs_partial_fail) echo -e "\e[1;31m[!]\e[0m Some AUR packages failed to install; continuing…" ;;
            preflight_sudo_prompt) echo -e "\n\e[1;34m:: Privilege escalation required. Enter sudo password:\e[0m" ;;
        esac
    fi
}

select_language() {
    local focus=1
    clear 2>/dev/null || true

    while true; do
        printf '\e[?25l\e[H'
        show_logo
        echo -e "  \e[1;36m── 请选择语言 / Select Language ──\e[0m\n"
        if [ "$focus" -eq 0 ]; then
            echo -e "  \e[1;36m❯ \e[1;37mEnglish\e[0m"
            echo -e "    \e[90m简体中文 (Simplified Chinese)\e[0m"
        else
            echo -e "    \e[90mEnglish\e[0m"
            echo -e "  \e[1;36m❯ \e[1;37m简体中文 (Simplified Chinese)\e[0m"
        fi
        echo ""
        echo -e "  \e[90m[↑/↓/j/k] Move  [Enter/Space] Select\e[0m"
        printf '\e[J'

        if [ ! -t 0 ] || [ ! -c /dev/tty ]; then
            LANG_MODE="zh"
            break
        fi

        local key
        key=$(read_key) || break

        case "$key" in
            UP|[kK]|LEFT)
                focus=0
                ;;
            DOWN|[jJ]|RIGHT)
                focus=1
                ;;
            1)
                focus=0
                ;;
            2)
                focus=1
                ;;
            ENTER|SPACE)
                if [ "$focus" -eq 0 ]; then
                    LANG_MODE="en"
                else
                    LANG_MODE="zh"
                fi
                break
                ;;
        esac
    done
    printf '\e[?25h'
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
