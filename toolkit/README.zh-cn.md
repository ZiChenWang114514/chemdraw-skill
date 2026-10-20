[English](README.md) · [简体中文](README.zh-cn.md)

# CDXML Toolkit — ChemDraw MCP 服务器与 Python 化学绘图

![CDXML Toolkit：可编辑的分子结构与反应路线](assets/readme/overview.svg)

面向任意 Agent 的 MCP 与 Python 化学绘图工具包。解析和比较分子、绘制反应路线与机理、制作原生 TLC 和装置图、分析已处理的一维 NMR 数据，并交付可编辑 CDXML 或 Office 中的 ChemDraw 对象。

**平台支持：** CDXML 与 RDKit 核心功能可在 Windows、macOS 和 Linux 使用。ChemDraw 原生渲染、ChemScript 和 Office 可编辑对象需要已激活的 Windows 桌面版 ChemDraw；Office 功能还需要相应桌面应用。

[验证状态](https://github.com/ZiChenWang114514/cdxml-toolkit-community/actions/workflows/validate.yml) · [主打案例](#主打案例) · [快速开始](#快速开始) · [接入任意-agent](#接入任意-agent) · [工具参考](docs/mcp-tools.md) · [MIT 许可证](LICENSE)

## 主打案例

从实际图片和数据出发，直接查看效果、原图对照和可编辑文件。

| 案例 | 展示内容 | 交付范围 |
| --- | --- | --- |
| [论文反应路线](#paper-scheme-demo) | 五个结构、条件、产率与波浪键 | 完整复刻，非像素一致 |
| [Sceptrin 反应机理](#mechanism-demo) | 八个结构、电子箭头、电荷与条件 | 完整复刻，非像素一致 |
| [原生 TLC](#tlc-demo) | 可编辑泳道、斑点与 Rf | 可运行示例 |
| [原生装置图](#apparatus-demo) | 原生 ChemDraw 模板组装 | 可运行示例 |
| [实验 NMR 谱图](#nmr-demo) | 真实一维数据与可编辑谱图 | 可运行示例 |
| [模拟反应动力学](#kinetics-demo) | 数值数据转为可编辑曲线 | 可运行示例 |
| [复杂合成：101–112](#synthesis-101-demo) | 完整原生路线图与机理箭头 | 立体化学待完整验收；非 1:1 |
| [复杂合成：113–122](#synthesis-113-demo) | 完整原生路线图与机理箭头 | 立体化学待完整验收；非 1:1 |

<a id="stereo-reconstruction-demo"></a>

### 20 个结构：修复跨软件立体信息不一致

![20 个结构合成路线的 ChemDraw 原生复刻](assets/readme/stereo-reconstruction/native.png)

忠实于原图画法的版本有 16 个结构在 ChemScript 与 RDKit 中读法不同。修复版经原生保存后 **20/20 一致**，并保持复核后的目标结构。产物 **1** 改用了显式楔键，因此外观与原图有差异；同尺度墨迹 IoU 为 **0.6960**。这不是像素级 1:1，也不是实验绝对构型的独立验证。

[下载 CDXML](assets/readme/stereo-reconstruction/reconstruction.cdxml) · [踩坑复盘、改进流程与版权说明](assets/readme/stereo-reconstruction/CASE.md) · [逐结构证据与软件版本](assets/readme/stereo-reconstruction/verification.json)

X-ray 保留原图裁片。论文衍生图像不适用仓库的 MIT 许可，使用前请查阅案例中的来源与权利说明。

**已提供可运行的增量流程：**关联化学与绘图记录、验证缓存依赖、按变化局部检查，并分别验收原图版和兼容版。一次三处标题字号修改回放中，原生调用从8次减至2次，耗时从33.53秒降至8.88秒；这不是整图识别提速的结论。[原图画法版](assets/readme/stereo-reconstruction/source-oriented.cdxml) · [使用流程](https://github.com/ZiChenWang114514/chemdraw-skill/blob/main/skill/chemdraw/references/incremental-reconstruction.md) · [实测证据](assets/readme/stereo-reconstruction/incremental-verification.json)。

<a id="paper-scheme-demo"></a>

### 论文反应路线

**将论文反应图转为可编辑的 ChemDraw 文档。** 示例保留了原图中的五个结构、反应条件、产率和化合物编号。

**论文原图**

![论文原图，包含 13a、14、15、16 及 17a/17b 共用结构](assets/readme/paper-replica/original.png)

**可编辑复刻｜ChemDraw 原生输出**

![ChemDraw 可编辑复刻，保留原图取向、反应条件与化合物编号](assets/readme/paper-replica/replica.png)

[下载可编辑 CDXML](assets/readme/paper-replica/replica.cdxml) · [查看逐结构左右对照](assets/readme/paper-replica/structure-comparison.png) · [案例来源与验证范围](assets/readme/paper-replica/provenance.json)

从保存的 CDXML 中重新解析出的五个结构，与经核对的参考结构一致。17a/17b 共用的波浪键保留原图中未指定构型的表示。

**经过视觉复核，可继续编辑；尚非逐像素 1:1。** 字体、箭头和部分线条几何仍有差异。保存前后的结构一致，并不能独立证明图中所有细节都识别正确。

<a id="mechanism-demo"></a>

### Sceptrin 反应机理

**原始截图**

![Reference mechanism showing compounds 192 through 199](assets/readme/mechanism/reference.png)

**ChemDraw 重绘**

![Native ChemDraw reconstruction with eight structures, electron arrows and reaction conditions](assets/readme/mechanism/native.png)

[可编辑 CDXML](assets/readme/mechanism/mechanism.cdxml) · [原生 CDX](assets/readme/mechanism/mechanism.cdx) · [左右对照](assets/readme/mechanism/comparison.png) · [验证与原图限制](assets/readme/mechanism/provenance.json)

八个编号结构和六个氯离子经过实际 ChemDraw CDXML → CDX → CDXML 保存后，分子组成、图示立体化学和形式电荷保持一致。未定义的 R 保留为通用取代基。已进行视觉核对，**并非逐像素一致**：字体、电子箭头路径、部分桥键几何以及离域电荷标记位置仍有差异；未推测补全原图被裁掉的重结晶说明。

<a id="tlc-demo"></a>

### 原生 TLC

原生 TLC 板、泳道和斑点，Rf 数值为示例。

![原生 TLC](assets/readme/scientific/tlc.png)

[可编辑 CDXML](assets/readme/scientific/tlc.cdxml) · [运行示例](docs/scientific-workflows.md) · [数据与模板来源](assets/readme/scientific/provenance.json)

<a id="apparatus-demo"></a>

### 原生装置图

由 ChemDraw 自带装置模板组装，保留原生可编辑图形。

![原生装置图](assets/readme/scientific/apparatus.png)

[可编辑 CDXML](assets/readme/scientific/apparatus.cdxml) · [运行示例](docs/scientific-workflows.md) · [数据与模板来源](assets/readme/scientific/provenance.json)

<a id="nmr-demo"></a>

### 实验 NMR 谱图

真实已处理的一维 NMR 数据；支持寻峰和指定区间积分，未进行自动原子归属。

![实验 NMR 谱图](assets/readme/scientific/nmr.png)

[可编辑 CDXML](assets/readme/scientific/nmr.cdxml) · [运行示例](docs/scientific-workflows.md) · [数据与模板来源](assets/readme/scientific/provenance.json)

<a id="kinetics-demo"></a>

### 模拟反应动力学

明确标注为模拟的一阶衰减曲线，展示数据到科研图的转换。

![模拟反应动力学](assets/readme/scientific/kinetics.png)

[可编辑 CDXML](assets/readme/scientific/kinetics.cdxml) · [运行示例](docs/scientific-workflows.md) · [数据与模板来源](assets/readme/scientific/provenance.json)

<a id="synthesis-101-demo"></a>

### 复杂合成：101–112

**完整路线图与可编辑结构。** 已包含全部编号、反应条件和机理箭头。原生保存保持连接关系、电荷、同位素和双键几何；桥头立体信息尚未完整验收，字体与线条几何也有差异，不能视为严格 1:1。

![复杂合成：101–112](assets/readme/synthesis-101-112/reconstructed.png)

[完整 CDXML](assets/readme/synthesis-101-112/figure.cdxml) · [原图与复刻对照](assets/readme/synthesis-101-112/comparison-full.png) · [验收范围与来源](assets/readme/synthesis-101-112/provenance.json)

<details>
<summary>展开原图与复刻对照</summary>

![复杂合成：101–112 — comparison](assets/readme/synthesis-101-112/comparison-full.png)

</details>

<a id="synthesis-113-demo"></a>

### 复杂合成：113–122

**完整路线图与可编辑结构。** 已包含全部编号、反应条件和机理箭头。原生保存保持连接关系、电荷、同位素和双键几何；桥头立体信息尚未完整验收，字体与线条几何也有差异，不能视为严格 1:1。

![复杂合成：113–122](assets/readme/synthesis-113-122/reconstructed.png)

[完整 CDXML](assets/readme/synthesis-113-122/figure.cdxml) · [原图与复刻对照](assets/readme/synthesis-113-122/comparison-full.png) · [验收范围与来源](assets/readme/synthesis-113-122/provenance.json)

<details>
<summary>展开原图与复刻对照</summary>

![复杂合成：113–122 — comparison](assets/readme/synthesis-113-122/comparison-full.png)

</details>

## 复刻范围与结构核对

两张复杂合成图均提供完整布局、原生分子结构、文字、括号和电子箭头。结构由可编辑的原子、键及可展开缩写构成，没有用嵌入截图或轮廓描摹代替分子。

| 检查项目 | 当前结果 |
| --- | --- |
| 原生保存后的连接、元素、电荷、同位素和双键几何 | 两张图的保存前后检查通过 |
| 完整立体化学 | 尚未通过；部分桥头中心的 RDKit 与 ChemScript 读回结果相反 |
| 原图视觉对照 | 已查看原生预览和整图对照；字体、箭头和部分线条几何仍有差异 |
| 严格逐像素 1:1 | 未达到 |

保存前后一致不等于原图识别绝对正确。105–109、115–120 和 121 存在已指定构型的分歧；原图中部分展开链与缩写定义也需进一步核实。复刻保留各处图示内容，未擅自改成自洽路线。[逐原子检查记录](examples/paper-reconstructions/stereochemistry-check.json) 给出组件哈希及对应关系，便于复核；没有分歧也不能独立证明原图构型正确。

安装运行时后，可离线重建这两张布局，无需再次调用 DECIMER：

```powershell
python examples/paper-reconstructions/rebuild.py ./paper-figures-output
```

请使用新的输出目录。此命令组装已保存的结构组件；原生预览仍需 Windows ChemDraw。[重建示例与限制](examples/paper-reconstructions/README.md)。原论文图片的版权不随软件许可证转授。

## 论文绘图与化学处理

| 工具或功能 | 用途 |
| --- | --- |
| `compose_chemical_figure` | 使用明确坐标组装结构、多种反应箭头、富文本、编号、网格和原生模板 |
| `rdkit_workbench` | 检查原子编号与 CIP 标签，明确修改构型，进行有限枚举、MCS 和 R-group 分解 |
| `compare_figure_images` | 保存左右对照与图像差异，供实际视觉复核 |
| TLC 与装置 | 原生板、泳道和斑点；Rf 测量；安装版 ChemDraw 模板的可编辑组装 |
| NMR 与科研绘图 | 已处理一维谱的寻峰与指定区间积分；数值数据转为可编辑曲线 |
| Office 与实验记录 | 嵌入或提取 ChemDraw OLE 对象；处理 ELN、SciFinder RDF、LCMS/NMR 报告 |

结构检查应读取最终 CDXML。波浪键保持未指定，增强立体化学 AND/OR/ABS 分组单独处理。有效 SMILES、楔线数量或图像相似度不能证明原图识别正确。当前不包含自动 NMR 原子归属、完整 FID 处理或反应机理的自动证明。新绘制的自由基及非四面体立体表示若未受支持，应使用经过验证的原生模板。

**版本说明：** 论文绘图等新增能力需要下面的源码安装，不包含在 `v0.7.0a1` 发布包中。

## 快速开始

需要 64 位 Python 3.10–3.13；暂不支持 Python 3.14。无需 ChemDraw 即可使用可移植核心；原生功能的要求见页首。

```powershell
conda create -n cdxml python=3.12 pip -y
conda activate cdxml
git clone https://github.com/ZiChenWang114514/cdxml-toolkit-community.git
Set-Location .\cdxml-toolkit-community

# 两个发行包使用同一 cdxml_toolkit 导入名称。
pip uninstall -y cdxml-toolkit
pip install -e ".[all]"
cdxml-doctor --no-tests
```

默认安装包含 CDXML、RDKit 和 MCP 核心。可选依赖组包括 `windows`、`office`、`chemscript`、`analysis`、`scientific`、`image`、`decimer`、`opsin`、`http`、`all` 和 `dev`；按需要安装即可。

不需要本地源码目录时，也可以直接安装：

```powershell
pip install "cdxml-toolkit-community[all] @ git+https://github.com/ZiChenWang114514/cdxml-toolkit-community.git@main"
```

<details>
<summary>ChemScript 与 Java 设置</summary>

`cdxml-doctor --no-tests` 只检查环境。需要交互式配置兼容的 ChemScript 环境时，运行：

```powershell
cdxml-doctor --no-tests --configure-chemscript
cdxml-doctor --json
```

ChemScript 为可选组件。OPSIN 可在具备 Java 时离线解析 IUPAC 名称。发行包不附带 JRE；运行时先检查 `JAVA_HOME` 和 `PATH` 中的 `java`。使用已批准的本地归档时，可显式提供路径和完整性信息：

```powershell
$env:CDXML_TOOLKIT_JRE_ZIP = "C:\installers\temurin-jre.zip"
$env:CDXML_TOOLKIT_JRE_SHA256 = "approved sha256"
cdxml-doctor --no-tests
```

安装前检查归档大小、解压大小、路径、链接及提供的 SHA-256。
</details>

## 接入任意 Agent

启动完整的 39 工具 stdio 服务：

```powershell
cdxml-mcp
```

在客户端的 MCP 配置中填写 Python 解释器和参数。常见 JSON 格式如下；配置位置及具体语法以客户端为准：

```json
{
  "mcpServers": {
    "chemdraw": {
      "command": "C:\\Users\\YOU\\miniconda3\\envs\\cdxml\\python.exe",
      "args": ["-m", "cdxml_toolkit.mcp_runtime"]
    }
  }
}
```

重启 Agent 后尝试：“解析阿司匹林，绘制 CDXML，并生成 PNG 预览。”

论文复刻与实验绘图可配合客户端无关的 [ChemDraw Skill](https://github.com/ZiChenWang114514/chemdraw-skill)。历史配置名 `codex` 仅作为兼容接口保留，不限制 Agent 类型。支持项目指令的客户端也可加载 [CLAUDE.md](CLAUDE.md)，按其中要求取得可靠结构、使用 OCSR、检查结构修改并保留化学语义。

## 运行方式与工具配置

![从结构来源到受控操作，再到经核对的 ChemDraw 或 Office 输出](assets/readme/workflow.svg)

工具调用运行在独立工作进程中，具备可配置超时和结构化错误；ChemDraw、Word 与 PowerPoint 共享串行资源协调。输出工具检查文件并防止意外覆盖。指标只记录调用数量、耗时、超时、失败及队列长度，不记录分子内容或工具参数。Agent 可先调用 `get_toolkit_capabilities` 检查本机能力。

| 配置 | 工具数 | 适用范围 |
| --- | ---: | --- |
| `core` | 16 | 兼容核心与能力发现 |
| `office` | 21 | Office 检查、替换、模板与批量嵌入 |
| `analysis` | 20 | 实验发现、LCMS、实验记录与 SciFinder RDF |
| `chemscript` | 20 | 分子比较与受控 ChemScript SDK 访问 |
| `codex` | 39 | 完整本地与远程工具集合，兼容名称 |

[MCP 工具参考](docs/mcp-tools.md)和 [JSON Schema](docs/mcp-schema.json)提供准确签名，CI 检查生成文件的一致性。

## Streamable HTTP

本地默认使用 stdio。安装 `http` 依赖后，已激活的 Windows 工作站可为受信任的远程计算机提供服务：

```powershell
$env:CHEMDRAW_MCP_HTTP_API_KEY = "generate-a-long-random-value"
cdxml-mcp --transport streamable-http --host 0.0.0.0 --port 8029 `
  --allowed-host chemdraw-host.example:8029 `
  --allowed-origin https://trusted-client.example
```

远程监听需要 bearer 密钥与明确的主机白名单，并应通过加密网络连接。`/health` 不含分子数据；远程可达时，`/metrics` 要求身份验证。DECIMER 默认不上传图像；远程识别需要 `confirm_upload=true`，并检查图像解码及请求、响应大小。

## 命令行

| 命令 | 用途 |
| --- | --- |
| `cdxml-mcp` | 完整 MCP 运行时，默认提供 39 个工具 |
| `cdxml-mcp-core` | 兼容的 15 工具核心服务 |
| `cdxml-doctor` | 只读诊断、测试及显式 ChemScript 配置 |
| `cdxml-render` | 将 JSON、YAML 或紧凑文本绘制为 CDXML |
| `cdxml-image` | 将 CDXML 渲染为 PNG 或 SVG |
| `cdxml-merge` / `cdxml-layout` | 合并路线或清理布局 |
| `cdxml-ole` | 在 PPTX 或 DOCX 中嵌入可编辑 ChemDraw 对象 |
| `cdxml-lcms` / `cdxml-nmr` | 解析仪器报告 |
| `cdxml-mcp-docs` | 重新生成 Markdown 和 JSON 工具参考 |

路线渲染器支持 YAML、反应 JSON 和紧凑文本语法，见[案例目录](experiments/scheme_dsl/showcase/INDEX.md)。实验绘图命令与输入示例见[科研工作流](docs/scientific-workflows.md)。

## 开发与验证

```powershell
python -m pip install -e ".[dev,windows,office,analysis,image,scientific]"
python -m pytest -m "not network" -q
python -m build
python -m twine check dist/*
```

托管 CI 检查 Python 3.10–3.13、MCP SDK 1.x 与 2.x、生成参考、可移植测试和发行包。原生 ChemDraw、ChemScript、Word 与 PowerPoint 检查需要具备许可证的 Windows 工作站。

参与开发或发布前，请阅读[贡献指南](.github/contributing.md)、[安全策略](.github/SECURITY.md)和[维护指南](docs/maintenance.md)。

## 社区与许可证

本项目维护自 [leehiufung911/cdxml-toolkit](https://github.com/leehiufung911/cdxml-toolkit)。发行名称为 `cdxml-toolkit-community`，兼容的 Python 导入名称为 `cdxml_toolkit`。

- 社区维护者：[ZiChenWang114514](https://github.com/ZiChenWang114514)
- 原作者：Hiu Fung Kevin Lee（[@leehiufung911](https://github.com/leehiufung911)）
- 第三方数据与组件声明：[NOTICE.md](NOTICE.md)
- 许可证：[MIT](LICENSE)

原项目由有机化学博士 Hiu Fung Kevin Lee 主导，其文档记载使用 Claude Code（Opus 4.6）构建与测试。ChemDraw、Office、第三方数据和模板继续适用各自的许可证。

## 从数据生成可持续修改的论文图

将 CSV/XLSX 与可信结构生成底物拓展图或完整结构 SAR 图。化合物 ID 绑定结构和实验指标；在 ChemDraw 手工编辑后更新数据或替换结构，保留无关布局与注释。无法唯一匹配时输出冲突草稿。详见[使用指南与示例](docs/data-driven-figures.md)。XLSX 读取需要工具包的 `publication` 可选依赖。
