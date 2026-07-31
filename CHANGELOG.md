# Changelog

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
