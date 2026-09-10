# ChemDraw Skill 安装与运行

适用于任何能够加载本地指令并调用 MCP 或 Python 的 Agent。先阅读[通用接入说明](../skill/chemdraw/references/agent-integration.md)。客户端不支持 Skill 自动发现时，将 `SKILL.md` 的绝对路径加入项目指令即可；不要假定每个 Agent 共享同一配置格式。

## 首次 Windows 安装

使用 64 位 Python 3.10–3.13（建议单独建立 Python 3.12 环境）。可移植 CDXML/RDKit 功能不需要桌面软件；原生渲染需要已激活的 Windows ChemDraw，Office 和 ChemScript 按需求安装。

```powershell
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
Set-Location .\chemdraw-skill
python -m pip install "cdxml-toolkit-community[windows,office,chemscript] @ git+https://github.com/ZiChenWang114514/cdxml-toolkit-community.git@57db286ea4fa1c74a524e7a329dd5ba3f39dc21e"
```

```powershell
$python = (Get-Command python).Source
.\scripts\check_prerequisites.ps1 -Python $python -Capabilities core
# Use your client's actual Skill discovery path, or load this folder explicitly.
.\scripts\install.ps1 -Destination "$HOME/.agents/skills/chemdraw" -Python $python
.\scripts\install.ps1 -Destination "$HOME/.agents/skills/chemdraw" -Python $python -Apply
```

安装器先输出方案，`-Apply` 后备份并安装；默认不更改 Agent 配置。macOS/Linux 的 MCP 服务使用同样的 Python 参数，Skill 文件夹直接复制即可。通用服务启动参数为 `-m cdxml_toolkit.mcp_runtime --profile codex`；这里的配置名是兼容标识。

## 验证与故障处理

```powershell
.\skill\chemdraw\scripts\health_check.ps1 -Python $python -SkipNativeChemDraw
# Native ChemDraw + ChemScript, without Office:
.\skill\chemdraw\scripts\health_check.ps1 -Python $python -SkipOffice
# Complete licensed workstation checks:
.\skill\chemdraw\scripts\health_check.ps1 -Python $python
```

成功标记为 `ChemDraw agent integration: OK`。通用检查不验证特定客户端的注册；刷新 Agent 的工具列表并调用 `get_toolkit_capabilities()`。按需检查 `core,native,chemscript,office,decimer`；不要将跳过的能力当作通过。原生位数、超时、远程服务和 DECIMER 的详细处理见 [operations](../skill/chemdraw/references/operations.md)。

<details>
<summary>Optional Codex client adapter / 可选客户端适配</summary>

Only for this client, after its CLI is already installed:

```powershell
.\scripts\install.ps1 -Python $python -ConfigureMcp
.\scripts\install.ps1 -Python $python -ConfigureMcp -Apply
codex mcp get cdxml-toolkit --json
.\skill\chemdraw\scripts\health_check.ps1 -Python $python -SkipNativeChemDraw -CheckCodex
```

This opt-in adapter uses `$HOME/.codex/skills/chemdraw` (or `CODEX_HOME`) and preserves the client's configuration. `configure_mcp.ps1` configures only this client. Other agents use their own MCP registration settings.

</details>

## Streamable HTTP

在客户端注册主机提供的 MCP URL 与认证信息，具体格式遵循客户端设置。服务参数和访问控制见 [operations](../skill/chemdraw/references/operations.md#streamable-http-and-metrics)。

## 开发验证

```powershell
python scripts/validate_distribution.py
python -m pytest skill/chemdraw/scripts -q
```

结构读回与视觉对照分别检查。仅按请求读取[工作流指南](../skill/chemdraw/references/workflow-router.md)；精确接口以[生成签名](../skill/chemdraw/references/mcp-signatures.md)为准。化学内容、源文件与凭据不得进入日志或公开仓库。项目自有内容采用 [MIT](../LICENSE)，依赖与桌面软件各自遵循原有条款。
