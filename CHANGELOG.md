# Changelog

## [v2.1.7] - 2026-07-26 (进行中)

### Fixed / Hardened

- **护眼模式 (Mod+N) 部署后状态颠倒错位修复**: `toggle-eyecare.sh` 不再依赖会被"部署配置"清空重置的 `.eyecare_state` 状态文件，改为直接以 `wlsunset` 进程是否存活作为唯一事实来源判断当前护眼状态，彻底解决部署后色温与窗口透明度/Blur 状态脱同步、切换键表现"颠倒"的问题；新增 `--sync` 校准模式并接入 `config.kdl` 的 `spawn-at-startup`，niri 重启后可自愈对齐。
- **install.sh 部署原子化**: 新增 `atomic_replace_dir()`，部署/回滚前先复制到临时目录、确认成功后才 `rm+mv` 换上去，避免中断（Ctrl+C / 断电 / 磁盘满）导致配置目录只删不建、直接丢失；顺手删除了从未被调用的死代码 `copy_config_items()`。
- **install.sh 清理陷阱死代码修复**: 原 `TEMP_WORKDIR` 声明后从未被实际赋值，中断清理 trap 形同虚设；改为 `CLEANUP_TEMP_PATHS` 注册表，所有临时文件/目录均能在退出时被正确回收。
- **install.sh 备份列表空格拆分 bug**: `get_all_backups` 原先靠 `echo "${arr[@]}"` 与 `read -a` 字符串往返传递，路径含空格时会被错误拆分，可能导致回滚指向错误快照；改为直接填充全局数组。
- **install.sh 自更新安全性**: 统一改用脚本自解析的 `REAL_SCRIPT_PATH` 而非裸 `$BASH_SOURCE` 定位并覆盖自身；下载的新版本脚本先落地临时文件、`bash -n` 语法校验通过后才原子替换真身，避免网络中断导致执行到半截的脚本被直接运行；`git reset --hard` 前检测工作区是否存在未提交改动并交互确认，不再静默丢弃本地修改；连接 GitHub 失败切换国内镜像时，交互场景下会先征求用户确认。

### Added

- **`clean-cache` 智能化改造**: 用体积阈值（默认 50MB）动态扫描 `~/.cache` 取代逐个硬编码的 App 缓存白名单，新装软件无需改脚本即可被自动覆盖清理；新增 `-y/--yes/--auto` 非交互自动化模式，便于接入 cron/systemd timer；补充清理内核升级残留的孤立内核模块目录（`/usr/lib/modules/<旧版本>`）与 `systemd-coredump` 系统崩溃转储。
- **Fish 包搜索体验重做**: `se`/`un` 改为基于 `paru -Slq`/`pacman -Qq` 全量包名列表 + `fzf` 原生模糊匹配的交互式搜索安装/卸载，替代原先只能精确匹配包名、且完全不搜 AUR 的 `shelly query` 别名。

## [v2.1.6] - 2026-07-26

### Fixed / Hardened

- **NVIDIA 显卡 & 虚拟机黑屏致命修复**: 默认注释 `v2/niri/config.kdl` 中的 NVIDIA 专属环境变量（`GBM_BACKEND "nvidia-drm"` 等），彻底解决 Intel/AMD 显卡以及 VMware/VirtualBox/QEMU 虚拟机设备在启动 Niri Wayland 会话时渲染引擎崩溃黑屏且无法响应的硬伤。
- **GPU 硬件自动探测与开箱即用**: 在 `install.sh` 部署环节增加 `lspci` GPU 自动识别逻辑，仅在检测到设备确实包含 NVIDIA 独显时自动解注释 `config.kdl` 中的 NVIDIA 变量，实现全平台设备开箱即用。
- **root / sudo 账号误运行防护**: 在 `install.sh` 入口增加 `[ "$(id -u)" -eq 0 ]` 断言保护，严格阻止以 root 权限部署 dotfiles，防止配置文件写错至 `/root` 目录或发生 `root:root` 文件所有权错乱。
- **Fisher 在线获取网络超时防护**: 为 `install.sh` 中的 Fisher 插件获取补全 `--connect-timeout 5` 与错误捕获，避免无网络或 GitHub 连接中断时 `set -e` 导致脚本部署中途中断。
- **强自愈式锁释放 (Self-Healing Lock Release)**: 优化 `v2/niri/toggle-eyecare.sh` 前置清理逻辑，按 `Mod+N` 时会在 1 毫秒内强制解包 Noctalia 的 Wayland Gamma 协议锁，解决手动干预导致的色温状态混乱。

