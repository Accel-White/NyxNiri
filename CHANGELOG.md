# Changelog

## [v2.2.1] - 2026-08-08

### Fixed

- **国际化字典死代码清理与全仓校验 (i18n Dictionary Dead Code Cleanup & Auditing)**:
  - 彻底审计并清理 `lib/i18n.sh` 中遗留的 14 组未使用文案键值（包含 `checking_dep`、`install_plan_*`、`summary_customs_header`、`greeter_noninteractive_skip`、`mirror_fallback_confirm` 等）。
  - 参照 `AGENTS.md` 铁律 0 完成全仓库静态依赖排查，确认 0 处外部引用，消除废弃文案残留，提升代码维护性。

## [v2.1.20] - 2026-08-07

### Fixed

- **JetBrains Mono 字体在全新系统未生效 (JetBrains Mono Font Not Applied on Clean Installs)**:
  - 依赖列表仅安装 `ttf-jetbrains-mono-nerd`，而其提供的家族名是 `JetBrainsMono Nerd Font`；`kitty.conf` / `zed/settings.json` / `noctalia-config.toml` 请求的家族名却是 `JetBrains Mono`（仅由 `ttf-jetbrains-mono` 提供），导致新机器部署后终端 / 编辑器回退到默认字体。
  - 根因经全仓库排查（AGENTS.md 铁律 0）确认：修复前用宽泛关键字 `JetBrains` 检测字体安装态，一旦家族不吻合就永久判定「已安装」而漏装。`lib/deps.sh` 现新增 `ttf-jetbrains-mono` 依赖，并把两个字体包的状态检测分别收窄为精确匹配 `JetBrains Mono` / `JetBrains.*Nerd`，互相不再误判。
- **护眼模式关闭时 Blur 无法复原 + 失效的 reload 命令 (EyeCare Blur Restore & Reload Command Fix)**:
  - `niri msg action reload-config` 在 niri 26.04 中不存在（正确命令为 `load-config-file`），每次调用均静默失败（被 `|| true` 吞掉），特效切换长期仅靠 niri 对 include 文件的自动热重载兜底，并在或然期间触发了护眼模式关闭后 Blur 不恢复。
  - 引入持久状态机：护眼模式的开/关改由 `effects.kdl` 符号链接的指向目标（`readlink`）判定，替代脆弱的 `pgrep wlsunset` 进程推断——wlsunset 未安装 / 崩溃会令每次 `Mod+N` 都误入 ON 分支并永远卡在护眼模式；现在 wlsunset 死活不再影响特效切换。
  - `--sync` 对齐语义反转：按符号链接状态对齐 wlsunset（eyecare 则拉起、normal 则杀掉），并自愈缺失 / 损坏的 `effects.kdl`（重建为 Normal + 记录日志）；reload 失败不再静默，写入 `$XDG_RUNTIME_DIR/nyxniri-eyecare.log` 并延时重试一次；符号链接交换后以 `readlink` 校验。
  - 注销 / 重登状态同步：`--sync` 改为确定性重建——无条件释放 Noctalia 残留 gamma 锁并清理上一会话遗留的孤儿 `wlsunset` 进程（其 gamma 连接已随旧 niri 失效，`pgrep` 仍可见但不再生效），随后依据持久化的 `effects.kdl` 符号链接状态为本会话拉起全新暖色引擎。避免护眼保持开启时注销重登出现「特效已护眼但暖色丢失」的错位。
  - 终极并发防打架机制 (Flock Serialization & Noctalia Conflict Fix)：引入 `flock` 全局排他锁对切换脚本进行严格串行化，彻底解决手速过快连按 `Mod+N` 或开机自启带来的进程泄漏与竞态不同步；剔除原先为触发弹窗而错误调用的 `noctalia msg nightlight-force-toggle`（该调用会强制唤醒 Noctalia 夺取 Gamma 锁），换为无副作用的纯净 `notify-send`。这解决了笔记本上护眼模式关闭时模糊恢复但暖色不退的顽疾。
  - 核心依赖补全：将 `wlsunset` 正式加入 `lib/deps.sh` 依赖列表，防止在缺少该依赖的机器上发生意外的“备胎”逻辑漂移。

## [v2.1.19] - 2026-08-06

### Added

- **Fish Shell 自定义文件夹自动加载 (`__custom__/`)**:
  - 在 `v2/fish/conf.d/__custom__.fish` 中新增对 `conf.d/__custom__/*.fish` 及 `~/.config/fish/__custom__/*.fish` 的动态遍历与自动载入逻辑。
  - 补充中英双语注释与三重容错校验（目录存在性 `test -d`、通配符空扩展防护、文件有效性 `test -f`），允许用户通过私有子文件夹（如 `__custom__/`）灵活组织多个 `.fish` 脚本，完美履行 Dunder 协议的自动保留承诺。
- **一键清理工具深度重构 (`clean-cache` powered by Maclean)**:
  - 直接拉取并融合 CachyOS / Arch 社区顶级开源清理引擎 Maclean (`BSD-3`)，替换原版 `v2/fish/clean-cache` 逻辑。
  - 引入 Maclean 核心物理安全锁算法 (`_mc_rm_safer`)，基于 `realpath` 规范化校验，彻底防御误删系统核心目录或跨符号链接擦除；
  - 扩展 Shelly 包管理器孤立包与缓存清理支持 (`_mc_shelly`)，全面提升在 Arch / CachyOS / NyxNiri 下的清理效率与安全性；兼容 `-y`/`--yes`/`--auto` 命令行自动模式。

### Changed

- **静态资源架构剥离 (Static Assets Decoupling)**: 彻底重构大体积壁纸分发逻辑，大幅提升主仓库克隆体验：
  - 将庞大的动态视频与高清静态壁纸资源拆分迁移至独立的 `ech678/wallpaper-collection` 仓库。
  - 主仓库仅保留一张轻量级壁纸 `lawson_fuji.webp` 作为默认极速保底，整体克隆体积缩减超过 90%，彻底解决弱网环境下由于大体积媒体文件导致的拉取失败、频繁断线等问题。
  - README 克隆指令统一升级为 `git clone --depth 1` 浅克隆，安装仅需拉取最新快照（约 9MB）。
