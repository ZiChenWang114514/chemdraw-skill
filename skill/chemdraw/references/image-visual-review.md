# 论文反应图快速复刻

目标：拿到图片后直接工作，减少探索代码和临时编写脚本。默认交付可编辑 CDXML 与原生预览；仅在用户要求时展开长报告。

## 1. 整图一次读清

先用视觉看整张图，列出结构编号、箭头连接、条件、产率、X/R 定义。条件和编号由智能体读图，不作为分子交给 DECIMER。复制 [最小记录模板](../assets/paper-replica/task-template.json)，按实际结构数量填写；它是记录模板，不是绘图接口参数。

优先使用用户已有 CDX/CDXML 或可信结构；存在原生文件时跳过 OCSR。截图路线继续以下步骤。不要为了开始任务先读完整接口目录、遍历源码或重装环境。

## 2. 视觉分区并识别

将结构区域写成 `regions.json`（原图显示像素，左上包含、右下不包含）：

```json
[{"id":"A","box":[20,10,340,180],"kind":"structure","exclude_boxes":[]}]
```

使用已有 MCP Python 环境运行辅助脚本，`<skill>` 表示当前 skill 目录：

```powershell
& <MCP-Python> <skill>/scripts/image_review_workspace.py prepare source.png regions.json work/crops --scale 4
```

`work/crops` 必须是新目录。打开裁片看一遍，确保 OMe、CN、末端字母和立体键完整。`exclude_boxes` 可移除邻近编号/箭头，坐标仍用原图坐标，不能覆盖任何化学信息。源图不改写，裁片哈希与坐标换算自动保存；四倍放大只帮助识别，不恢复缺失信息。

用户明确要求 DECIMER API，即已授权该任务相关裁片上传；无需重复确认。否则沿用已获授权的服务，未获授权时不上传。对每个裁片调用：

```python
extract_structures_via_decimer_api(
    image_path="<absolute>/work/crops/A.png",
    output_path="<absolute>/work/A-decimer.json",
    confirm_upload=True, timeout_seconds=120)
```

这是单图片接口；在工具允许并行时并行处理独立裁片，不构造不存在的 batch 参数。保存所有原始结果，包括无效 SMILES。只针对明确错误改变裁片/放大方式后重试；无效结果不能直接绘制。已有识别缓存且裁片哈希相同，就复用缓存。

## 3. 一开始就匹配原图取向

先检查识别结果里的明显错误和 X/R 定义。普通结构使用现有约束对齐；折叠链、桥环优先追踪可见原子坐标。不要先大量生成随机取向再筛选。只有无法直接对齐时，才尝试少量旋转候选；不镜像、不拉伸。

绘图采用 `compose_chemical_figure(manifest_path, output_path)`。以下为 **绘图 manifest**，不是上面的记录模板：

```json
{"version":1,"objects":[
  {"type":"molecule","id":"A","file":"A-corrected.mol","position":[120,100]}
]}
```

精确取向时将 `position` 换为 `coordinates`，每个输入原子一个 `[x,y]`，单位是点，向右/下为正。索引来自该 MOL/SMILES 的实际原子顺序；不能在 canonical SMILES 重排后复用旧索引。裁片坐标回原图：`source_xy = crop_xy / scale + box_origin`；原图转点：`point_xy = source_xy * points_per_pixel + offset`。只用统一比例，不独立拉伸横纵轴。绘图器在最终坐标上重算楔线并检查读回。

新 MCP 工具尚未显示时，直接使用已存在的 CLI：

```powershell
& <MCP-Python> -m cdxml_toolkit.mcp_runtime.figure_tools compose_chemical_figure --arguments draw-args.json
```

其中 `draw-args.json` 是 `{"manifest_path":"<absolute>/figure.json","output_path":"<absolute>/figure.cdxml"}`。只在需要具体图形字段时查 [绘图字段参考](publication-figures.md)。R/X 等真实缩写及复杂桥环的已验证实现见末尾可运行示例；目前它们不是通用 manifest 中的 `abbreviations` 字段，不要虚构接口。

## 4. 原生重绘、左右检查、只改出错结构

一次原生批量渲染准备好的文件：

```python
render_cdxml_files(input_paths=["<absolute>/A.cdxml", "<absolute>/B.cdxml"],
                   output_dir="<absolute>/work/native-r1", format="png", dpi=144)
```

本机原生调用使用现有隔离 worker 和锁，不另起无锁 COM 会话。生成左右对照：

```powershell
& <MCP-Python> <skill>/scripts/image_review_workspace.py compare work/crops/A.png work/native-r1/A.png work/A-review-r1.png --height 400
```