### Added

- **XDG 规范日志引擎 (install.log)**: 在 `install.sh` 中构建符合 `XDG_STATE_HOME` 规范的日志引擎（保存于 `~/.local/state/NyxNiri/install.log`），支持 ANSI 颜色转义符自动剥离、时间戳单行记录与自动截断滚动（限制 800 行 / <50KB），绝不污染用户 `$HOME` 家目录。
- **Bug Report 可观测性集成**: 在 `nyxniri bug-report` 导出的报告末尾自动附带 `install.log` 最新运行日志切片，大幅提升疑难杂症的诊断效率。
- **System Doctor 诊断强化**: 新增对 `wlsunset` 护眼模式平滑渐变组件的检查，以及虚拟机环境（VMware/VirtualBox/QEMU）下 “3D 硬件加速” 开启状态的诊断提醒。
- **审查方案与规范文档**: 在项目根目录新建《NyxNiri Dotfiles 审查方案与实战指南》（`审查方案.md`），总结防误判原则 (False-Positive Prevention Protocol)、5 步标准审查流程与经验心得，并配置 `.gitignore`。

### Changed / Refactored

- **Quickshell / iNiR 历史死代码清理**: 清理 `v2/fish/conf.d/inir-env.fish` 中的过时虚拟环境变量、`v2/fish/config.fish` 中的旧版终端颜色序列打印，以及 `v2/niri/config.kdl` 中残留的 `quickshell` 图层与窗口规则。
- **Kitty 主题配置去重**: 移除 `v2/kitty/kitty.conf` 顶部重复导入的 `include themes/matugen.conf` 引入项。

## [v2.1.5] - 2026-07-25

### Added

- **wlsunset 强劲色温引擎**: 在 `v2/niri/toggle-eyecare.sh` 中全盘接入原生 `wlsunset` 色温渲染引擎，实现物理级色温控制（5500K 微暖自然护眼）。
- **Noctalia v5 原生 OSD 联动**: 接入 Noctalia v5 内置原生的 Nightlight OSD 悬浮胶囊卡片，随快捷键触发行云流水显示“夜间模式：开启/关闭”并全效支持系统 i18n 国际化语言。

### Changed / Refactored

- **Noctalia 配置解耦**: 在 `v2/noctalia/noctalia-config.toml` 中显式设置 `[nightlight] enabled = false`，完全释放 Wayland Gamma 协议控制锁，消除系统内不同 Gamma 渲染器之间的死锁摩擦。
- **install.sh 截图路径优化**: 在 `install.sh` 配置部署环节新增自动动态替换 `niri/config.kdl` 中 `screenshot-path` 用户家目录逻辑。

### Fixed / Hardened

- **防显卡撕裂与无闪烁平滑过渡**: 为 `wlsunset` 引入 `-d 0.3` 渐变模式，并结合 50ms 显卡管线错峰重载（Pipeline Frame Separation），彻底解决了 `Mod+N` 触发时 Niri 窗口 Shader 与 GPU 色温控制硬碰撞导致的二次闪烁与视觉撕裂问题。
- **自愈式按键响应**: 解决夜间定时计划导致色温不响应的硬伤，确保不论昼夜或 UI 手动开关状态，按 `Mod+N` 均能 100% 稳定实现 UI 纯色/毛玻璃与色温双重同步对齐。

## [v2.1.4] - 2026-07-24