- **壁纸按需镜像克隆 (On-Demand Mirrored Wallpaper Pull)**: 深度集成全套壁纸下载选项，并修复镜像重试机制：
  - 在 `deploy.sh` 部署环节中新增询问 `是否下载全套精美壁纸与动态视频包？(约 100MB) [y/N]`；新增 CLI 子命令 `nyxniri wallpapers` 与「可选模块」菜单项（含 `[已下载]/[未下载]` 状态标签）。
  - `download_wallpaper_pack` 内置镜像池（`Official`, `gh-proxy.org`），失败自动清理临时目录并轮转备用节点，拉取时强制 `GIT_TERMINAL_PROMPT=0` 避免代理失效引发的用户名密码卡死弹窗；克隆命令统一收敛至 `git_clone_timeout` 硬化助手（低带宽超时 + 禁交互）。
- **防止二次更新盲目下载 (Smart Redownload Prevention)**: 优化体验痛点，以 `~/Pictures/Wallpapers/video/` 特征目录为判据——已全量安装即跳过、缺失则拉取。交互询问显示 `[y/N]` 默认跳过（回车不触发下载），非交互/自动化（`NYXNIRI_AUTO_YES`）模式同样自动判定，避免例行更新时一路回车白白浪费 100MB 流量。
- **环境隔离守护 (Clean Copy Isolation)**: 移除外部克隆的临时仓库中的 `.git` 历史及演示动图 `preview.webp`、`README.md`，使用 `cp -an` 目录形式做绝对纯净的增量覆盖（不再退化为可覆盖用户文件的强拷贝），防止任何展示性质文件污染用户的个人图片文件夹。
- **稳定性修复**: 全局移除了失效与频繁限流的 `ghproxy.net` 节点（`lib/network.sh` 的 `GIT_MIRROR_REGISTRY` / `RAW_MIRROR_TEMPLATES`、`install.sh` 引导程序及 README 安装命令），提高网络切换稳定性；壁纸下载路径补全 `log_msg` 日志与 `git` 存在性守卫，`install.sh` 引导与 `lib/network.sh` 的镜像节点列表统一为同源两节点；同步修改 `README.md` 与 `AGENTS.md`。

## [v2.1.18] - 2026-08-05

### Added

- **快照手动删除 (Snapshot Delete)**: 新增 `nyxniri snapshot delete [序号]` 子命令，替代初版 `snapshot prune` 自动保留策略（快照体积小，保留策略属过度设计）：
  - `lib/backup.sh` 新增 `delete_backup()`：无参时交互列出快照供选择、有参直接校验，删除前强制二次确认（最旧快照可能承载安装前状态，`uninstall 原路复原` 依赖它），删除后显示剩余数量。
  - `get_all_backups()` 显式时间排序（ISO 时间戳字典序即时间序）；回滚前的安全备份统一收纳至 `~/.config/NyxNiri/backups/pre_rollback_*`，不再散落在 `~/.config` 根目录（旧版 `dotfiles_backup_*` 目录仍兼容识别）。
- **菜单 / CLI 全量对齐 + 模块状态显示 (Menu↔CLI Parity & Status Labels)**: 交互式菜单重构为 9 项主菜单 + 子菜单，功能与 CLI 完全等价：
  - 新增「快照管理」子菜单（创建/列表/删除/回滚）、「可选模块」子菜单（Noctalia Greeter / NyxMellow fcitx5 皮肤 / 深度清除，各带 install/status/uninstall 嵌套菜单）。
  - 可选模块子菜单实时显示安装状态标签（`[已安装+已启用]`/`[已安装]`/`[未安装]`/`[已启用]`/`[未启用]`/`[fcitx5 未装]`），由新增 `greeter_status_label()`/`fcitx_status_label()` 计算。
  - CLI 新增 `deps`（依赖菜单）、`bug`/`report`（Bug Report 导出）、`snapshot delete`，并同步更新 `help` 与 fish 补全（`v2/fish/completions/nyxniri.fish`）。
- **安装流程重构：前置清单 + 编号步骤 + 完成汇总 (Install Flow Redesign)**: `install_configs` 彻底重构，解决"可选模块无前置选择权、部署中静默启用、步骤无反馈"的问题：
  - **前置清单**：交互安装开始时打印"即将执行"计划，随后依次询问部署前备份、NyxMellow fcitx5 皮肤（检测到 fcitx5 时**每次必问**，因更新可能带来皮肤改动）、Noctalia Greeter（仅 full）、确认开始。
  - **编号步骤**：`[1/5] 部署配置 → [2/5] 壁纸 → [3/5] 可选模块 → [4/5] 依赖 → [5/5] Greeter`（config 模式自适应）。
  - **完成汇总**：逐项 ✓/跳过状态 + 保留自定义项报告（见下），安装结果一目了然。
- **NyxMellow 皮肤改为显式勾选制 (Skin Opt-in Consent)**: 修复部署时皮肤被无提示自动启用的问题：
  - 新增 `fcitx_consent_ask()` 与持久化启用标记 `~/.local/state/NyxNiri/fcitx-nyxmellow.enabled`：交互时始终询问；非交互自动化仅在用户此前已明确启用（标记存在）时才刷新皮肤，未启用一律跳过。
  - `deploy_fcitx_theme`（更新流程入口）改为先征询再应用，不再无条件自动启用；`nyxniri fcitx install` 成功写入标记、`uninstall` 清除标记。
- **Customizations Preserved 移入安装汇总 (Custom-Preserved Report in Summary)**: 提取 `print_custom_preserved()`，`deploy_selected_configs` 不再中途输出大色块，改由安装/更新流程尾部的完成汇总统一呈现。
- **开发者实机测试命令 `nyxniri test` (Test Deploy Command)**: 强制「不备份 + 保留 `monitor.kdl`（不询问）+ 跳过可选模块与依赖 + 零提示」的幂等重放，供维护者在实机快速验证部署。新增 `NYXNIRI_KEEP_MONITOR=1` 环境开关供 `deploy_selected_configs` 跳过显示器配置询问。
- **System Doctor 健康检查增强 (Doctor Health Checks)**: `nyxniri doctor` 新增三项容错检查：`xdg-desktop-portal-gtk` 后端缺失告警、`$HOME` 磁盘剩余空间低于 10 GiB 告警、NyxMellow fcitx5 皮肤启用态检测；`generate_bug_report` 同步收录（新增第 6 节 "NyxNiri Health Checks"）。

- **monitor.kdl 保留问询前置与无打断部署 (Uninterrupted Deploy Execution)**: 将 `monitor.kdl` 的显示器配置保留问询移至【前置集中配置卡片】阶段完成，彻底删除了物理复制过程中途突兀弹出的二次询问。部署执行零打断、一气呵成。
- **可选模块规范化扩展架构 (Modular Options Registry Protocol)**: 建立了统一的可选模块规范接口 (`OPTIONAL_MODULES` 及 `module_is_available`/`module_get_name`/`module_get_status`/`module_deploy`)：
  - **前置标准化卡片 (Pre-flight Setup Card)**：渲染结构化卡片，清晰呈现 Core、Hardware 以及各个可选模块的实时检测状态。
  - **子菜单与完成卡片统一**：配合 CJK 感知对齐函数 `_disp_pad`，具备高扩展性，方便未来无缝添加新可选模块。
