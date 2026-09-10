# ChemDraw Skill 中文指南

这是面向任意 Agent 的化学绘图与论文反应图复刻 Skill。需要读取本地指令、调用 MCP 或执行 Python；图像复刻还需要视觉检查能力。不同客户端的配置文件和发现目录各自适配。

## 从零开始安装

依次阅读[通用 Agent 接入](../skill/chemdraw/references/agent-integration.md)和[安装与能力验证](guide.zh-cn.md#首次-windows-安装)。项目不要求特定 Agent CLI，默认不会修改客户端配置。

## 10. 完成第一次使用

加载 `skill/chemdraw/SKILL.md` 后，可以向任何具备相应工具权限的 Agent 提出：

```text
使用 ChemDraw Skill 解析阿司匹林，输出可编辑 CDXML；原生 ChemDraw 可用时渲染 PNG，检查实际图像，并报告结构读回与输出路径。
```

论文图片使用[快速复刻指南](../skill/chemdraw/references/image-visual-review.md)：读整图、裁切、DECIMER、取向匹配、左右对照、结构修正、条件和版式组装、原生验收。结构正确和视觉相似分别验收。

[最小记录模板](../skill/chemdraw/assets/paper-replica/task-template.json) · [可复现示例](../skill/chemdraw/assets/paper-replica/example/CASE.md) · [全部任务入口](../skill/chemdraw/references/workflow-router.md)
