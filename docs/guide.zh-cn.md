# 项目维护指南

[English](guide.md)

这是安装、理解、测试和运行本项目的唯一详细指南。根目录 README 有意保持简短。

## 安装

### 选择所需功能组合

| 功能 | 额外要求 |
| --- | --- |
| CDXML 解析、名称解析和常规绘图 | Codex、Python 运行时、`cdxml-toolkit-community` 和 MCP SDK |
| 原生 PNG 渲染、CDX 转换和 ChemDraw 清理 | 已获得许可的 Windows 桌面版 ChemDraw，且 COM 注册能够正常工作 |
| 分子比较和完整 ChemScript SDK 访问 | 托管与原生 ChemScript DLL；较旧的 32 位版本可能需要独立的辅助 Python |
| DOCX 或 PPTX 中可编辑的 ChemDraw 对象 | 相应的桌面版 Microsoft Word 或 PowerPoint 应用程序 |
| 离线图像识别 | DECIMER 模型权重，以及额外的内存、磁盘空间和下载时间 |
| 从另一台计算机访问 | 已配置的 Windows 服务器，以及通过加密网络提供的、经过身份验证的 Streamable HTTP |

在具体工作流需要之前，Office、DECIMER 和 ChemScript 辅助环境均为可选组件。

### 主机前提条件