- **在线管道 Standalone 模式代码时效性保障 (Online Bootstrap Freshness)**: `install.sh` 在 Standalone 模式下，当 `$CACHE_DIR/.git` 已经存在时，自动尝试 `git pull --ff-only`（带超时与降级），确保在线管道一键安装始终运行最新的 `main` 分支代码。
- **依赖管理菜单快捷热键 (Dep Menu Hotkeys)**: `lib/deps.sh` 依赖勾选菜单支持快捷热键 `a` (全选)、`n` (全取消)、`i` (立即安装)，双语提示同步美化。
- **DRY 交互助手与零语言磁盘文件 (DRY Confirm Helper & Zero Language Disk Artifacts)**: 抽象出 `prompt_confirm` 确认助手函数，精简 50+ 行重复交互代码；取消语言选择磁盘持久化，保证 `$HOME` 绝对纯净。
- **README 极简排版与去 AI 味纯净润色 (De-AI README & Markdown Standard)**: 彻底扫除 README 中的机器感与膨胀修饰词，保持干净自然的 GitHub `##` 标题下方边框分隔；更正致谢与推荐项目描述（`glassy-niri` 标注参考 blur 效果，`shorin-niri` 标注“抄了很多！”，`noctalia-lyrics` 更正为状态栏歌词组件），修正折叠块内 HTML/Markdown 兼容性。

### Changed

- `lib/i18n.sh` 的 `msg()` 保留 `$p1`/`$p2` 双参数支持（供 `delete_done` 等多值提示）；主菜单与全部子菜单文案重排，中英文同步更新。
- **菜单视觉统一 (Menu Visual Unification)**: 统一屏幕标题为 `=== 标题 ===`（安装汇总原 `═══` 并入），删除主菜单与 logo 重复的 `welcome` 欢迎行；`9) 可选模块` 配色由黄转绿（破坏=红 / 退出=灰语义不变）；`按任意键返回主菜单` 文案修正为 `按任意键继续`（子菜单通用）；新增 CJK 感知补白函数 `_disp_pad()` 使「可选模块」菜单的安装状态列中英文右对齐；语言选择屏改为青色标题 + 绿色编号，与主菜单风格一致。
- README 更新 Tooling 表（`snapshot delete`/`deps`/`bug`/`test`）、安装流程说明（前置清单 + 步骤 + 汇总）与可选模块说明（皮肤显式勾选制）。

## [v2.1.17] - 2026-08-03

### Added

- **NyxMellow 动态 fcitx5 皮肤模块 (Dynamic Fcitx5 Skin Module)**: 新增可选模块 `lib/fcitx.sh`，将 mellow 系列的圆角形状与 Noctalia Material You 自动取色结合，提供实时跟随壁纸/明暗模式的输入法皮肤：
  - 主题源码存放于仓库根目录 `fcitx5/nyxmellow/templates/`（仿 `Wallpapers/` 资产目录）：`theme.conf` 沿用 mellow 的布局与边距、`panel.svg`/`highlight.svg` 保留 mellow 原版几何（圆角 9.5 / 描边 1.2 / 阴影），颜色全部替换为 Noctalia 模板变量（`surface_container_lowest`/`outline`/`primary`/`on_surface`/`on_primary`/`outline_variant`）。
  - 在 `v2/noctalia/noctalia-config.toml` 静态注册三条 `theme.templates.user.nyxmellow_*` 模板（路径用 `/home/user` 占位符，部署时由既有 sed 机制替换为 `$HOME`），末条附 `post_hook` 在渲染后安全重启 fcitx5（仅当进程在运行时）。
  - 新增 CLI 子命令 `nyxniri fcitx install|status|uninstall`：`install` 部署模板 → 定向改写 `classicui.conf` 的 `Theme`/`DarkTheme`（其余设置不动，原始值备份至 `~/.local/state/NyxNiri/`）→ `noctalia msg templates-apply` 渲染 → 重启 fcitx5；`uninstall` 剔除模板注册、删除主题目录并还原原主题。
  - `install.sh deploy/update` 流程在 `deploy_wallpapers` 之后自动调用 `deploy_fcitx_theme`（fcitx5 未安装时仅部署模板并跳过激活，不中断主流程）；`uninstall/purge` 一并清理。
  - 单模板随明暗模式自动重渲染：`{{ colors.X.default.hex }}` 跟随当前 mode，切换 `theme-mode-set dark/light` 即重新取色（浅色白面板/深色暗面板）。

### Fixed

- **fcitx 模块 REPO_DIR 加载时序缺陷 (Fcitx Module REPO_DIR Source-Time Resolution Fix)**: 修复 `lib/fcitx.sh` 在模块加载时（`main.sh` 于 `init_environment_paths` 之前 source）即展开 `FCITX_SOURCE_DIR="${REPO_DIR:-.}/..."`，导致 `REPO_DIR` 尚未赋值而回退为当前工作目录、从非仓库目录运行（如 `nyxniri` 软链/standalone 缓存模式）时模板源码路径失效、皮肤步骤被跳过的缺陷；改为 `fcitx_source_dir()` 调用时解析。

### Changed

- **README 重构与皮肤预览 (README Restructure & Skin Preview)**: 重写 `README.md`（595 → 477 行），保留中英双语锚点结构并精简为「预览 / 特性 / 环境要求 / 安装 / 配置一览 / 工具 / 快捷键 / 可选模块 / 故障排除 / 致谢许可」紧凑布局：
  - 快捷键表折叠进 `<details>`，`nyxniri` 与 `nyxhelp` 合并为 Tooling 一节；badges 8→5，admonition 块 7→2；全文去除模板化/AI 腔表述，新增 Requirements、Included Configs、Optional Modules、License 区块，链接 `LICENSE` 与 `CHANGELOG.md`。
  - 新增 `preview/` 目录：`preview.webp`（桌面总览）由仓库根目录移入（Git 识别为 rename，blob 不重复存储），并新增 `light_skin.png`/`dark_skin.png`（NyxMellow 皮肤浅/深色展示图）；README 新增 `Preview / 预览` 画廊区块，修正图片引用路径。

## [v2.1.16] - 2026-08-02

### Changed