**实际打开对照图检查**，不能根据生成成功判定正确。拼图自动记录两侧哈希与显示比例，但不会代替视觉判断，也不会验证右图确实来自 ChemDraw；应使用上一步返回的原生输出。

发现结构错误时调用：

```python
modify_molecule(mol_json={"smiles":"<recognized SMILES>"},
    operation="set_smiles", new_smiles="<visually grounded corrected SMILES>",
    description="A: 图中为 OH，识别结果误为甲基；其他连接保持")
```

查看返回的 MCS/分子式及立体变化，再绘制修正结果。非法 R token 的最小语法规范化需单独记录，不能冒充有效 OCSR 原文。只重做受修改影响的结构；布局改动后仍要查看最终预览。源图无法辨认的细节保持未解决，不能依靠反应常识补画。

## 5. 条件组装与交付

按照源图顺序记录条件原文、结构/状态编号及产率作用范围。比如“70% (3 steps)”是三步合计；共享波浪键结构对应 a/b 标签时保存相对描述，不自动生成两个绝对构型 SMILES。使用原生富文本处理上下标，再按源图位置放置结构、箭头和标签。

整图原生渲染后看一遍：条件顺序、产率、编号、箭头、缩写、交叉显示与裁边。输出顺序：**可编辑 CDXML → 预览 → 必要对照/未解决项**。原始响应、修正结果和哈希留在工作目录，不默认输出冗长审计报告。

默认分层验收：修正结构与最终 CDXML 读回一致；视觉检查未发现明显结构/标注错误；版式差异如实说明。严格 1:1 只有确实达到时才能宣布完成；像素相似度不是结构正确率，白底占比也不是复刻成功率。

## 高频问题：直接这样处理

| 看到的问题 | 已验证的处理 |
|---|---|
| 折叠链看似成环、桥环有交叉 | 逐键追踪；仅线条相交不增加原子或闭环 |
| Ph/Pb、OH/甲基、OMe/OH、CN、X/R | 优先核对这些部位；依据整图定义修正，再检查分子式差异 |
| R/X 缩写 | 显示原文，内部用真实原子子图和连接点；不能用文字代替连接关系 |
| 波浪键、α/β、R/S 混用 | 各自记录；未指定不等于消旋；CIP 字母改变不必然表示空间翻转 |
| 坐标/楔线调整 | 最终坐标重新楔化并读回，核对楔线窄端与连接原子 |
| 桥环构型缺失或读取结果矛盾 | 对同一原生保存文件比较 RDKit 的 CDXML 读回与 ChemScript 直接输出的 SMILES；MOL 中转可能损失立体信息，不能作为唯一裁判。逐原子对应核查；升级读取器后只复测一个有明确分歧的结构，确认有效后再批量处理。不要为使两个读取器一致而翻转楔线；分歧未解决时保留待验收状态 |
| 左向缩写倒排、堆叠或换行 | 显式设置节点/文本左右对齐与字体 runs；单结构预览也需足够页宽 |
| 桥环前后显示错误 | 先核对前后键，再调整粗键/遮挡；必要的矢量遮挡与结构归组，不遮掉真实标签 |
| 只在全图正常、单结构换行 | 检查单结构导出的页面宽度与坐标，不反复修改正确 SMILES |

## 可运行示例

[两张完整论文路线图](../assets/paper-reconstructions/README.md) 包含原生结构组件、布局清单和离线组装脚本。运行 `python <skill>/assets/paper-reconstructions/rebuild.py <new-output-directory>` 后进行原生预览。示例覆盖共享 OR、缩写、折叠链、桥键遮挡及电子箭头；完整布局已具备，但立体信息仍有读取工具间分歧，不能作为全部构型已验收的样板。不要将前后步骤自动改成自洽结构：原图的展开链与缩写定义可能不一致，逐处保留并列出差异。

[绘图示例](../assets/paper-replica/example/CASE.md) 包含图形 manifest、实际 CDXML/原生预览和离线重建脚本；覆盖常用箭头、电子曲线、富文本、手性和增强立体组。

```powershell
& <MCP-Python> <skill>/assets/paper-replica/example/replay.py <absolute-new-output-directory>
```

对生成的 `figure.cdxml` 调用原生渲染接口，再制作并查看左右对照。本例不调用 DECIMER；论文识图使用用户有权提供的图片按上述流程执行。图形字段见 [绘图参考](publication-figures.md)。

## 验证范围与原生能力缺失

`document_chemistry_validation` 验证最终文件中的完整分子清单（含重复次数），并记录 SHA-256；`scope=rdkit_readback_consistency` 仅表示 RDKit 读回一致。跨读取器构型分歧仍阻止完整立体化学验收。原生 ChemDraw 不可用时，交付可编辑文件并明确标记“原生预览待验证”，不能以其他渲染器替代原生验收。
