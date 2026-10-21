# ChemDraw Skill 快速上手

本指南适用于任何能读取本地说明文件并执行 shell 命令的 agent。图像重建还需要 agent 具备看图能力（或由人工复核）。

## 安装

按照[首次安装](guide.zh-cn.md#首次安装)操作：`python scripts/install.py --agent <你的 agent> --runtime --apply` 会为每个 agent 安装 Skill，并创建一个共享运行时。然后运行 `python <skill>/scripts/cdx.py doctor`。[agent 集成](../skill/chemdraw/references/agent-integration.md)解释了目录布局和每一条命令。

## 第一次使用

对你的 agent 说：

```text
使用 ChemDraw Skill 解析阿司匹林并生成可编辑的 CDXML。如果有原生 ChemDraw，请渲染并查看 PNG。报告结构回读结果和输出路径。
```

考试或讲义图（含 C10H21 之类的缩写、化合物代号、中文批注）走 [ACS 1996 绘图器](../skill/chemdraw/references/acs1996-drawings.md)。论文图片走[重建指南](../skill/chemdraw/references/image-visual-review.md)：通读整图、裁剪、用 DECIMER API 识别、对齐方向、并排比对、修正化学、组装条件与版面、原生渲染。

[记录模板](../skill/chemdraw/assets/paper-replica/task-template.json) | [可运行示例](../skill/chemdraw/assets/paper-replica/example/CASE.md) | [工作流路由](../skill/chemdraw/references/workflow-router.md)