- **Niri 配置文件纯粹拆分与模块化 (Niri Config Pure Splitting)**: 彻底重构了原本庞大的 `v2/niri/config.kdl`，在**绝对不改动任何核心外观**与原有规则优先级的前提下，将其模块化解耦。
  - 将外观布局参数与动画曲线拆分为独立的 `layout.kdl` 和 `animations.kdl`。
  - 将所有窗口规则与图层规则 (Window/Layer Rules) 提取至 `rules.kdl`。
  - **输入外设私有保护 (Input Preservation)**: 利用部署引擎原生的 Dunder 保护机制，将鼠标、触摸板、手势等设备配置专门剥离至 `input__custom__.kdl` 中。在日后执行 `./install.sh update` 同步仓库时，用户的键盘布局和硬件习惯将被自动保留而不被覆盖。
  - 主文件 `config.kdl` 现仅保留极简的核心挂载入口和环境变量，代码可读性与可维护性极大提升。

### Added

- **可选登录启动器模块 (Optional Noctalia Greeter Module)**: 新增独立可选模块 `lib/greeter.sh`，为 greetd 登录界面提供一键安装与配置能力：
  - 新增 CLI 子命令 `nyxniri greeter install|status|uninstall`，并在 `install full` 交互流程末尾提供 y/N 可选提示（非交互模式默认跳过，保持向后兼容）。
  - 自动安装 `greetd`（官方源）与 `noctalia-greeter`（AUR），备份并原子写入 `/etc/greetd/config.toml`（会话名经 `noctalia-greeter sessions` 运行时校验），补建 `/var/lib/noctalia-greeter` 状态目录，启用 `greetd` 服务（不抢占当前会话 VT）。
  - 写入 Greeter 主题免密同步 Polkit 规则；检测到其他显示管理器时仅打印一行提示、绝不自动禁用；全部特权步骤经 `sudo` 单命令容错执行，失败仅 WARN 不中断主流程。
  - `nyxniri greeter status` 与 `nyxniri doctor` 集成 Polkit 规则三态检测（present / missing / unverifiable），正确处理 polkit 126+ 默认 `750 root:polkitd` 锁定目录下的内容感知检测。
- **AUR Helper 自动自举 (Automatic AUR Helper Bootstrap)**: `lib/deps.sh` 新增 `ensure_aur_helper()`，`install full` 在缺少可用 paru/yay 时自动安装 `paru`——优先官方软件源（如 CachyOS），否则克隆 AUR 源码包在本机编译（全程非 root，`makepkg` 拒绝 root 运行），使纯命令行环境可一键安装包含 AUR 依赖（`noctalia`、`mpvpaper`）的完整 DE；任一环节失败自动回退到原有跳过逻辑，不中断安装。

### Fixed

- **CLI 命令 CONFIG_ITEMS 空数组缺陷 (CLI CONFIG_ITEMS No-op Fix)**: 修复 `nyxniri install/snapshot/rollback/uninstall/purge` 从命令行调用时未执行 `discover_config_items` 导致 `CONFIG_ITEMS` 为空、命令静默空操作（如快照为空目录、卸载不归档不移除）的缺陷，使 CLI 模式行为与交互菜单一致。
- **mpvpaper 版本检查 pipefail 中断 (mpvpaper Version Check Abort Fix)**: 修复 `check_mpvpaper_version` 中两处未受保护的命令替换在 `set -o pipefail` 下因 `pacman -Qi` 返回非零而中断 `install full` 的隐患，为 `git_version`/`version` 取值补充容错展开。
- **Greeter Polkit 规则误报 (Greeter Polkit Rule False Negative Fix)**: 修复 `greeter_status` 在 `/etc/polkit-1/rules.d`（polkit 126+ 默认 `750 root:polkitd`）下普通用户无法遍历目录而误报规则 `missing` 的问题，改为在 root 上下文内按 action 内容进行通配检测（兼容任意文件名），并区分不可验证 `unverifiable` 状态。
- **AUR Helper 预编译 ABI 不兼容 (AUR Helper Prebuilt ABI Fix)**: 修复 AUR 预编译 `paru-bin` 二进制链接的 libalpm 版本与本机不一致（新版 Arch / CachyOS 的 libalpm v16 下运行时报 `libalpm.so.15: cannot open shared object file`）导致自举"安装成功但不可运行"、进而连锁拖垮 AUR 依赖与 Greeter 安装的缺陷：新增 `aur_helper_usable()` 以 `--version` 真实运行验证取代原有仅 `command -v` 的存在性判断（坏 helper 一律视为不存在），并统一替换 deps/greeter 各处的存在性检测；自举策略改为官方源优先、AUR 源码包本机编译兜底，彻底规避 -bin 预编译的 ABI 陷阱。
- **残留 paru-bin 包冲突 (Stale paru-bin Conflict Fix)**: 修复早期失败自举残留的 `paru-bin`/`paru-bin-debug` 包与 `paru` 同名文件（`/usr/bin/paru`）冲突、导致 `pacman -U`/`pacman -S` 在 `--noconfirm` 下默认拒绝卸载而事务失败的问题；在 repo 与源码两条安装路径之前先按 `-Qq` 守卫逐个移除残留包。
- **README 排版与说明 (README Polish)**: 中英文版新增 greeter 可选模块、AUR 依赖自举与 Polkit 规则说明；清理重复表格行，保持与既有文档风格一致。

## [v2.1.15] - 2026-08-02

### Changed

- **Fish 包管理终端交互重构 (Terminal Package Management Refactor)**: 全面重构 `up` / `in` / `se` / `un` 命令，引入 `_nyxniri_pkg_helper` 智能感知 `paru` > `yay` > `shelly` > `pacman` 优先级以消除 `AccessDenied` 报错；支持带参无参智能跳转；拦截 `Ctrl+C` 二次触发；引入无 `fzf` 的平滑降级，全面提高防呆与容错体验。

### Fixed