- 可移植 CDXML 和 RDKit 工作流可以在 Windows、macOS 和 Linux 上运行。ChemDraw COM、ChemScript 和可编辑 Office 对象等原生功能需要 64 位 Windows 10 或 Windows 11 主机。
- 随附的安装器与检查器需要 Windows PowerShell 5.1 或 PowerShell 7。可移植软件包命令可以在对应平台的常用 shell 中运行。
- `codex` 命令能够正常工作，并且已经完成 Codex 登录。请参阅 [Codex CLI 官方指南](https://developers.openai.com/codex/cli)。
- 只有原生功能需要已获得许可的 Windows 桌面版 ChemDraw。仅浏览器版本的 ChemDraw 不提供 COM 或 ChemScript。ChemDraw 22.0 已通过测试；请根据安装的版本查阅 [Revvity 当前系统要求](https://support.revvitysignals.com/hc/en-us/articles/43424307511572-ChemDraw-What-are-the-System-requirements-for-ChemDraw-ChemOffice)。
- 64 位 Python 3.10-3.13 运行时。Python 3.12 已通过测试，推荐使用专用 Conda 环境。
- [Git](https://git-scm.com/downloads)；如果无法使用 Git，也可以下载 GitHub ZIP 文件。
- 对于完整 Python 环境，至少 10 GiB 可用磁盘空间和 8 GiB 内存是较为实际的最低配置。本地使用 DECIMER 时，建议配备 16 GiB 内存和更多可用空间。
- 首次安装需要网络连接，以获取仓库和 Python 依赖项。本地 DECIMER 还需要单独下载模型。

经过测试的运行时是 `cdxml-toolkit-community==0.7.0a1`，支持 MCP SDK 1.x 和 2.x。主 MCP 环境应保持 64 位。较旧的 ChemScript DLL 为 32 位时，请配置独立的辅助环境，不要改变主运行时。

### 首次 Windows 安装

1. 安装并激活桌面版 ChemDraw。手动打开 ChemDraw，创建并保存一个小型文档，然后关闭应用程序。本项目不会安装或修改产品许可证。
2. 使用下面最新的 Windows 官方命令安装 Codex，运行 `codex --version`，启动 `codex` 并完成登录。在阻止运行下载脚本的受管理计算机上，请让管理员按照 [Codex CLI 官方指南](https://developers.openai.com/codex/cli)中的 Windows 方法操作，不应关闭组织的安全控制措施。

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

3. 安装 [64 位 Miniconda](https://docs.conda.io/projects/conda/en/stable/user-guide/install/windows.html) 和 Git。打开 **Anaconda PowerShell Prompt**，确保可以使用 `conda`。
4. 克隆仓库并创建隔离的运行时：

```powershell
Set-Location "$HOME\Documents"
git clone https://github.com/ZiChenWang114514/codex-chemdraw-skill.git
Set-Location .\codex-chemdraw-skill

conda create -n cdxml python=3.12 pip -y
conda activate cdxml
python -m pip install --upgrade pip
python -m pip install "cdxml-toolkit-community[windows,office,chemscript] @ git+https://github.com/ZiChenWang114514/cdxml-toolkit-community.git@57db286ea4fa1c74a524e7a329dd5ba3f39dc21e"
python -m pip check
python -c "import cdxml_toolkit, mcp, rdkit, win32com.client; print('Python runtime OK')"
$python = (python -c "import sys; print(sys.executable)").Trim()
```

软件包安装包含科学计算、Office 文件处理、PDF、图像和机器学习依赖项，所需时间可能明显长于小型 Python 软件包。这些 Python 库不会安装 Microsoft Word 或 PowerPoint；可编辑 Office 对象工作流仍要求安装相应的桌面应用程序。

安装前先运行只读的前提条件报告：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
& .\scripts\check_prerequisites.ps1 -Python $python -Capabilities core,native,chemscript,office
```

`PASS` 表示满足检查要求，`WARN` 表示可选项目或需要手动处理的项目，`FAIL` 表示需要处理，`SKIP` 表示未能得出结论。检查器不会启动 ChemDraw、检查分子文件或改变系统配置。添加 `-Json` 可获得机器可读报告。仅安装可移植功能时使用 `-Capabilities core`；只有在安装软件包之前进行早期主机检查时，才应使用 `-SkipPythonPackages`。

如果需要分子比较或 ChemScript SDK 工具，请配置并测试桥接程序：

```powershell
& $python -m cdxml_toolkit.chemdraw.chemscript_bridge configure
& $python -m cdxml_toolkit.chemdraw.chemscript_bridge ping
```

32 位 ChemScript 安装没有兼容的辅助 Python 时，请激活 `cdxml` 并运行 `cdxml-doctor --no-tests`，然后按照其中针对辅助环境的说明操作。主 `cdxml` 环境应保持 64 位。

先预览 Skill 安装，检查报告中的 Python 和目标位置，然后正式安装：

```powershell
& .\scripts\install.ps1 -Python $python -ConfigureMcp
& .\scripts\install.ps1 -Python $python -Apply -ConfigureMcp
```

不提供 `-Apply` 时，安装程序只会报告拟使用的路径，不会修改这些路径中的内容。提供 `-Apply` 后，程序会先将现有 Skill 保存在 `$HOME\.codex\backups\skills\chemdraw`，再安装到 `$HOME\.codex\skills\chemdraw`。`-ConfigureMcp` 还会保留并更新 `$HOME\.codex\config.toml`。

重新启动 Codex 并验证注册情况：

```powershell
codex mcp get cdxml-toolkit --json
& "$HOME\.codex\skills\chemdraw\scripts\check_prerequisites.ps1" -Python $python -Capabilities core,native,chemscript,office
```

选择与已安装应用程序相符的健康检查：

```powershell
# 可移植代码、软件包、测试和 MCP 检查；不检查原生应用程序。
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python -SkipNativeChemDraw

# 原生 ChemDraw PNG 和 ChemScript 检查；不检查 Word 或 PowerPoint。
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python -SkipOffice

# 完整的原生功能、ChemScript、PowerPoint 和 Word 验证。
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python
```

执行原生检查之前，请关闭手动打开的 ChemDraw 和 Office 应用程序。所选健康检查只有以 `ChemDraw/Codex integration: OK` 结束时才算成功。

### 安装故障处理

- 无法识别 `git`、`conda` 或 `codex`：安装后重新打开 PowerShell，并确认使用了正确的用户账户。使用 Anaconda PowerShell Prompt 运行 Conda。
- 出现 `No usable Python runtime found`：从 `cdxml` 环境重新计算 `$python`，并通过 `-Python` 传入该准确路径。
- 软件包导入或 `pip check` 失败：创建新的 `cdxml` 环境，并在其中安装经过测试的社区版本；避免与无关项目共用该环境。
- 缺少 `ChemDraw.Application`：确认已安装 Windows 桌面版 ChemDraw，打开一次；如果仍然缺少 COM 注册，请修复安装。
- ChemDraw 已激活但许可证检查失败：手动打开并保存一个测试文档，关闭 ChemDraw，然后重新运行所选原生检查。不要为了诊断而改动正常工作的许可证。
- ChemScript 文件存在但 `ping` 失败：重新运行 `configure`，检查 DLL 位数，并为 32 位版本使用独立的辅助 Python。
- 未安装 Office：使用 `-SkipOffice`；只有明确希望省略全部原生检查时，才使用 `-SkipNativeChemDraw`。
- Codex 看不到工具：完整重启 Codex，运行 `codex mcp get cdxml-toolkit --json`，随后运行 `codex doctor --all`。
- 缺少本地 DECIMER 模型：常规绘图和 ChemDraw 工作流仍可使用。只有需要离线图像识别时才安装模型。

### 运行时发现

MCP 运行时按以下顺序解析可执行文件和应用程序：

1. 明确指定的工具参数。
2. 受支持的环境变量。
3. 当前激活的 Python 或 Conda 环境。
4. Windows 注册表和常见安装位置。
5. 说明缺失内容的结构化错误。

仓库代码中不应硬编码用户名、Conda 根目录、ChemDraw 目录或 Office 目录。

### 激活与位数

ChemDraw 桌面应用程序已激活，并不能保证所有自动化接口均可使用。`diagnose_runtime()` 会分别报告各项功能状态；完整健康检查还会添加临时的原生 PNG、ChemScript 以及 PPTX/DOCX OLE 检查。

原生工作流失败时，请确认主 Python 为 64 位，并且任何旧版 ChemScript 辅助程序都与其 DLL 体系结构相符，然后运行适当的检查：

```powershell
.\skill\chemdraw\scripts\health_check.ps1 -Python $python -SkipOffice
codex doctor --all
```

## 架构

Skill 采用渐进式披露方式，使常规提示词只载入所需上下文：

1. `SKILL.md` 提供触发元数据、科学约束、隐私规则和任务路由。
2. 工作流参考文档说明绘图、反应、识别、Office、分析和诊断任务的完整步骤。
3. 各领域参考文档提供决策规则和失败模式。
4. 自动生成的 API 参考文档提供准确的可调用签名。
5. 清单分片支持按模块名或函数名进行定向审计。

公共 MCP 工具通过统一扩展注册表注册，并在隔离的工作进程中执行，同时设有强制超时和结构化错误。新工具返回 `ok`、`outputs`、`warnings` 和 `metadata`；已有工具继续保留兼容的名称与约定。

分子比较通过已安装的 `ChemScriptBridge` 解析两个输入；在可用时使用 ChemScript InChI 检查精确身份，并计算考虑手性与仅考虑连接关系的 RDKit 指纹。批量比较会复用同一个桥接进程，最多接受 256 个分子对，并且不会在结果行中重复来源表示。

ChemScript SDK 适配器会在运行时反射已安装的托管程序集。它会编目 SDK 声明的每一个公共类型和成员，随后同时报告目录覆盖情况与执行路径覆盖情况。声明式程序可以构造对象、调用静态或实例方法、读取或写入成员、索引和枚举集合，以及释放对象。文件访问、替换现有文件和 SWIG 指针/句柄互操作分别需要明确启用相应选项。这样可以让每一个公共成员都拥有可发现的记录，同时将原生互操作与 MCP 进程隔离。

经过测试的服务器运行时支持 MCP Python SDK 1.x 和 2.x。兼容处理由 `cdxml-toolkit-community==0.7.0a1` 提供，CI 会验证这两代受支持的 SDK。

自动生成的签名和清单文件必须根据源代码重新生成。不要在说明性文档中手工重复这些签名。

### Streamable HTTP

stdio 保持默认模式，不需要网络监听器。若要让另一台计算机访问已获得许可的 ChemDraw 工作站，请生成持有者令牌并启动可选 HTTP 模式。下面的示例监听所有网络接口，但只接受 `--allowed-host` 中提供的工作站地址：

```powershell
$env:CHEMDRAW_MCP_HTTP_API_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
python .\skill\chemdraw\scripts\mcp_server.py `
  --transport streamable-http `
  --host 0.0.0.0 `
  --port 8029 `
  --allowed-host "192.168.1.20:*"
```

在客户端计算机上，将相同令牌放入另一个本地环境变量，并注册该 URL：

```powershell
$env:CHEMDRAW_REMOTE_TOKEN = "<same token>"
codex mcp add chemdraw-remote `
  --url "http://192.168.1.20:8029/mcp" `
  --bearer-token-env-var CHEMDRAW_REMOTE_TOKEN
```

当流量离开完全可信的仅主机网络时，请使用 Tailscale、WireGuard 或 HTTPS 反向代理。普通 HTTP 不会加密持有者令牌。非环回监听如果没有令牌会拒绝启动；通配符监听还要求明确指定允许的 Host 模式。公开的 `/health` 响应只包含进程状态。配置身份验证后，`/metrics` 需要持有者令牌，并会导出调用耗时、超时、工作进程故障、活动工作进程数量和本地 ChemDraw 队列指标。指标标签只包含已注册的工具名称和稳定状态码。

## 开发与验证

提交更改前，请运行仓库验证和完整的 Skill 测试套件：

```powershell
python scripts/validate_distribution.py
python -m pytest skill/chemdraw/scripts -q -v
.\skill\chemdraw\scripts\health_check.ps1 -SkipNativeChemDraw
```

针对性测试必须覆盖有效输入、无效参数、缺失文件、拒绝覆盖、超时处理和结构化失败。发布验证会检查打包目录、文档链接、自动生成的参考文档、可移植性和意外出现的密钥模式。

涉及 ChemDraw 或 Office 的声明，需要在已获得许可的本地安装环境中验证，并生成能够成功打开或渲染的真实输出。测试 CDXML 渲染行为时，应使用 ChemDraw 原生渲染器。远程 DECIMER 测试需要主动启用，并且必须使用非敏感测试文件。

GitHub Actions 运行可移植检查。机器专用的原生检查继续在本地执行，因为托管运行器不包含获得许可的 ChemDraw 或 Office 应用程序。

## 安全与隐私

- 远程图像识别要求 `confirm_upload=true`；默认行为是拒绝上传。
- 远程输入必须是能够真实解码的图像，并受到大小、响应和超时限制。
- 修改工具默认生成新的输出路径，并拒绝意外覆盖。
- 临时文件和输出继承本地文件系统权限；分享前请先检查。
- 绝对不要提交 API 密钥、凭据、个人实验数据、专有文档或受许可约束的二进制文件。
- HTTP 身份验证值保留在父服务器中，并会从工作进程环境中移除。
- 在根据来源核查并完成化学验证之前，应将识别或生成的化学结构视为待验证假设。

## 第三方软件与许可

仓库自行编写的代码和文档采用 MIT 许可证。仓库不分发 ChemDraw、Microsoft Office、Codex、DECIMER 权重或其他专有组件。

- [ChemDraw](https://revvitysignals.com/products/research/chemdraw) 是 Revvity Signals 授权的专有软件。
- [cdxml-toolkit-community](https://github.com/ZiChenWang114514/cdxml-toolkit-community) 是本 Skill 使用的维护版运行时，并延续上游 `cdxml-toolkit` 项目。
- [DECIMER](https://github.com/Kohulan/DECIMER-Image_Classifier) 组件和模型权重遵循其上游条款。
- Codex 和 Microsoft Office 是可选的外部运行时，并受各自供应商条款约束。

重新分发前，请检查环境中所用依赖项准确版本的许可证元数据。项目历史与发布说明应保存在 Git 和 GitHub Releases 中，不应建立重复的 Markdown 记录文档。
