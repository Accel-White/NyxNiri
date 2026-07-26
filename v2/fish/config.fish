if test -f /usr/share/cachyos-fish-config/cachyos-config.fish
    source /usr/share/cachyos-fish-config/cachyos-config.fish
end

# 代理配置 (Proxy Configuration) — 修改此处以适配你的代理端口
set -g PROXY_ADDR "127.0.0.1:7890"

# 开启代理
function proxy_on
    set -gx http_proxy "http://$PROXY_ADDR"
    set -gx https_proxy "http://$PROXY_ADDR"
    set -gx all_proxy "socks5://$PROXY_ADDR"
    echo "[+] 终端代理已开启 (Proxy: $PROXY_ADDR)"
end


# 关闭代理
function proxy_off
    set -e http_proxy
    set -e https_proxy
    set -e all_proxy
    echo "[-] 终端代理已关闭"
end

# 查看代理状态
function proxy_status
    echo "--- 代理环境变量 (Proxy Env) ---"
    for var in http_proxy https_proxy all_proxy
        if set -q $var
            echo "$var: "$$var
        else
            echo "$var: [未设置]"
        end
    end

    echo ""
    echo "--- 连通性测试 (Connectivity) ---"
    echo -n "测试 Google.com... "
    set -l start (date +%s%3N)
    set -l code (curl -I -s --connect-timeout 3 -o /dev/null -w "%{http_code}" https://www.google.com 2>/dev/null)
    set -l end (date +%s%3N)
    if test "$code" = "200" -o "$code" = "301" -o "$code" = "302"
        set -l duration (math $end - $start)
        echo "成功 (HTTP $code, $duration ms)"
    else
        echo "失败"
    end

    echo ""
    echo "--- IP 地理位置 (IP Location) ---"
    curl -s -m 3 cip.cc 2>/dev/null | head -n 3
end

function ask_agy
    proxy_on
    agy $argv
end

# Added by Antigravity CLI installer
fish_add_path -m "$HOME/.local/bin"

if status is-interactive
    # No greeting
    set fish_greeting

    # Tab 智能自动补全：优先采纳灰色历史建议，无建议时触发 Tab 列表补全
    function custom_tab_complete
        if commandline -f accept-autosuggestion
            # 成功采纳自动提示建议
        else
            commandline -f complete
        end
    end

    function fish_user_key_bindings
        # 绑定 Tab 键
        bind \t custom_tab_complete
    end

    # Use starship prompt
    if command -v starship &>/dev/null
        starship init fish | source
    end

    # Aliases
    alias clear "printf '\033[2J\033[3J\033[1;1H'" # fix: kitty doesn't clear scrollback properly
    alias celar "printf '\033[2J\033[3J\033[1;1H'"
    alias claer "printf '\033[2J\033[3J\033[1;1H'"
    
    # Shelly 统一包管理别名 (CachyOS 官方推荐)
    alias up='shelly upgrade-all'                 # 一键更新官方包、AUR、Flatpak、AppImage
    alias update='shelly upgrade-all'             # 同上，完整拼写
    alias in='shelly install'                     # 安装软件包 (支持官方源/AUR/Flatpak)
    alias clean='~/.config/fish/clean-cache'      # 运行一键缓存清理脚本

    # se：模糊搜索软件包 (官方源 + AUR) 并用 fzf 交互安装
    # paru -Slq 列出全部包名，模糊匹配交给 fzf 自己做，比 `shelly query` 的精确匹配好用得多
    function se --description "模糊搜索并安装软件包 (官方源 + AUR)"
        set -l pkgs (paru -Slq | fzf --multi --prompt='📦 安装 > ' \
            --preview 'paru -Si {1}' --preview-window 'right:60%:wrap')
        test -n "$pkgs"; and paru -S $pkgs
    end

    # un：模糊搜索已安装的包并用 fzf 交互卸载
    function un --description "模糊搜索并卸载已安装软件包"
        set -l pkgs (pacman -Qq | fzf --multi --prompt='🗑  卸载 > ' \
            --preview 'pacman -Qi {1}' --preview-window 'right:60%:wrap')
        test -n "$pkgs"; and paru -Rns $pkgs
    end
    
    # 自定义指令与别名总览说明 (Custom Commands & Aliases Help)
    function custom_help
        echo "=== 终端自定义快捷指令 (Custom Commands & Aliases) ==="
        echo ""
        echo "  --- NyxNiri 配置工具与快照恢复 (NyxNiri CLI & Snapshots) ---"
        echo "  nyxniri                    -> 打开 NyxNiri 桌面控制面板主菜单"
        echo "  nyxniri snapshot [备注]    -> 手动创建当前配置快照"
        echo "  nyxniri rollback [序号]    -> 恢复指定的历史配置快照"
        echo "  nyxniri list               -> 列出所有可用的配置快照"
        echo "  nyxniri uninstall          -> 安全卸载并复原系统配置环境"
        echo "  nyxniri doctor             -> 运行系统诊断检查"
        echo ""
        echo "  --- 代理控制 (Proxy Controls) ---"
        echo "  proxy_on       -> 开启终端代理 (Socks5/HTTP :7890)"
        echo "  proxy_off      -> 关闭终端代理"
        echo "  proxy_status   -> 检查代理连通性及公网 IP 位置"
        echo ""
        echo "  --- 包管理 (Package Management - Shelly) ---"
        echo "  up / update    -> shelly upgrade-all"
        echo "                    (一键更新官方包、AUR、Flatpak、AppImage)"
        echo "  se             -> 模糊搜索软件包 (官方源 + AUR)，fzf 交互选择安装"
        echo "                    Enter/Tab 多选，Esc 取消，右侧预览包详情"
        echo "  in <包名>      -> shelly install <包名>"
        echo "                    (安装软件包，支持官方/AUR/Flatpak)"
        echo "  un             -> 模糊搜索已安装的包，fzf 交互选择卸载"
        echo "  clean          -> ~/.config/fish/clean-cache"
        echo "                    (一键清理系统与用户缓存，动态扫描大缓存目录)"
        echo "  clean --auto   -> 跳过确认直接执行，适合接入 cron/systemd timer"
        echo ""
        echo "  --- 智能自动补全与模糊搜索 (Autocomplete & Fuzzy Search) ---"
        echo "  Tab            -> 优先采纳灰色历史建议，无建议时触发 Tab 列表补全"
        echo "  Ctrl + R       -> 模糊搜索历史命令 (fzf 历史记录)"
        echo "  Ctrl + Alt + F -> 模糊查找文件并插入路径 (fzf 文件)"
        echo "  Ctrl + Alt + L -> 模糊浏览 git commit 历史 (fzf Git Log)"
        echo "  Ctrl + Alt + S -> 模糊浏览 git status 状态 (fzf Git Status)"
        echo "  (提示: 括号和单双引号均已配置自动双向配对补全)"
        echo ""
        echo "提示: 可用 'custom_help'、'pkg_help' 或 'my_help' 触发此菜单。"
    end
    alias pkg_help='custom_help'
    alias my_help='custom_help'
    alias shelly_help='custom_help'
    
    if command -v eza &>/dev/null
        alias ls 'eza --icons=auto'
    end
    alias q 'qs -c ii'
end
