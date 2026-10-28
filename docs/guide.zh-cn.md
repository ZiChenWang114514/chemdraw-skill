# ChemDraw Skill 安装与运维

本 Skill 适用于任何能读取本地说明文件并执行 shell 命令的 agent。所有操作都经由同一个入口 `skill/chemdraw/scripts/cdx.py`。各 agent 的 Skill 目录、运行时发现顺序、命令白名单和命令参考见 [agent 集成](../skill/chemdraw/references/agent-integration.md)。

## 首次安装

构建运行时需要 64 位 Python 3.10–3.13（3.12 为已测试版本）；安装器本身可在任意 Python 3.9+ 上运行。Python 3.14 及更新版本目前尚未被内置工具包支持：如果你的机器上只有 3.14，请先安装 3.12（例如 `uv python install 3.12`），或用 `--python <解释器>` 指定。可移植的 CDXML/RDKit 工作不需要任何桌面软件，可在 Windows、macOS 和 Linux 上运行。原生输出需要已激活的桌面版 ChemDraw（Windows，或 ChemDraw for macOS）；Office 与 ChemScript 只在对应工作流中才需要。

```bash
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
cd chemdraw-skill
pwsh ./scripts/check_prerequisites.ps1 -Capabilities core,native     # 可选：只读的 Windows 主机环境报告
python scripts/install.py --agent claude agents --runtime            # 预览
python scripts/install.py --agent claude agents --runtime --apply    # 安装 Skill 副本 + 共享运行时
```

`--agent` 可以同时指定 `claude`、`agents`（大多数 agent 都会读取的共享目录 `~/.agents/skills`）、`gemini`、`copilot`、`cursor`、`opencode`、`kimi` 和 `pi` 中的一个或多个；`--project <仓库>` 改为安装项目级副本，`--destination <目录>` 可安装到任意位置。自动检测找不到合适解释器时用 `--python <解释器>` 指定基础解释器，`--extras` 选择 toolkit 的可选依赖组（默认安装适用于当前操作系统的全部依赖组），`--runtime-dir` 可改变共享 venv 的位置。

安装器会先暂存并校验每一份副本，把已有安装移到共享备份目录（位于所有 Skill 目录之外），失败时自动还原，然后为所有副本安装一次运行时，并写入 `manifest.json` 以便日后检测漂移。重复运行即升级 Skill 并复用 venv。当 venv 不在 `cdx.py` 默认搜索的位置时，安装器会把 `runtime.local.json` 写入每份副本和当前仓库检出目录（该文件已被 Git 忽略），因此在仓库里直接运行 `cdx.py` 也能找到运行时。

### macOS

```bash
python3 scripts/install.py --agent claude agents --runtime --opsin --apply   # 同时下载 OPSIN JAR（校验 SHA-256）
python3 scripts/install.py --runtime --mapping --apply                       # 可选：RXNMapper 与 LocalMapper 原子映射（各数百 MB）
python3 skill/chemdraw/scripts/cdx.py doctor --native --office --chemscript
```