### Added

- **Niri 护眼模式 (Mod+N)**: 新增 `v2/niri/effects_normal.kdl` 与 `v2/niri/effects_eyecare.kdl` 视觉样式模板；按 `Mod+N` 开启护眼模式时自动将色温调暖，禁用毛玻璃 Blur 效果并将窗口透明度拉满至 100% 纯不透明（消除眩光与背景杂乱透出）
- **零常驻后台脚本**: 新增 `v2/niri/toggle-eyecare.sh` 极简单次触发脚本（运行时间 < 2ms 即刻退出，零内存常驻），引入昼夜上下文感知与确定性状态对齐（Self-Healing Sync），无缝联动 Noctalia 色温与 Niri 特效重载，彻底消除夜间快捷键反向错位问题
- **System Doctor 诊断**: 扩展脚本健康检查，新增对 `toggle-eyecare.sh` 快捷脚本的可执行权限自动检测与自愈修复

### Changed / Refactored

- **install.sh**: 抽象提炼全局 `CONFIG_ITEMS` 配置项数组与 `copy_config_items` 辅助函数，清除了快照、部署、回滚与卸载逻辑中的多处代码冗余
- **install.sh**: 优化后处理 `sed` 替换逻辑，使用通配正则确保无论模板源路径如何变化均能无缝映射至当前用户的 `$HOME` 与壁纸路径 `$wp_dest`
- **README.md**: 优化中英文双语排版，补充护眼模式 (Focus Mode) 快捷键与特性说明，并将演示视频全篇更新至最新链接 (`BV1Dig16rEZ7`)

### Fixed / Hardened

- **install.sh**: 为 `get_version` 等命令及管道查询添加 Safe Wrappers，消除无匹配项时 `set -e` 严格模式导致的脚本意外退出
- **theme-sync.sh**: 增加 INI 配置 key/val 的 `sed` 正则符号转义保护，并封装 `set_gsettings` 屏蔽非 GNOME 环境下的 stderr 告警
- **wallpaper-hook.sh**: 增加视频壁纸文件存在性与非空校验，防止无效路径引发 `ffmpeg` 报错
- **mpvpaper-sync.sh**: 增加 `jq` JSON 解析容错保护与 `SIGINT`/`SIGTERM` 信号清理陷阱
- **clean-cache**: 采用 Bash 数组安全的展开解析 Pacman 孤立包，防止孤立包列表为空或为空白字符时误传参数

## [v2.1.3] - 2026-07-23

### Added

- **install.sh**: 新增 `nyxniri snapshot [备注]` 与 `nyxniri rollback [序号]` 极简配置快照与一键回滚指令
- **install.sh**: 新增 `nyxniri uninstall` 分层安全卸载与原路复原功能，支持自动打包备份当前配置 `NyxNiri_final_backup_*.tar.gz` 并在需要时恢复最早期初始环境
- **install.sh**: 新增 `nyxniri purge` 参数，支持全套深度粉碎清理（配置、缓存、快照与壁纸）
- **install.sh**: 新增全局 `cleanup` 信号捕获句柄（`EXIT INT TERM`），防止异常或 `Ctrl+C` 中断留下残留
- **install.sh**: 在 Fish 终端 `custom_help` 中添加 `nyxniri` 快捷指令帮助说明

### Changed / Refactored

- **install.sh**: 优化快照落盘机制，统一归档至专用的 `~/.config/NyxNiri/backups/` 目录，并保持对旧版 `dotfiles_backup_*` 目录的无缝向下兼容
- **install.sh**: 移除硬编码版本号，引入 `get_version()` 自动优先解析 Git Tag（如 `v2.1.3`）与 CHANGELOG.md 标题
- **install.sh**: 运行模式中立化表述，准确标识 `Local Path` 与 `Remote Cache` 部署源
- **install.sh**: 增强软链接路径解析 `readlink -f`，解决全局调起 `nyxniri` 时的模式误判问题
- **install.sh**: 清理已失效的 `kkgithub` 镜像，更新为更稳定靠谱的国内镜像源（如 `ghproxy.net` / `bgithub.xyz`）