- **安装脚本核心删除加固 (Installer Rm-rf Hardening)**: 为 `install.sh` 在克隆仓库前的 `rm -rf "$target_dir"` 增加了多重断言。只有在目录非空、路径深度 `>= 3` 且匹配 `.cache/NyxNiri` 后缀时才执行删除，从源头消灭参数丢失导致误删关键目录的红线风险。
- **护眼模式无参调用崩溃修复 (EyeCare Mode Argument Fix)**: 修复了 `v2/niri/toggle-eyecare.sh` 在通过 `Mod+N` 快捷键无参调用时，因近期引入的 `set -uo pipefail` 严格模式导致脚本因 `$1` 变量未绑定而直接崩溃的问题，通过采用 `"${1:-}"` 语法安全展开缺省参数，恢复了护眼功能的正常切换。
- **自定义软链接静默丢失修复 (Custom Symlink Preservation Fix)**: 修复了 `lib/deploy.sh` 的 `atomic_replace_item` 中因 `find -type f` 漏判软链接（`-type l`）导致更新时用户外部挂载的自定义配置文件（如 `01__custom__.fish -> /other/path`）被静默删除的红线级缺陷，提升文件匹配规则为 `\( -type f -o -type l \)` 彻底保障数据完整性。
- **Noctalia Polkit 代理与免密同步 (Noctalia Built-in Polkit & Greeter Sync)**: 
  - 在 `v2/noctalia/noctalia-config.toml` 的 `[shell]` 模块中默认开启 Noctalia 现代化内置认证代理 `polkit_agent = true`，解决移除外部代理自启后导致 `pkexec` 无法弹窗而抛出同步外观失败通知的问题。
  - 在 `README.md` 故障排除模块新增了通过写入系统级 Polkit 规则实现 `greeter` 外观免密静默同步的完整解决方案。
- **README 参考文档排版修正 (README References Restructure)**: 优化中英文版 `README.md` 排版，将致谢项目 (`RanXom/glassy-niri`) 与其它推荐组件剥离，消除误导表述。

## [v2.1.14] - 2026-07-31

### Fixed

