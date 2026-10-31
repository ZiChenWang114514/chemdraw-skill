// The interface words of the Chinese pages: one JSON object, with the same keys in both languages.
globalThis.ChemWords = {
 "hint": {
  "move": "拖动原子来移动它。",
  "bond": "点键改键级，点原子接一个碳。从一个原子拖到另一个原子可以成键，点空白处放一个碳。",
  "atom": "点原子换元素，按住 Shift 点往回换。点空白处放一个碳。",
  "ring": "点原子接苯环，点空白处放一个苯环。",
  "erase": "点击原子或化学键即可删除。"
 },
 "ask": "“用 ChemDraw Skill 把{name}画成可编辑 CDXML，渲染后给我看。”",
 "names": {
  "aspirin": "阿司匹林",
  "paracetamol": "对乙酰氨基酚",
  "caffeine": "咖啡因",
  "ibuprofen": "布洛芬",
  "vanillin": "香草醛"
 },
 "build": "{name}.cdxml，ACS Document 1996",
 "matches": "与输入一致",
 "differs": "与输入的 {input} 不同",
 "empty": "画布是空的",
 "order": [
  "单键",
  "双键",
  "三键"
 ],
 "setBond": "已改为{order}。",
 "grow": "已接上一个碳。",
 "element": "已改为 {sym}。",
 "ring": "已接上苯环。",
 "noRoom": "这里放不下，先把结构挪开些。",
 "erased": "已删除。",
 "moved": "已移动。",
 "undone": "已撤销。",
 "reset": "已恢复原样。",
 "valence": "{sym} 现在有 {n} 个键，超过常见的 {v} 个。",
 "challenge": {
  "title": "挑战 {n} / {total}",
  "hint": "提示",
  "skip": "换一题",
  "next": "下一题",
  "close": "退出挑战",
  "done": "完成！用了 {moves} 步。",
  "matches": "与目标一致",
  "aim": "目标 {formula}",
  "tasks": {
   "salicylic": {
    "name": "水杨酸",
    "task": "像体内水解那样，去掉阿司匹林的乙酰基，留下酚羟基。",
    "hint": "选橡皮，删掉左边的甲基、羰基碳和它的双键氧，共三个原子。",
    "fact": "阿司匹林在体内水解后就生成水杨酸，它也是祛痘护肤品里的常见成分。"
   },
   "aminophenol": {
    "name": "4-氨基苯酚",
    "task": "把对乙酰氨基酚退回它的前体：4-氨基苯酚。",
    "hint": "删掉乙酰基的三个原子，留下 NH₂。",
    "fact": "工业上常用它做对乙酰氨基酚的最后一步原料，乙酰化后就得到成品。"
   },
   "acetanilide": {
    "name": "乙酰苯胺",
    "task": "去掉对乙酰氨基酚的羟基，得到乙酰苯胺。",
    "hint": "用橡皮点掉环上的 OH。",
    "fact": "1886 年它以“退热冰”之名作为退烧药上市，是最早的合成解热药之一。"
   },
   "phenylAcetate": {
    "name": "乙酸苯酯",
    "task": "去掉阿司匹林的羧基，留下乙酸苯酯。",
    "hint": "删掉环上的 COOH：羧基碳和两个氧，共三个原子。",
    "fact": "它是 Fries 重排的经典底物：酰基从氧迁移到苯环上。"
   },
   "theophylline": {
    "name": "茶碱",
    "task": "咖啡因少一个甲基就是茶碱：去掉五元环氮上的甲基。",
    "hint": "五元环上连着甲基的是左下方的 N。用橡皮点掉那个甲基。",
    "fact": "茶叶里含有微量茶碱，它也是治疗哮喘和慢阻肺的支气管扩张药。"
   },
   "theobromine": {
    "name": "可可碱",
    "task": "换一个甲基去掉：这次删掉两个羰基之间的氮上的甲基。",
    "hint": "找夹在两个 C=O 之间的 N，用橡皮点掉它的甲基。",
    "fact": "它是可可和巧克力里的主要生物碱。名字来自可可属 Theobroma，分子里并没有溴。"
   },
   "paraxanthine": {
    "name": "副黄嘌呤",
    "task": "去掉连在六元环、又靠近五元环那个氮上的甲基。",
    "hint": "这个 N 一边是 C=O，一边连着五六元环的稠合碳。用橡皮点掉它的甲基。",
    "fact": "你喝下的咖啡因，大部分在肝脏里变成了副黄嘌呤。"
   },
   "xanthine": {
    "name": "黄嘌呤",
    "task": "三个甲基全部去掉，露出母核黄嘌呤。",
    "hint": "用橡皮把三个氮上的甲基都点掉。",
    "fact": "它是嘌呤代谢的中间体，黄嘌呤氧化酶会把它继续氧化成尿酸。"
   },
   "ibufenac": {
    "name": "异丁苯乙酸",
    "task": "布洛芬去掉 α-甲基，就是它的前辈异丁苯乙酸。",
    "hint": "找羧基旁边的 CH，用橡皮点掉它上面的甲基。",
    "fact": "它是布洛芬的前身，上市后因肝毒性撤市。多一个甲基的布洛芬安全得多。"
   },
   "protocatechuic": {
    "name": "原儿茶醛",
    "task": "去掉香草醛甲氧基上的甲基，得到两个相邻的羟基。",
    "hint": "用橡皮点掉 O 上的甲基。",
    "fact": "给它的一个羟基接上甲基，就得到香草醛；接在另一个上，就得到异香草醛。"
   },
   "fluoroacetanilide": {
    "name": "4-氟乙酰苯胺",
    "task": "把对乙酰氨基酚的 OH 换成氟。",
    "hint": "用原子工具连点 OH 氧，切换到 F。用键盘时，把光标放在它上面按 F。",
    "fact": "用氟取代芳环上容易被代谢的位置，是药物化学的常用手法。"
   },
   "vanillylAlcohol": {
    "name": "香草醇",
    "task": "把香草醛的醛基还原成醇。",
    "hint": "用化学键工具点 C=O 双键，点到它变成单键。",
    "fact": "用硼氢化钠还原香草醛得到它，这是本科有机实验里的常见一步。"
   },
   "ibuprofenAmide": {
    "name": "布洛芬酰胺",
    "task": "把布洛芬的羧基变成伯酰胺。",
    "hint": "用原子工具连点 OH 氧，切换到 N。",
    "fact": "羧酸变成酰胺后，酸性的 OH 就没有了，分子的极性和溶解性也随之改变。"
   },
   "isovanillin": {
    "name": "异香草醛",
    "task": "让香草醛的甲基换个位置：从一个氧搬到相邻的另一个氧。",
    "hint": "删掉 O 上的甲基，再用化学键工具点环上的 OH 氧，接一个碳。",
    "fact": "它和香草醛的分子式完全相同，只是 OH 和 OCH₃ 互换了位置。分子式一致，不代表结构正确。"
   },
   "wintergreen": {
    "name": "水杨酸甲酯",
    "task": "从阿司匹林出发，做出冬青油的主要成分水杨酸甲酯。",
    "hint": "先像第一关那样去掉乙酰基，再在羧基的 OH 上接一个碳。",
    "fact": "冬青油的香气主要来自它，许多外用镇痛药膏里也有它。"
   },
   "ibuprofenMethyl": {
    "name": "布洛芬甲酯",
    "task": "把布洛芬变成它的甲酯。",
    "hint": "用化学键工具点羧基里的 OH 氧，接一个碳。",
    "fact": "气相色谱分析羧酸之前，常先把它们做成这样的甲酯。"
   },
   "vanillic": {
    "name": "香草酸",
    "task": "把香草醛的醛基氧化成羧酸。",
    "hint": "用化学键工具点醛基碳接一个碳，再用原子工具把新原子切换到 O。",
    "fact": "香草醛氧化就得到它，香草豆的风味物质里也有它。"
   },
   "ethylVanillin": {
    "name": "乙基香草醛",
    "task": "把香草醛的甲氧基加长成乙氧基。",
    "hint": "用化学键工具点甲基，再接一个碳。",
    "fact": "一种合成香料，香气比香草醛更浓，天然香草里并没有它。"
   },
   "veratraldehyde": {
    "name": "藜芦醛",
    "task": "把香草醛的酚羟基也做成甲氧基。",
    "hint": "用化学键工具点环上的 OH 氧，接一个碳。",
    "fact": "它是香草醛甲基化的产物，常作香料和药物合成的中间体。"
   },
   "phenacetin": {
    "name": "非那西丁",
    "task": "给对乙酰氨基酚的羟基接上乙基。",
    "hint": "用化学键工具点 OH 氧接一个碳，再点这个碳接第二个碳。",
    "fact": "它曾是常用止痛药，后因肾毒性退市。它在体内主要转化成对乙酰氨基酚。"
   }
  }
 },
 "run": "运行一遍",
 "progressTop": "开头",
 "shortcuts": {
  "title": "快捷键",
  "rows": [
   ["V B A R E", "切换工具"],
   ["C N O S F L", "悬停原子时换元素，L 是氯"],
   ["1 2 3", "悬停键时改键级"],
   ["Delete", "删除悬停的原子或键"],
   ["方向键", "在原子和键之间移动"],
   ["Shift 方向键", "微移原子"],
   ["Enter", "在光标处使用当前工具"],
   ["Ctrl Z", "撤销"],
   ["Ctrl Shift Z", "重做"],
   ["Ctrl Shift K", "整理结构"],
   ["Esc", "关闭这个列表"]
  ]
 },
 "elements": {
  "C": "碳",
  "N": "氮",
  "O": "氧",
  "S": "硫",
  "F": "氟",
  "Cl": "氯",
  "Br": "溴"
 },
 "tip": {
  "atom": "{name}，{h} 个隐含氢，价键 {used} / {max}",
  "bond": "{pair}，{order}键"
 },
 "faq": {
  "expand": "全部展开",
  "collapse": "全部收起",
  "count": "{n} 个结果",
  "link": "复制这个问题的链接"
 },
 "running": "运行中…",
 "rerun": "再运行一遍",
 "copyAsk": "复制",
 "copiedAsk": "已复制",
 "lightbox": {
  "open": "放大查看：{alt}",
  "close": "关闭",
  "prev": "上一张",
  "next": "下一张",
  "zoomIn": "放大",
  "zoomOut": "缩小",
  "fit": "适应窗口",
  "count": "{n} / {total}",
  "hint": "滚轮或双击缩放，拖动平移，左右方向键切换，Esc 关闭。"
 },
 "aria": "{name} 的结构，分子式 {formula}。可以用鼠标、触屏编辑，也可以聚焦画布后用方向键选择，按 Enter 使用当前工具。",
 "cleaned": "已整理：键长和键角已摆正。",
 "smiles": "SMILES：{smiles}",
 "copied": "已复制 SMILES：{smiles}",
 "noSmiles": "有原子超出常见价态，先修正再导出 SMILES。",
 "download": "已保存 {file}，可以直接用 ChemDraw 打开。",
 "keys": "小技巧：鼠标停在原子上按 C、N、O、S、F 或 L（Cl）换元素，停在键上按 1、2、3 换键级，按 Delete 删除。",
 "redone": "已重做。",
 "placed": "已放置一个碳。",
 "bonded": "已成键。",
 "alreadyBonded": "这两个原子已经连着了。",
 "cursorAtom": "{sym}，{n} 根键",
 "cursorBond": "{order}键",
 "linkCopied": "分享链接已复制。",
 "link": "分享链接：{url}",
 "tooBig": "结构太大，放不进链接。",
 "ringPlaced": "已放置苯环。",
 "drawing": "这个结构",
 "daily": {
  "button": "今日分子",
  "title": "今日分子 #{n}",
  "streak": "连续 {n} 天",
  "shareTitle": "ChemDraw Skill 今日分子 #{n}",
  "shareMoves": "{moves} 步",
  "share": "分享结果",
  "shared": "结果已复制。",
  "shareText": "结果：{text}",
  "lab": "去实验室继续",
  "line": "今日分子 #{n}：从{mol}出发。",
  "lineStreak": "今日分子 #{n}：从{mol}出发。已连续 {days} 天。",
  "solved": "今天的分子已完成，明天再来。",
  "again": "再做一次"
 },
 "lab": {
  "modes": {
   "daily": "今日分子",
   "levels": "路线图",
   "hunt": "找错",
   "isomers": "异构体",
   "dex": "图鉴",
   "free": "画板"
  },
  "chapters": {
   "take": {
    "title": "拆",
    "text": "从五个常见分子出发，去掉基团。"
   },
   "swap": {
    "title": "改",
    "text": "换一个原子，或挪动一个基团。"
   },
   "add": {
    "title": "造",
    "text": "接上新的碳，把分子做长。"
   }
  },
  "stats": {
   "stars": "星",
   "streak": "连续天数",
   "compounds": "化合物",
   "badges": "成就"
  },
  "moves": "步数",
  "par": "最少步数",
  "delta": "分子式还差",
  "deltaJoin": "、",
  "deltaDone": "分子式已一致，再看连接方式",
  "target": "目标分子式",
  "starsLabel": "{n} 颗星（共 3 颗）",
  "unsolved": "未完成",
  "lockedName": "未解锁",
  "backToRoute": "返回路线图",
  "restart": "重新开始",
  "nextLevel": "下一关",
  "solvedIn": "完成！用了 {moves} 步。",
  "starsHelp": "在最少步数内完成且不看提示得 3 星，不看提示得 2 星，看了提示得 1 星。连续切换同一个原子或键只算一步。",
  "dexIntro": "完成一关就解锁一种化合物。每种都能下载 CDXML，也能复制一句话交给你的 Agent。",
  "dexEmpty": "去路线图完成第一关，这里就会出现第一种化合物。",
  "saveCdxml": "下载 .cdxml",
  "copyAsk": "复制 Agent 请求",
  "openBoard": "在画板打开",
  "ask": "用 ChemDraw Skill 把{name}画成可编辑的 CDXML，用 ChemDraw 渲染后给我看 PNG。",
  "badgesTitle": "成就",
  "badges": {
   "first": {
    "title": "第一个分子",
    "text": "完成任意一关。"
   },
   "perfect": {
    "title": "一步不多",
    "text": "拿到一次 3 星。"
   },
   "xanthines": {
    "title": "黄嘌呤一家",
    "text": "完成咖啡因的四个亲戚。"
   },
   "complete": {
    "title": "路线走完",
    "text": "完成全部 20 关。"
   },
   "readback": {
    "title": "readback 全对",
    "text": "找错模式连过 8 题。"
   },
   "isomers": {
    "title": "一个不漏",
    "text": "找齐一组同分异构体。"
   },
   "streak": {
    "title": "连续一周",
    "text": "连续 7 天完成今日分子。"
   },
   "export": {
    "title": "带回 ChemDraw",
    "text": "下载一个 .cdxml 文件。"
   }
  },
  "badgeUnlocked": "解锁成就：{title}",
  "badgeView": "查看",
  "huntIntro": "Agent 交来的图里有一处错。对照正确结构，点出错的原子或键。这些结构是故意改错的，只用于游戏。",
  "huntStart": "开始一局",
  "huntAgain": "再来一局",
  "huntNext": "下一题",
  "huntRound": "第 {n} 题，共 {total} 题",
  "huntLives": "还剩 {n} 次机会",
  "huntTruth": "正确结构",
  "huntDrawn": "Agent 的图",
  "huntFound": "找到了：{kind}",
  "huntMiss": "这里没错，再看看。",
  "huntOver": "这局过了 {n} 题，最好成绩 {best} 题。",
  "huntClear": "8 题全对。readback 就是这样抓住错误的。",
  "huntBest": "最好成绩 {n} / 8",
  "huntMirror": "这张图左右翻转了。",
  "huntAtom": "{sym} 原子",
  "huntBond": "{order}键",
  "huntKinds": {
   "element": "元素写错了。",
   "ringN": "环上的碳被写成了氮。",
   "order": "键级写错了。",
   "extra": "多了一个甲基。",
   "missing": "少了一个原子。",
   "valence": "这里的碳超过了四价。"
  },
  "isoIntro": "从空白画布开始，画出这个分子式的所有构造异构体。不计立体异构。",
  "isoPick": "选一个分子式",
  "isoProgress": "已找到 {n} / {total}",
  "isoFound": "找到一个新的！",
  "isoSeen": "这个已经找到过了。",
  "isoDone": "全部找齐了。",
  "isoClear": "清空画布",
  "isoHint": "当前分子式 {formula}",
  "isoEmpty": "空白画布",
  "freeIntro": "随便画，复制 SMILES、下载 CDXML，或者把结构做成链接发给别人。",
  "freeLoad": "从这里开始",
  "freeBlank": "空白画布",
  "sharedLoaded": "已打开分享的结构。",
  "sharedBad": "这个链接里的结构无法读取，已打开空白画布。",
  "reset": "清除进度",
  "resetConfirm": "再点一次确认清除",
  "resetDone": "进度已清除。",
  "prog": "进度只保存在这个浏览器里，不会上传。",
  "from": "起始分子"
 }
};