## [v2.1.2] - 2026-07-22

### Added

- **install.sh**: 新增一键生成 Bug Report 诊断日志功能（主菜单选项 6），导出完整的系统环境、显示器连线、软硬件版本及系统日志切片（`~/nyxniri-bug-report-*.md`）
- **install.sh**: 部署 `niri` 配置时新增 `monitor.kdl` 交互式保护，检测到已有配置时提示询问用户是否保留本地显示器布局
- **install.sh**: 新增自动注册并启用 Noctalia `mpvpaper` 插件逻辑
- **Noctalia 配置**: 默认开启 `mpvpaper` 插件、设置视频壁纸选择器浮动窗口、配置视频壁纸目录及 Bar 右侧控件
- **System Doctor**: 扩展组件诊断支持，涵盖 `swaylock` 锁屏、`wpctl` 音频、`ddcutil`/`brightnessctl` 亮度控制及 `xdg-desktop-portal` 服务状态
- **GitHub 社区与赞助**: 新增 GitHub 官方赞助配置文件 `.github/FUNDING.yml`（配置爱发电与 GitHub Sponsor）与 Issue 报告模板 `.github/ISSUE_TEMPLATE/bug_report.md`
- **README.md**: 补充社区交流群、开发者 QQ、Telegram (@Echoes678) 及其赞助支持板块，并同步了最新快捷键文档

### Changed / Refactored

- **Fastfetch**: 切换界面风格为 Catnap 圆角卡片风格 (Preset 13)
- **Niri 快捷键**: 优化动态壁纸选择器快捷键绑定为 `Mod+Shift+W` (静态壁纸维持 `Mod+W`)

### Fixed

- **install.sh**: 为 `fc-list` 增加 `command -v` 存在性保护，解决未安装 `fontconfig` 环境下 `set -e` 导致脚本意外中断退出
- **install.sh**: 增加 `xdg-user-dir PICTURES` 空值保底退守逻辑，防范图片路径拼接异常
- **install.sh**: 修正 Bug Report 导出中 `wpctl` 与 `mpvpaper` 版本信息提取，兼容非 `--version` 标志的二进制工具
- **mpvpaper-sync.sh**: 修改 `inotifywait` 为监听所在目录 `close_write,moved_to` 事件，解决应用原子写入导致 `inotify` 监听句柄丢失退出的问题
- **README.md**: 修复中英文组件一览表格表头缺失缺陷，补充 mpvpaper 引擎与壁纸快捷键说明

## [v2.1.1] - 2026-07-21

### Added

- **install.sh**: 更新成功后自动渲染 `CHANGELOG.md` 最新版本更新日志并暂停等待按键确认

### Fixed

- **Fish 配置**: `eza --icons` → `--icons=auto`，兼容新版 eza 参数校验
- **Fish 配置**: `set -gx PATH` → `fish_add_path -m`，避免重复追加 PATH
- **install.sh**: 依赖分为官方源/AUR 两类，纯 pacman 环境自动跳过 AUR 包并提示 (解决 Issue #1)
- **install.sh**: 使用 `LC_ALL=C` 解析 `pacman` 输出，消除系统 Locale 差异导致的检查失效
- **install.sh**: 规范化 `mpvpaper` 版本提取（剥离 Epoch/修订号），修复 Bash 算术比较抛错 (解决 Issue #2)
- **install.sh**: 优化 `mpvpaper-git` 检查与平滑升级流程，防止预先卸载造成软件包丢失
- **clean-cache**: 移除主脚本作用域内的 `local` 关键字，消除运行时 Bash 报错
- **mpvpaper-sync.sh**: 缩略图生成改用 PID 临时文件 + `mv` 原子替换，防止并发竞争写入损坏
- **Niri 配置**: 移除 auto-Niri.fish，修复 greetd 会话启动时的死循环
