# ChemDraw Skill 快速上手

本指南适用于任何能读取本地说明文件并执行 shell 命令的 agent。图像重建还需要 agent 具备看图能力（或由人工复核）。

## 开始之前

先确认这台机器有什么：

- **ChemDraw。** 原生渲染、第 3 步里的 PNG、CDX 转换和 Word/PowerPoint 对象，都需要 Windows 或 macOS 上已授权的桌面版 ChemDraw。没有它时，Skill 仍然可以生成、编辑、检查和识别结构，也能运行各个计算工具（[有哪些差别](../skill/chemdraw/references/operations.md#no-chemdraw-on-this-host)）。
- **Python。** 运行时要用 64 位 Python 3.10–3.13 来构建；安装脚本本身在 3.9 及以上版本就能运行。打包的 toolkit 还不支持 Python 3.14 及更新版本：如果机器上只有这些版本，先装一个 3.12（例如 `uv python install 3.12`），或者用 `--python <解释器>` 指定。
- **磁盘。** 默认运行时是一个约 760 MB 的虚拟环境。`--extras` 不带名字只装核心部分，`--extras publication office` 只加这两组。
- **可选工具。** 通过 OPSIN 把名称转成结构，默认不安装，需要加 `--opsin`。OPSIN 依赖 Java：Windows 上第一次使用时会自动下载，macOS 和 Linux 上需要自己安装。`image` 扩展里的文字识别需要 Tesseract 程序。

## 安装

**1. 安装。** 安装脚本会自己找一个 64 位 Python 3.10–3.13 来构建 toolkit 运行时（通过 `py` 启动器、`uv` 管理的解释器或 PATH 上的 `python3.x`）。先预览，确认无误后再加 `--apply`：

```bash
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
cd chemdraw-skill
python scripts/install.py --agent claude agents --runtime          # 只预览
python scripts/install.py --agent claude agents --runtime --apply  # 安装
```

**2. 检查**这台机器上哪些功能可用：

```bash
python $HOME/.claude/skills/chemdraw/scripts/cdx.py doctor
```

**3.** 按下面“第一次使用”的方式，用平常的话告诉 agent 要做什么。

如果想先试 ChemDraw 自带的反应计算器，而不是画图，可以运行 `python $HOME/.claude/skills/chemdraw/scripts/cdx.py calc "OCc1ccccc1.CC(=O)Cl>>CC(=O)OCc1ccccc1"`。

可选的识别和预测引擎（更多 OCSR 引擎、逆合成、产物、反应条件和核磁预测）不随安装一起下载。先用 `cdx.py engines --recommend 需求` 看看该装哪个、要占多大空间，同意后再运行 `cdx.py install-engines --bundle 名称`。每个引擎占用从 2 MB 到约 8.5 GB 不等（最大的是 RetroChimera，运行时还需要约 14 GB 空闲内存）。`decimer-local` 在本机运行 DECIMER 模型，直接装进工具包运行环境。有 NVIDIA 显卡时引擎会使用显卡并报告 `execution.device`，设置 `CHEMDRAW_ENGINE_DEVICE=cpu` 可关闭；自适应复杂度分类器（`--accel auto|on|off`、`--task-hint`）让简单单次调用保持无状态，并在复杂或批量任务（如多图批处理 `recognize_batch`）中自动预热常驻工作守护进程。许可限制：MolParser 的权重仅限非商业用途，RetroChimera 仅供研究，Reacon 没有许可证。想装到其他磁盘，就在安装前设置 `CHEMDRAW_ENGINE_HOME`，并且之后一直保留这个设置（见[引擎说明](../skill/chemdraw/references/engines.md)）。

其他 agent 的安装位置、手动构建运行时和诊断方法见[首次安装](guide.zh-cn.md#首次安装)；[agent 集成](../skill/chemdraw/references/agent-integration.md)解释了目录布局和每一条命令。

## 第一次使用

对你的 agent 说：

```text
使用 ChemDraw Skill 解析阿司匹林并生成可编辑的 CDXML。如果有原生 ChemDraw，请渲染并查看 PNG。报告结构回读结果和输出路径。
```

结构已知、图还不存在时，把需求说成一句话，agent 会写出简短的说明文件，再用 `cdx.py draw` 一次画出并检查单步反应、线性/收敛/发散或催化循环（`catalytic-cycle`）路线、底物拓展图或带弯箭头的机理，见[绘制新反应图](../skill/chemdraw/references/scheme-drawing.md)。条件只取自你给的内容。科研与实验记录工作流还支持原生读取一维 NMR（Bruker `1r`/`fid`、JCAMP-DX、JEOL、Varian 与 CSV/FT）以及解析 LCMS（Waters PDF、OpenLynx `.rpt`、Waters `.raw`、Shimadzu `.daml`、Agilent `report.txt` 与 `mzML`/`mzXML`）。

考试或讲义图（含 C10H21 之类的缩写、化合物代号、中文批注）走 [ACS 1996 绘图器](../skill/chemdraw/references/acs1996-drawings.md)。论文图片走[重建指南](../skill/chemdraw/references/image-visual-review.md)：通读整图、裁剪、用 DECIMER API 识别、对齐方向、并排比对、修正化学、组装条件与版面、原生渲染。

[记录模板](../skill/chemdraw/assets/paper-replica/task-template.json) | [可运行示例](../skill/chemdraw/assets/paper-replica/example/CASE.md) | [工作流路由](../skill/chemdraw/references/workflow-router.md)
