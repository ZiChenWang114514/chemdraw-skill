# ChemDraw Skill 快速上手

本指南适用于任何能读取本地说明文件并执行 shell 命令的 AI Agent；涉及文献或专利截图重建时，还需 Agent 支持看图（或由人工并排复核）。

## 安装

**1. 一键安装**（安装脚本在 Python 3.9+ 上运行，会自动查找本机 64 位 Python 3.10–3.13 构建共享工具包环境）：

```bash
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
cd chemdraw-skill
python scripts/install.py --agent claude agents --runtime          # 仅预览路径
python scripts/install.py --agent claude agents --runtime --apply  # 正式安装
```

**2. 检查本机能力**：

```bash
python $HOME/.claude/skills/chemdraw/scripts/cdx.py doctor
```

**3. 第一次使用**（直接复制发给你的 Agent）：

```text
使用 ChemDraw Skill 解析阿司匹林并生成可编辑的 CDXML。如果有原生 ChemDraw，请渲染并查看 PNG，同时报告结构回读结果和输出路径。
```

如果想先体验 ChemDraw 自带的反应计算器，可运行：

```bash
python $HOME/.claude/skills/chemdraw/scripts/cdx.py calc "OCc1ccccc1.CC(=O)Cl>>CC(=O)OCc1ccccc1"
```

<a id="开始之前"></a>

## 环境与可选组件说明

- **桌面版 ChemDraw（可选）。** 原生 300 dpi PNG 渲染、CDX 转换、交互式化学计量表和 Word/PowerPoint 对象需要 Windows 或 macOS 上已授权的桌面版 ChemDraw。未安装时，Skill 仍可生成、编辑、识别和校验 `.cdxml` 结构，并运行批量计算工具（[有哪些差别](../skill/chemdraw/references/operations.md#no-chemdraw-on-this-host)）。
- **Python。** 工具包运行时需要 64 位 Python **3.10–3.13**；暂不支持 Python 3.14 及更新版本（若本机只有 3.14+，可先执行 `uv python install 3.12` 或传 `--python <解释器>`）。
- **磁盘空间。** 默认共享虚拟环境约 760 MB；`--extras` 不带名字只装核心部分，`--extras publication office` 仅加装指定分组。
- **按需扩展参数：**
  - `--opsin`：启用离线英文命名转结构（Windows 首次使用自动下载 Java，macOS 和 Linux 需自装 Java）。
  - `--mapping`：在各自独立环境中安装机器学习原子映射后端（RXNMapper、LocalMapper）。
  - `image` 扩展中的文字识别依赖 Tesseract 程序。
- **可选识别与预测引擎：** 默认不随安装下载。先运行 `cdx.py engines --recommend 需求` 查看推荐引擎与占用空间（2 MB 至约 8.5 GB；RetroChimera 另需约 14 GB 空闲内存），确认后再执行 `cdx.py install-engines --bundle 名称`。安装前设置并长期保留 `CHEMDRAW_ENGINE_HOME` 可将引擎存放在其他磁盘（详见[引擎说明](../skill/chemdraw/references/engines.md)）。

其他 Agent 的安装目录、手动创建运行时与故障排查见[首次安装](guide.zh-cn.md#首次安装)和 [Agent 集成说明](../skill/chemdraw/references/agent-integration.md)。

## 常用工作流导航

- **从零绘制新反应或底物拓展图：** 支持 `cdx.py resolve`、`cdx.py draw --name` / `--smiles` / `--reaction`，或由一句话生成 JSON 说明文件绘制单步反应、线性/汇聚/发散路线、催化循环（`catalytic-cycle`）、底物拓展网格与弯箭头机理；用 `--style nature_portfolio` / `--style baran_group` 切换 28 种期刊与课题组画法风格（`cdx.py styles` 查看全部）。详见[绘制新反应图](../skill/chemdraw/references/scheme-drawing.md)。
- **试卷与讲义插图（含缩写、代号与中文批注）：** 见 [ACS 1996 绘图指南](../skill/chemdraw/references/acs1996-drawings.md)。
- **文献反应图复刻：** 通读整图 → 裁切结构 → DECIMER 识别 → 匹配取向 → 左右对照 → 修正化学 → 组装版面 → 原生预览，详见[图像复刻指南](../skill/chemdraw/references/image-visual-review.md)。
- **谱图与实验记录：** 支持一维 NMR（Bruker `1r`/`fid`、JCAMP-DX、JEOL、Varian、CSV）与 LCMS（Waters PDF/OpenLynx `.rpt`/`.raw`、Shimadzu `.daml`、Agilent `report.txt`、`mzML`/`mzXML`）。

[记录模板](../skill/chemdraw/assets/paper-replica/task-template.json) | [可运行示例](../skill/chemdraw/assets/paper-replica/example/CASE.md) | [工作流路由](../skill/chemdraw/references/workflow-router.md)