ChemDraw for macOS 无需配置，会在 `/Applications` 中自动找到（可用 `CHEMDRAW_EXE` 覆盖）。第一次原生调用时，macOS 会询问是否允许终端或 agent 应用控制 ChemDraw；允许一次即可，之后也可在“系统设置 > 隐私与安全性 > 自动化”中修改。ChemScript 由 ChemDraw、OPSIN 和 RDKit 替代，Office 的 PDF 预览需要已激活的 Microsoft 365。macOS 上的全部差异见[运维说明](../skill/chemdraw/references/operations.md#macos)。

运行时由本仓库的 [`toolkit/`](../toolkit) 目录构建，因此总是与你安装的 Skill 版本一致；CI 也以同样方式构建。没有仓库检出的已安装 Skill 副本会退回到 [runtime.json](../skill/chemdraw/runtime.json) 中钉住的精确提交。如需手动构建运行时：

```bash
python3 -m venv <venv>
<venv>/bin/python skill/chemdraw/scripts/install_runtime.py --extras publication scientific
export CHEMDRAW_MCP_PYTHON=<venv>/bin/python      # 仅当 <venv> 不在 cdx.py 搜索的位置时需要
```

`install_runtime.py --print-requirement` 只打印依赖声明而不安装；`--toolkit-path <目录>`（`install.py` 也接受）可从其他 toolkit 源码目录构建。开发 toolkit 时，可在运行时中执行 `python -m pip install -e "./toolkit[dev]"` 进行可编辑安装。

## 检查安装

```bash
python <skill>/scripts/cdx.py doctor              # 版本、可选依赖、漂移、能力矩阵
python <skill>/scripts/cdx.py doctor --native     # 额外执行 ChemScript ping 和一次原生 PNG 渲染
python <skill>/scripts/cdx.py doctor --office     # 额外执行 PPTX/DOCX ChemDraw-OLE 探测
```

任何 Python 都可以启动 `cdx.py`，它会自行切换到运行时解释器；无法启动的候选解释器会被跳过。被跳过的探测不算已验证的能力。位数、超时、DECIMER 和故障代码见[运维说明](../skill/chemdraw/references/operations.md)。

在 agent 的命令白名单中放行一次 `python <skill>/scripts/cdx.py` 前缀即可避免反复弹出权限确认；[agent 集成](../skill/chemdraw/references/agent-integration.md#command-permissions)中有示例。该前缀同时涵盖 `cdx.py py`，它能在运行时中执行任意 Python，如果觉得范围太大，请改为逐个放行子命令。

处理保密或需要离线的内容时设置 `CHEMDRAW_OFFLINE=1`：此后 PubChem 查询、Java 运行时下载以及 DECIMER 图片上传都会被拒绝（见 [operations](../skill/chemdraw/references/operations.md#environment-variables)）。

## ChemDraw 接口覆盖

本 Skill 为 Windows 上的 ChemDraw 22.2 建立了接口目录，并为每一条说明受支持的程度。目录覆盖四层：ChemScript SDK、ChemDraw 的 COM 自动化对象、CDXML 文档模型和菜单命令。每一条都有一个等级：

- **T1**：有专用工具完成该操作（例如用 `chemdraw_object` 读写 CDXML 元素，用 `chemdraw_chemical_properties` 取 ChemDraw 自己计算的分子式、质量和 ClogP，以及 `structure_to_name`、`convert_cdx_cdxml`）。
- **T2**：可通过通用工具（`execute_chemscript_sdk` 或 `chemdraw_com_call`）调用，并且有一个已在 ChemDraw 上实际运行并核对过结果的配方。
- **T3**：仅有文档，并写明原因（内部支撑代码、隐藏或被禁止的成员，或尚未运行过配方）。不要把 T3 条目当作已验证的功能。

| 层 | 条目数 | T1 | T2 | T3 |
| --- | --- | --- | --- | --- |
| ChemScript SDK | 576 | 7 | 9 | 560 |
| COM 自动化对象 | 1,666 | 8 | 17 | 1,641 |
| CDXML 元素 | 50 | 37 | 0 | 13 |
| 菜单命令 | 159 | 1 | 0 | 158 |

查询目录用 `chemdraw_inventory(layer, query, tier)`，也可以直接打开 `skill/chemdraw/references` 下生成的页面（`interface-chemscript.md`、`interface-com.md`、`interface-cdxml-model.md`、`interface-menu.md`、`recipes-chemdraw.md`）。这些页面用 `python <skill>/scripts/cdx.py regen-catalog` 重新生成。

不能由此推出的结论：上述数字只在 Windows 上的 ChemDraw 22.2.0 中核对过。macOS 只回答 ChemScript 操作和 SDK 的一个子集，其他 ChemDraw 版本可能不同，二进制 CDX 文件通过 ChemDraw 转换而不是直接编辑，菜单命令（例如 NMR 预测）也没有开放为工具，因为 ChemDraw 只有在可见窗口中才能运行它们；唯一的例外是 Analyze Stoichiometry，`stoichiometry_grid` 会在一个短暂显示的独立 ChemDraw 窗口中运行它。`chemdraw_com_call` 拒绝打印、剪贴板、菜单对象和首选项修改，并且只有在明确允许文件访问时才写文件。

## MCP（可选）

命令行已覆盖全部工具，不需要常驻服务器。偏好 MCP 的客户端可以注册 `<runtime-python> -m cdxml_toolkit.mcp_runtime`（无需 profile 参数）；`cdx.py doctor` 会打印运行时路径。远程 Windows 主机见[运维说明](../skill/chemdraw/references/operations.md#remote-http-only-when-asked)中的 HTTP 一节。

## 开发验证

```powershell
python scripts/validate_distribution.py                           # 仓库检查与安装器测试
python skill/chemdraw/scripts/cdx.py py -m pip install pytest
python skill/chemdraw/scripts/cdx.py py -m pytest skill/chemdraw/tests -q
python skill/chemdraw/scripts/cdx.py regen-signatures             # toolkit 改动后执行
cd toolkit; python -m pytest -m "not network" -q                 # toolkit 测试（使用运行时 Python）
```

请把最终结构回读与视觉比对分开验证。只阅读相关的[工作流](../skill/chemdraw/references/workflow-router.md)；精确接口以[生成的签名](../skill/chemdraw/references/mcp-signatures.md)为准。不要把化学数据、源文件和凭据写进日志或公开仓库。仓库内容采用 [MIT](../LICENSE) 许可；依赖与桌面软件保留各自的条款。