- **纯 TTY 控制台图标降级兼容 (TTY Console Icon Fallback, Fix Issue #8)**: 修复在退出桌面环境进入纯 Linux 虚拟控制台（TTY）时，命令行提示符因不支持渲染 Nerd Font 而显示方块乱码的问题。通过检测 `$TERM == "linux"`，自动回退并禁用 Starship 提示符与 `eza --icons`，在桌面终端保留高颜值配置的同时，为纯字符 TTY 环境提供干净的原生纯 ASCII 体验。

## [v2.1.13] - 2026-07-31

### Fixed

- **在线安装管道交互修复 (Pipeline Interactive Mode Fix)**: 修复了使用 `curl -sL ... | bash` 安装时，控制台菜单因为 stdin 被管道占用而瞬间自动跳过的问题。引导程序现在会智能识别管道环境，并在主控制台启动时将键盘控制权强行重定向回物理终端 `/dev/tty`，完美恢复交互式安装体验。

## [v2.1.12] - 2026-07-31

### Added / Improved

- **安装脚本全面模块化拆分 (Modular Script Architecture)**:
  - 将原单文件约 1800 行的 `install.sh` 重构拆分为模块化架构：根目录仅保留极简 `install.sh` 引导程序（兼顾 `curl` 在线一键安装与本地仓库部署），根目录简洁利落。
  - 主程序控制台解耦移入 `lib/main.sh`，并划分出 7 大功能库模块：`lib/core.sh` (核心基础/日志/Trap), `lib/i18n.sh` (双语国际化字典), `lib/network.sh` (镜像源回退/超时防断), `lib/deps.sh` (依赖检测/安装), `lib/backup.sh` (快照备份/回滚/卸载), `lib/deploy.sh` (原子部署/自适应替换), `lib/doctor.sh` (健康诊断与 Bug Report 导出)。
- **Bash 严苛执行模式与安全性强化 (Strict Shell Mode & Safety Hardening)**:
  - 全库模块开启 `set -euo pipefail` 严格错误与未定义变量捕获模式，全面消除未初始化变量可能引发的逻辑与部署陷阱。
  - 优化 `trap cleanup` 机制，所有临时路径统一入队注册并自动防死锁清理。
- **`*__custom__*` 私有配置通配继承与数字排序支持 (Enhanced Custom Preservation Protocol)**:
  - 升级部署引擎中的 `atomic_replace_item()`，匹配规则扩展为 `*__custom__*`。
  - 全面支持无后缀文件（如 `__custom__env`）、规则文件（如 `01__custom__.fish`）及数字前缀排序，允许用户通过前缀（如 `01-` / `99-`）精确控制在 Fish `conf.d/` 或其它加载环境中的字母表解析与覆盖顺序。
  - 在 `find` 引擎中引入 `-prune` 剪枝，连根提取 `*__custom__*` 目录及其内部所有脚本与素材，彻底消除重复递归与多余控制台日志。
- **Kitty 终端私有配置挂载补全**: 在 `v2/kitty/kitty.conf` 最末尾接入 `include __custom__.conf` 挂载点，并在 `v2/kitty/__custom__.conf` 中下发双语注释模版，预置 `include glob:*__custom__*.conf` 高级通配指令。
- **文档与测试规范更新**: 同步更新 `README.md` 中英文版关于 `*__custom__*` 通配与数字前缀排序的标注；在 `审查方案.md` 中新增物理隔离沙箱与实机 `~/.config` 测试方法规范及 Changelog 归档。

### Fixed / Hardened

- **字体识别算法与依赖菜单交互修复 (Package Detection & Dep Menu State Fix)**:
  - 修复 `lib/deps.sh` 依赖检测：优先通过 `pacman -Qq <pkg>` 查询包数据库，结合增强正则匹配，彻底解决 `ttf-jetbrains-mono-nerd` 和 `noto-fonts-cjk` 因空格/后缀在 `fc-list` 中匹配失败导致误报 `[未安装]` 的缺陷。
  - 修复依赖安装菜单交互：解耦系统检测 `check_all_deps` 与用户交互勾选数组 `DEP_SELECT`，解决每次循环按键刷新都导致用户 `[*]` / `[ ]` 勾选状态被强制擦除重置的 bug。
- **单文件部署类型隔离 (Single File Deployment Hardening)**: 修复 `atomic_replace_dir` 在处理单文件（如 `starship.toml`）时尝试执行目录 `find` 与 `mkdir` 的类型混淆缺陷，隔离文件级原子替换与目录替换逻辑。
- **非 TTY 与批处理环境崩溃防护**: 在交互读取处增加 `[ -t 0 ] && [ -c /dev/tty ]` 联合校验，解决在管道、非交互及无 TTY 环境下因 `set -e` 导致脚本突然中断报错的问题。
- **全仓库鲁棒性审查修复 (Full Repository Robustness Audit)**:
  - **`lib/backup.sh`**: `rollback_configs` 回滚循环从非原子 `rm -rf` + `cp -rP` 改为 `atomic_replace_dir`，消除 Ctrl+C 中断时配置目录只删不建的数据丢失风险，与 `deploy_selected_configs` 保持一致。
  - **`lib/network.sh`**: `safe_pull_or_reset` 中 `git pull` 和 `git fetch` 添加 `http.lowSpeedTime=15` 超时配置，防止网络不通时菜单更新操作无限挂起；`ensure_repo` 的 `rm -rf` 补充路径深度（≥3 层 `/`）校验加固高危删除安全保护。
  - **`lib/deploy.sh`**: 将 `noctalia-config.toml` 壁纸路径替换从依赖 `图片` 中文字符改为 TOML 键名精准匹配（`^directory` / `^video_directory`），兼容所有语言系统（如英文 `~/Pictures`）；修复 `export VAR=$(mktemp)` 在 `set -e` 下掩盖 mktemp 失败的 Bash 语义陷阱，改为先赋值后 export。
  - **`lib/doctor.sh`**: 将 noctalia 检测从单一分支拆分为三条独立诊断，区分「noctalia 未安装」与「进程未运行」，提升故障排查精度。
  - **`v2/niri/toggle-eyecare.sh`**: 添加 `set -uo pipefail` 严格模式（不开 `-e`，保留 pgrep `&&` 控制流语义）。
  - **`审查方案.md`**: 1.2 节补充软链接例外条款（系统配置内部互链不违反隔离原则）；第 4 节归档全量审查记录。
  - **`README.md`**: 修复 `nyxhelp --all` 错误参数为 `nyxhelp all`；补全 `nyxniri install [full|config]` 参数说明；目录树添加缺失的 `lib/` 核心模块目录条目（中英文均已修复）。

## [v2.1.11] - 2026-07-30

### Added / Improved

- **Dunder 私有配置与文件夹继承机制 (Dunder Custom Preservation Protocol)**: 在 `install.sh` 的 `atomic_replace_dir()` 原子替换引擎中接入针对 `__custom__.*` 私有文件与 `__custom__/` 私有命名空间文件夹的继承防护逻辑。在更新部署时自动将用户个人的入口配置（如 `__custom__.kdl`, `__custom__.fish`）及整个私有文件夹连根提取并无缝合并，彻底解决系统覆盖更新时用户自定义脚本被破坏的问题。
- **自定义文件双语模版预置**: 在 `v2/niri/__custom__.kdl` 与 `v2/fish/conf.d/__custom__.fish` 下下发预置的中英双语空白注释模版，并在 `v2/niri/config.kdl` 末尾默认挂载 `include "__custom__.kdl"` 引入钩子。
- **部署日志透明化与末尾总结输出**: 在配置覆盖阶段提供亮蓝色的可视化日志沉淀，并在部署完成前自动归档打印 `[ NyxNiri Customizations Preserved ]` 摘要总结卡片；离开时自动安全回收临时日志句柄。
- **README 文档与描述修正**: 在 README 中英文版中新增 `> [!TIP]` 标注的 Dunder 自定义配置使用说明，并修正安装备份提示为可选预留逻辑。

### Changed / Refactored

- **Git 克隆与镜像降级策略重构 (`clone_repo_with_fallback`)**: 在 `install.sh` 中废弃先通过 `git ls-remote` 预测试延迟的 `select_git_mirror` 方案，重构为按优先级直接尝试 `git clone --depth 1` 并自动回退的引擎。当某一节点拉取失败时自动清理残存文件夹并切至下一个镜像节点，显著提升在不稳定网络环境下的部署成功率与抗波动能力。
- **缓存目录验证与自动修复 (`ensure_repo`)**: 校验逻辑升级为严格检查 `$CACHE_DIR/.git` 文件夹的存在性；若缓存目录存在但非合法 Git 仓库（如上次异常中断留下的空目录），自动触发 `rm -rf` 彻底清理后重新拉取，防范因残缺目录导致误判或部署阻断。
- **代码精简与规范清理**: 移除测速与毫秒耗时计算等约 30 行非核心开销代码，使主干流程更加直观干净；清理脚本内多处尾随空格（Trailing Whitespaces）。

## [v2.1.10] - 2026-07-30

### Added / Improved

- **多节点镜像源阶梯降级 (3-Tier Mirror Fallback Protocol)**: 在 `install.sh` 中引入极强鲁棒性的镜像降级引擎。网络拉取与 Git 仓库克隆严格遵循 **官方直连 $\rightarrow$ Fastly jsDelivr CDN $\rightarrow$ gh-proxy 镜像代理 (`gh-proxy.org` / `ghproxy.net`)** 阶梯降级策略；彻底清理废弃的 `bgithub.xyz` 站点。
- **安装日志透明化沉淀 (Explicit & Transparent Logging)**: 在 Git 节点测试、资源下载与 Fisher 插件安装过程中，引入带色彩的实时终端进度 Log 输出（包含 HTTP 状态码与连通耗时），同步沉淀至 `$LOG_DIR/install.log` (`~/.local/state/NyxNiri/install.log`)。
- **双模式安装与镜像克隆文档重构**: 在 `README.md` 中英文版中明确划分为 **独立在线管道模式 (Standalone)** 与 **仓库部署模式 (Repository)**；在网络加速卡片中增加 `git clone https://gh-proxy.org/https://github.com/ech678/NyxNiri.git` 镜像克隆指令。
- **集中化镜像源注册表 (Centralized Mirror Registry)**: 在 `install.sh` 顶部全局集中定义 `GIT_MIRROR_REGISTRY` 与 `RAW_MIRROR_TEMPLATES` 数组，实现镜像配置与探测下载引擎彻底解耦，极大提升项目可维护性。
- **`set -e` 安全隔离与 Payload 校验**: 隔离 `git fetch` 与 `curl` 网络命令，引入双重超时防护（`--connect-timeout 3` 与 `-m 10`）及 Content-Type HTML 拦截校验，防止网络中断或 404 网页拦截打断安装流程。
- **Fish Shell 代理诊断增强 (`proxy_status`)**: 在 `v2/fish/config.fish` 的 `proxy_status` 指令中新增对 `https://github.com` 的 HTTP 响应与耗时测试，方便用户一眼分辨终端代理接管 GitHub 流量的状态。

### Fixed / Hardened

- **壁纸无痛增量同步 (Incremental Wallpaper Sync, Fix Issue #5)**: 彻底重构 `deploy_wallpapers()` 为 `cp -an "$wp_src"/. "$wp_dest"/` 静默增量同步。在自动补全与升级仓库新增壁纸/视频的同时，**100% 完好保留**用户在 `~/Pictures/Wallpapers` 中的个人图片与视频文件；淘汰原有的破坏性 `rm -rf` 整盘清空与二选一弹窗。
- **配置纯净直接覆盖与消除误判弹窗**: 还原 `atomic_replace_dir()` 为干净原子的直接整盘覆盖，完全移除 `has_custom` 误判检测逻辑，消除 `effects.kdl`（运行时生成）和 `fish_variables`（Fish 动态生成）等非仓库文件导致频繁误弹的问题；彻底消除误导性的备份文案，配置覆盖行为完全由开头的 `:: 是否在部署前备份当前配置？[y/N]` 统一掌控。
- **Fish 包管理交互降级兼容 (`se` / `un`)**: 在 `v2/fish/config.fish` 的 `se` (模糊搜索安装) 与 `un` (模糊搜索卸载) 快捷指令中添加 `paru` $\rightarrow$ `yay` $\rightarrow$ `pacman` 动态感知降级检测。当系统未安装 `paru` 时自动使用 `yay` 或 `pacman`，避免命令直接报错崩溃。
- **Fisher 自动安装网络超时防护**: 在 `install.sh` 的 Fisher 自动安装管道中为 `curl` 添加 `-sfL` (`--fail`) 选项，防止网络超时或 GitHub Raw 拦截返回 HTTP 40x/50x 错误网页时打断 Fish 初始化。
- **README 文档校对与 CLI 表格补齐**: 在 README 中英文 CLI 工具说明表格中补齐 `nyxniri install [mode]` 与 `nyxniri update [--force]` 指令说明；同步在 `审查方案.md` Changelog 历史集中归档全量审查记录。
- **README 视觉与排版全面优化 (Visual & Typography Overhaul)**: 快捷键表格全面升级为 `<kbd>` 键帽样式（4 张表格 52 行）；修正 Material You 取色描述为 Noctalia V5 原生取色 + 自定义 Lua 钩子桥接视频壁纸；修正 `Super+J/K` 方向描述 (`up/down` → `down/up`)；故障排除段落标题与正文拆分独立；中文段落消除名词跨行断裂（`Noctalia V5`、`护眼模式 (Super+N)` 等）；安装模式描述结构化排版；修复中文版 LaTeX `$\rightarrow$` 为 Unicode `→`；`lua` 规范为 `Lua`；底部添加分隔线；中文 NOTE/WARNING 断行修复。

## [v2.1.9] - 2026-07-29

### Added

- **智能动态配置自动发现 (Dynamic Config Auto-Discovery)**: 彻底废除硬编码的配置项目录数组，实现 `discover_config_items()` 扫描引擎，自动探索并纳管 `$REPO_DIR/v2/` 下的所有组件；新增 Zed 编辑器配置至 `v2/zed`，实现零代码改动全自动纳管部署、快照备份与回滚。
- **配置覆盖升级 (Optional Overwrite Upgrade)**: 运行 `nyxniri update` 或选择菜单选项 6 时，支持在 git pull 更新仓库与脚本后选择 `1) 极速直接覆盖`、`2) 安全备份覆盖`、`3) 选择性/逐组件覆盖` 与 `4) 跳过`；部署备份提示调整为 `[y/N]` 默认回车跳过备份，同时完好隔离保护个人硬件配置 `monitor.kdl`。
- **Starship 实时网络代理指示器 (Starship Real-Time Proxy Indicator)**: 在 `v2/starship.toml` 中新增 `[custom.proxy]` 模块，当检测到全局代理环境变量（`http_proxy` / `all_proxy` 等）激活时，实时在终端 Prompt 中绘制黄底黑字 `󰲝 端口` 胶囊（如 `󰲝 7890`）；重构 `git_branch` 与格式化前缀，实现多场景下 100% 数学对称间距。
- **壁纸部署安全保护 (Wallpaper Preservation)**: 将壁纸部署逻辑从 `deploy_selected_configs()` 独立抽取为 `deploy_wallpapers()` 函数；部署前交互提示用户是否保留已有壁纸目录（默认 Y 保留），非交互模式（SSH/管道）自动跳过已有目录；选择性覆盖升级模式不再强制替换壁纸。

### Fixed / Hardened

- **更新后新配置目录遗漏修复**: `update_repo_and_script()` 在 repo 和 standalone 两条路径的 git pull 成功后均重新调用 `discover_config_items()` 刷新组件列表，确保更新拉取的新配置目录在本次部署中不会遗漏。
- **`discover_config_items` 备用数组补全**: 硬编码 fallback 列表新增 `"zed"`，与自动扫描逻辑保持一致。
- **README 文档修复与校对**: 修正 `Super + Ctrl + Arrows` 键位描述（列移动 vs 窗口移动），补充缺失快捷键及 `nyxhelp` 交互式速查入口；4 条 `curl` 安装命令补齐 `--connect-timeout 10` 防止 GitHub 不可达时无限挂起；英文版 `nyxhelp proxy` 描述对齐中文版的动态端口说明；目录结构树与 fallback 数组同步补全 `zed/`。

### Changed / Refactored

- **单一事实来源 (Single Source of Truth, SSOT) 鲁棒性重构**: 在 `install.sh` 顶部全局统一定义配置模版名称常量 `CONFIG_DIR_NAME="v2"`，全脚本清除所有硬编码 `/v2` 路径；未来若重命名模版文件夹只需修改头部这 1 行代码。
- **纯粹多语言隔离 (Pure I18n Language Separation)**: 彻底清理中文模式下所有混杂的英文翻译括号与斜杠后缀（如 `/ Deployment & Setup`），选择简体中文即呈现 100% 纯正地道的中文界面。
- **零 Emoji 极简 Modern CLI 界面**: 在完全保留原版 6 行 ASCII 大 Banner (`NYX NIRI`) 的前提下，彻底清除所有 Emoji 视觉噪音，采用经典的 Arch / Modern CLI 指示符 (`::`, `[+]`, `[-]`, `[OK]`, `[WARN]`)；将主菜单划分为四大生命周期逻辑分组。
- **部署自动化初始化扩展 (Post-Deployment Initialization)**: 在 `install.sh` 部署成功后自动检测并赋予 `theme-sync.sh` 可执行权限并触发首次同步，确保部署完成后 GTK 3/4 与系统主题自动调和对齐；同步更新 `nyxhelp` 命令速查说明。


## [v2.1.8] - 2026-07-28

### Added

- **`nyxhelp` 炫酷 TUI 交互式速查终端**: 全新推出唯一命令 `nyxhelp`，依托 `fzf` 构建双栏 TUI 交互界面，实时检索与预览 NyxNiri CLI、代理控制、包管理、Niri 核心快捷键及终端自动补全指南；完全清理旧版 `custom_help`、`pkg_help` 等分散别名。
- **代理控制增强 (`proxy_on`)**: `proxy_on` 全面支持动态覆盖自定义端口与 IP 地址（如 `proxy_on 10808` 或 `proxy_on 192.168.1.5:7890`）；同时导出大写与小写代理环境变量（`HTTP_PROXY` / `http_proxy` 等），增强 CLI 工具兼容性。

### Fixed / Hardened

- **`fzf` 预览窗渲染报错修复**: 解决在子 Shell 场景下运行 `nyxhelp` 导致 `fzf` 预览窗口抛出 `未知的命令` 异常的问题；将 `nyxhelp` 进行全局内聚封装，实现低至 <1ms 的高亮预览。
- **终端审美排版调优**: 优化速查终端排版，全面替换繁杂花哨的 Emoji，采用端庄优雅的字符框段（如 `[ NyxNiri CLI & 配置快照 ]`）与 Fish `set_color` 原生色彩引擎，提升极简专业审美。

### Changed / Refactored

- **Noctalia 自动化脚本 DRY 重构**: 重构 `theme-sync.sh` 精简 23 行重复的分支写入逻辑；在 `wallpaper-hook.sh` 和 `mpvpaper-sync.sh` 中使用 Bash 正则表达式优化视频文件后缀校验，并在 `mpvpaper-sync.sh` 中补充局部变量作用域声明，防止变量污染。
- **死代码与废弃配置大清理**: 移除过时 Matugen 主题文件 `v2/kitty/themes/matugen.conf`、空置脚本 `v2/fish/conf.d/inir-env.fish`、Starship 残留 `[palettes.ii]` 色板以及 Niri 配置中的旧版图层规则注释。
- **PATH 路径脚本规范化**: 将 `v2/fish/conf.d/inir-path.fish` 重命名为 `v2/fish/conf.d/nyxniri-path.fish`，统一项目前缀并简化 PATH 路径挂载逻辑。

## [v2.1.7] - 2026-07-27

### Fixed / Hardened

- **护眼模式 (Mod+N) 部署后状态颠倒错位修复**: `toggle-eyecare.sh` 不再依赖会被"部署配置"清空重置的 `.eyecare_state` 状态文件，改为直接以 `wlsunset` 进程是否存活作为唯一事实来源判断当前护眼状态，彻底解决部署后色温与窗口透明度/Blur 状态脱同步、切换键表现"颠倒"的问题；新增 `--sync` 校准模式并接入 `config.kdl` 的 `spawn-at-startup`，niri 重启后可自愈对齐。
- **install.sh 部署原子化**: 新增 `atomic_replace_dir()`，部署/回滚前先复制到临时目录、确认成功后才 `rm+mv` 换上去，避免中断（Ctrl+C / 断电 / 磁盘满）导致配置目录只删不建、直接丢失；顺手删除了从未被调用的死代码 `copy_config_items()`。
- **install.sh 清理陷阱死代码修复**: 原 `TEMP_WORKDIR` 声明后从未被实际赋值，中断清理 trap 形同虚设；改为 `CLEANUP_TEMP_PATHS` 注册表，所有临时文件/目录均能在退出时被正确回收。
- **install.sh 备份列表空格拆分 bug**: `get_all_backups` 原先靠 `echo "${arr[@]}"` 与 `read -a` 字符串往返传递，路径含空格时会被错误拆分，可能导致回滚指向错误快照；改为直接填充全局数组。
- **install.sh 自更新安全性**: 统一改用脚本自解析的 `REAL_SCRIPT_PATH` 而非裸 `$BASH_SOURCE` 定位并覆盖自身；下载的新版本脚本先落地临时文件、`bash -n` 语法校验通过后才原子替换真身，避免网络中断导致执行到半截的脚本被直接运行；`git reset --hard` 前检测工作区是否存在未提交改动并交互确认，不再静默丢弃本地修改；连接 GitHub 失败切换国内镜像时，交互场景下会先征求用户确认。
- **Qt 应用 Wayland/X11 容错回退优化**: 将 `v2/niri/config.kdl` 中的环境变量 `QT_QPA_PLATFORM` 改进为 `"wayland;xcb"`。使 Qt5/Qt6 应用优先运行于 Wayland 原生模式，当缺失 Wayland 插件或初始化失败时能自动回退至 Xwayland (`xcb`) 运行，避免应用直接崩溃。

### Added

- **`clean-cache` 智能化改造**: 用体积阈值（默认 50MB）动态扫描 `~/.cache` 取代逐个硬编码的 App 缓存白名单，新装软件无需改脚本即可被自动覆盖清理；新增 `-y/--yes/--auto` 非交互自动化模式，便于接入 cron/systemd timer；补充清理内核升级残留的孤立内核模块目录（`/usr/lib/modules/<旧版本>`）与 `systemd-coredump` 系统崩溃转储。
- **Fish 包搜索体验重做**: `se`/`un` 改为基于 `paru -Slq`/`pacman -Qq` 全量包名列表 + `fzf` 原生模糊匹配的交互式搜索安装/卸载，替代原先只能精确匹配包名、且完全不搜 AUR 的 `shelly query` 别名。
- **Noctalia v5 原生空闲超时管理**: 在 `v2/noctalia/noctalia-config.toml` 中配置原生 `[idle]` 策略（300s 自动锁屏、360s 自动关闭显示器熄屏、900s 自动睡眠挂起），实现开箱即用的自动化电源管理。

### Changed / Refactored

- **Niri 快捷键模块化解耦**: 将 `v2/niri/config.kdl` 中庞大的键盘快捷键配置剥离解耦至同目录独立的 `v2/niri/binds.kdl` 文件中，并通过 `include "binds.kdl"` 引入；为所有快捷键与按键分组补充了详细的中英文对照注释，大幅提升配置的可读性与易维护性。
- **Niri 智能边界动作 (`*-or-*`) 升级**: 在 `v2/niri/binds.kdl` 中将方向键全面升级为 Niri 原生 `*-or-*` 智能穿透动作（`focus-column-or-monitor-*`、`focus-window-or-workspace-*`、`move-column-left-or-to-monitor-*`、`move-window-down-or-to-workspace-*`），实现方向键在列内、跨屏幕与跨工作区之间的平滑自然穿透；新增 `Mod+U` 对称工作区导航。
- **Noctalia v5 原生锁屏与依赖清理**: 将 `v2/niri/binds.kdl` 中的锁屏快捷键 `Mod+L` 切换为 Noctalia v5 原生锁屏指令（`noctalia msg session lock`），清理 `install.sh` 中遗留的外部 `swaylock` 依赖与冗余诊断检查。
- **README 快捷键文档同步**: 同步更新 `README.md` 中英文版快捷键对照表，清晰展现智能焦点与智能搬运快捷键。

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
