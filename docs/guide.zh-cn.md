# ChemDraw Skill 安装与运维

本 Skill 适用于任何能读取本地说明文件并执行 shell 命令的 agent。所有操作都经由同一个入口 `skill/chemdraw/scripts/cdx.py`。各 agent 的 Skill 目录、运行时发现顺序、命令白名单和命令参考见 [agent 集成](../skill/chemdraw/references/agent-integration.md)。

## 首次安装

构建运行时需要 64 位 Python 3.10–3.13（3.12 为已测试版本）；安装器本身可在任意 Python 3.9+ 上运行。Python 3.14 及更新版本目前尚未被 `cdxml-toolkit-community` 支持：如果你的机器上只有 3.14，请先安装 3.12（例如 `uv python install 3.12`），或用 `--python <解释器>` 指定。可移植的 CDXML/RDKit 工作不需要任何桌面软件，可在 Windows、macOS 和 Linux 上运行。原生输出需要已激活的 Windows ChemDraw；Office 与 ChemScript 只在对应工作流中才需要。

```bash
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
cd chemdraw-skill
pwsh ./scripts/check_prerequisites.ps1 -Capabilities core,native     # 可选：只读的 Windows 主机环境报告
python scripts/install.py --agent claude agents --runtime            # 预览
python scripts/install.py --agent claude agents --runtime --apply    # 安装 Skill 副本 + 共享运行时
```

`--agent` 可以同时指定 `claude`、`agents`（大多数 agent 都会读取的共享目录 `~/.agents/skills`）、`gemini`、`copilot`、`cursor` 和 `opencode` 中的一个或多个；`--project <仓库>` 改为安装项目级副本，`--destination <目录>` 可安装到任意位置。自动检测找不到合适解释器时用 `--python <解释器>` 指定基础解释器，`--extras` 选择 toolkit 的可选依赖组（默认安装适用于当前操作系统的全部依赖组），`--runtime-dir` 可改变共享 venv 的位置。

安装器会先暂存并校验每一份副本，把已有安装移到共享备份目录（位于所有 Skill 目录之外），失败时自动还原，然后为所有副本安装一次运行时，并写入 `manifest.json` 以便日后检测漂移。重复运行即升级 Skill 并复用 venv。当 venv 不在 `cdx.py` 默认搜索的位置时，安装器会把 `runtime.local.json` 写入每份副本和当前仓库检出目录（该文件已被 Git 忽略），因此在仓库里直接运行 `cdx.py` 也能找到运行时。

运行时的版本是 [runtime.json](../skill/chemdraw/runtime.json) 中钉住的那个精确提交；CI 安装的也是同一提交。如需手动构建运行时：

```bash
python3 -m venv <venv>
<venv>/bin/python skill/chemdraw/scripts/install_runtime.py --extras publication scientific
export CHEMDRAW_MCP_PYTHON=<venv>/bin/python      # 仅当 <venv> 不在 cdx.py 搜索的位置时需要
```

`install_runtime.py --print-requirement` 只打印依赖声明而不安装；`--toolkit-path <检出目录>`（`install.py` 也接受）用于安装本地 toolkit 检出以便开发。

## 检查安装

```bash
python <skill>/scripts/cdx.py doctor              # 版本、可选依赖、漂移、能力矩阵
python <skill>/scripts/cdx.py doctor --native     # 额外执行 ChemScript ping 和一次原生 PNG 渲染
python <skill>/scripts/cdx.py doctor --office     # 额外执行 Word/PowerPoint OLE 探测
```

任何 Python 都可以启动 `cdx.py`，它会自行切换到运行时解释器；无法启动的候选解释器会被跳过。被跳过的探测不算已验证的能力。位数、超时、DECIMER 和故障代码见[运维说明](../skill/chemdraw/references/operations.md)。

在 agent 的命令白名单中放行一次 `python <skill>/scripts/cdx.py` 前缀即可避免反复弹出权限确认；[agent 集成](../skill/chemdraw/references/agent-integration.md#command-permissions)中有示例。

## MCP（可选）

命令行已覆盖全部工具，不需要常驻服务器。偏好 MCP 的客户端可以注册 `<runtime-python> -m cdxml_toolkit.mcp_runtime`（无需 profile 参数）；`cdx.py doctor` 会打印运行时路径。远程 Windows 主机见[运维说明](../skill/chemdraw/references/operations.md#remote-http-only-when-asked)中的 HTTP 一节。

## 开发验证

```powershell
python scripts/validate_distribution.py                           # 仓库检查与安装器测试
python skill/chemdraw/scripts/cdx.py py -m pip install pytest
python skill/chemdraw/scripts/cdx.py py -m pytest skill/chemdraw/tests -q
python skill/chemdraw/scripts/cdx.py regen-signatures             # toolkit 升级后执行
```

请把最终结构回读与视觉比对分开验证。只阅读相关的[工作流](../skill/chemdraw/references/workflow-router.md)；精确接口以[生成的签名](../skill/chemdraw/references/mcp-signatures.md)为准。不要把化学数据、源文件和凭据写进日志或公开仓库。仓库内容采用 [MIT](../LICENSE) 许可；依赖与桌面软件保留各自的条款。
