# Fixed vs Heading Badcase Analysis

## 1. 总体结论

heading-aware chunk 相比 fixed baseline 有小幅净提升：strict pass 从 32/50 提升到 34/50，pass_rate 从 0.64 提升到 0.68。但提升并不稳定：fixed 失败 heading 通过 5 题，同时 fixed 通过 heading 失败 3 题，净增 2 题；avg_keyword_hit_rate 从 0.446 降到 0.427。

从 badcase 对齐看，heading 的主要收益来自两类：一是 section-aware 内容让摘要、关键词、实验结论等上下文更集中，例如 paper004_q001；二是 no-answer 回答措辞更贴合评测脚本，例如 paper003_q010、paper004_q010。后者更像评测规则触发，而不是 RAG 能力实质提升。

剩余失败中，`likely_eval_keyword_too_strict` 仍是最大类，说明很多回答语义接近但没有命中严格关键词；`retrieval_context_weak` 有 4 题，其中 paper003_q007 和 paper004_q008 更值得作为后续 retrieval 优化样本；`answer_keyword_mismatch` 有 3 题，主要是答案没有覆盖关键数字或总结性关键词。

## 2. 结果迁移统计

| 类型 | 数量 | 说明 |
|---|---:|---|
| fixed 失败 heading 通过 | 5 | heading 净增的主要来源，包含 2 个 no-answer 评测措辞改善 |
| fixed 通过 heading 失败 | 3 | 包含 1 个 no-answer 评测退化和 1 个实验数字覆盖退化 |
| 两者都失败 | 13 | 大多是 strict keyword 太硬、上下文弱或答案漏关键点 |
| 两者都通过 | 29 | heading 没破坏大多数已通过样本 |

### fixed 失败 heading 通过

- paper001_q006
- paper002_q001
- paper003_q010
- paper004_q001
- paper004_q010

### fixed 通过 heading 失败

- paper001_q004
- paper001_q010
- paper003_q005

### 两者都失败

- paper001_q002
- paper001_q007
- paper002_q002
- paper002_q004
- paper002_q008
- paper003_q007
- paper004_q002
- paper004_q005
- paper004_q006
- paper004_q007
- paper004_q008
- paper005_q007
- paper005_q008

### 两者都通过

- paper001_q001
- paper001_q003
- paper001_q005
- paper001_q008
- paper001_q009
- paper002_q003
- paper002_q005
- paper002_q006
- paper002_q007
- paper002_q009
- paper002_q010
- paper003_q001
- paper003_q002
- paper003_q003
- paper003_q004
- paper003_q006
- paper003_q008
- paper003_q009
- paper004_q003
- paper004_q004
- paper004_q009
- paper005_q001
- paper005_q002
- paper005_q003
- paper005_q004
- paper005_q005
- paper005_q006
- paper005_q009
- paper005_q010

## 3. heading 改善的 case

### paper001_q006

- question: 论文的验证方式主要是什么，而不是哪类实验？
- fixed 失败原因: `likely_eval_keyword_too_strict`，strict keyword_hit_rate=0.3333，只命中“数学证明”“次模性”。
- heading 为什么通过: heading keyword_hit_rate=0.6667，额外命中“关键集”“紧集”。heading 检索中出现 `[Section: 摘要]`、`[Section: 关键词]` 等更结构化片段，让方法概念更容易进入回答。
- 是否和 heading chunk / metadata 有关: 有一定关系，section 前缀和摘要/关键词片段增强了概念覆盖。
- 是否真实提升: 部分真实提升。fixed 的回答语义也基本正确，且 relaxed 已通过；heading 主要提升了关键词覆盖和表达完整度。

### paper002_q001

- question: 这篇论文主要研究什么问题？
- fixed 失败原因: `likely_eval_keyword_too_strict`，strict keyword_hit_rate=0.3333，命中“点云”“邻域”，但漏“准确性”等关键词。
- heading 为什么通过: heading keyword_hit_rate=0.5，回答覆盖了点云法向估计、邻域、准确性与鲁棒性。heading 召回更偏实验/结论片段，回答补充了性能目标。
- 是否和 heading chunk / metadata 有关: 可能有关，heading chunk 让较长的结果分析内容聚在一起，减少了 fixed 小块切断后的上下文碎片。
- 是否真实提升: 中等程度真实提升，但 fixed 答案本身也答到了研究问题；部分收益来自严格关键词命中改善。

### paper003_q010

- question: 这篇论文是否提供了每位实验参与者的个人身份信息和联系方式？
- fixed 失败原因: `likely_eval_keyword_too_strict`，这是 no-answer 题，fixed relaxed 已通过但 strict 未通过。
- heading 为什么通过: heading 回答使用了“当前上传文档中没有找到直接依据”这类 strict no-evidence 触发表达，因此 strict 通过。
- 是否和 heading chunk / metadata 有关: 关系不大。检索上下文没有明显更强，主要是拒答措辞更符合评测脚本。
- 是否真实提升: 更像评测规则导致的偶然提升，而不是 RAG 检索能力提升。

### paper004_q001

- question: 这篇论文主要综述什么研究主题？
- fixed 失败原因: `likely_eval_keyword_too_strict`，只命中“深度学习”“图像融合”。
- heading 为什么通过: heading keyword_hit_rate=0.8333，回答覆盖“不同源图像”“互补信息”“融合图像”等摘要核心定义。
- 是否和 heading chunk / metadata 有关: 是。heading 更容易把综述主题、摘要定义和 section 语义放在同一上下文窗口里。
- 是否真实提升: 是本轮最明确的真实提升。fixed 召回中有较多题名/引用噪声，heading 结果更利于回答主题定义。

### paper004_q010

- question: 这篇论文是否提供了每位实验参与者的个人身份信息和联系方式？
- fixed 失败原因: `likely_eval_keyword_too_strict`，fixed relaxed 已通过，但检索到作者简介和邮箱，回答需要额外区分作者与实验参与者。
- heading 为什么通过: heading 没有优先召回作者邮箱片段，回答更直接说明“没有找到直接依据”和“不涉及实验参与者”。
- 是否和 heading chunk / metadata 有关: 可能有轻微关系，heading 改变了排序，减少了作者简介片段的干扰。
- 是否真实提升: 部分真实。它改善了 no-answer 场景中的干扰上下文，但主要仍是评测措辞与上下文噪声变化。

## 4. heading 退化的 case

### paper001_q004

- question: 论文中的次模性思想是如何服务于极小图结构分析的？
- fixed 为什么能过: fixed 命中“关键集”“紧集”“必然存在”，strict keyword_hit_rate=0.5。
- heading 为什么失败: heading 命中“关键集”“紧集”，但漏掉“必然存在”，strict keyword_hit_rate 降到 0.3333；relaxed 仍通过。
- 是否因为 chunk 边界变化导致关键信息丢失: 可能有轻微影响，heading 更偏摘要/关键词，低度顶点存在性的表述没有被模型复述成预期词。
- 是否召回片段变差: 不明显，heading 召回仍包含摘要、关键词和方法相关信息。
- 是否只是关键词命中下降但语义正确: 基本是。回答语义仍在讲次模性、关键集、紧集如何支撑结构推导。

### paper001_q010

- question: 这篇论文是否提供了每位实验参与者的个人身份信息和联系方式？
- fixed 为什么能过: fixed 回答末尾包含“当前上传文档中没有找到直接依据”一类 strict no-evidence 表达。
- heading 为什么失败: heading 回答语义上也是否定回答，但没有命中 strict/relaxed no-evidence 词表中的关键短语，评测脚本将其判为失败，并标记 `retrieval_context_weak`。
- 是否因为 chunk 边界变化导致关键信息丢失: 不是。no-answer 题本来没有正向证据。
- 是否召回片段变差: heading 召回的是题名、关键词、理论背景等片段，没有召回明显“不该召回”的参与者上下文。
- 是否只是关键词命中下降但答案语义仍然正确: 是。它是 no-answer 判定规则退化，不是明显 RAG 事实错误。

### paper003_q005

- question: 论文实验中与基准模型相比取得了怎样的准确率提升？
- fixed 为什么能过: fixed 召回到比较实验/图 9 附近片段，回答命中“四种基准模型”“平均准确率”“5.24%”“RF-CNN-CBAM-BiLSTM”。
- heading 为什么失败: heading 顶部片段虽然包含“5.24%”，但上下文更短或更偏摘要句，回答只命中“5.24%”和模型名，漏“四种基准模型”“平均准确率”“提高”。
- 是否因为 chunk 边界变化导致关键信息丢失: 是，可能是较明确的边界/排序退化。heading 取到了关键数字，但没有稳定保留比较对象和指标语义。
- 是否召回片段变差: 是。fixed 的结果更靠近完整比较分析，heading 的结果更像压缩后的局部事实。
- 是否只是关键词命中下降但答案语义仍然正确: 部分正确，但答案缺少“相对四种基准模型平均准确率提高”的完整关系，因此算真实退化。

## 5. heading 仍失败的 case 分类

### likely_eval_keyword_too_strict

- case: paper001_q002, paper001_q004, paper001_q007, paper002_q002, paper002_q004, paper004_q005, paper004_q006, paper004_q007, paper005_q007
- 代表 case: paper001_q002 和 paper004_q007。
- 失败原因: 多数回答语义接近标准答案，但没有命中严格关键词或同义表达。例如图类名称、方法概念、综述分析维度在答案中有描述，但 expected keywords 要求字面命中。
- 是否是真 RAG 问题: 大多不是纯 RAG 问题；retrieved chunks 通常非空且相关。
- 是否是评测规则问题: 是主要因素。relaxed_pass 多数为 true。
- 后续优先方向: 优先调 eval keywords/同义词组，其次调 prompt 让回答更贴近标准术语；chunk 策略优先级较低。

### retrieval_context_weak

- case: paper001_q010, paper003_q007, paper004_q002, paper004_q008
- 代表 case: paper003_q007 和 paper004_q008。
- 失败原因: 对实验结果或综述结论类问题，heading 召回常拿到概览片段，但未覆盖完整指标、比较对象或结论建议。paper001_q010 是 no-answer 评测逻辑问题。
- 是否是真 RAG 问题: paper003_q007、paper004_q008 更像真实 retrieval 问题；paper004_q002 介于 retrieval 和关键词评测之间；paper001_q010 更像评测规则问题。
- 是否是评测规则问题: 部分是，尤其 no-answer 题和综述问题的中文关键词匹配。
- 后续优先方向: 对真实 retrieval 弱样本优先尝试 rerank、query rewrite、metadata 加权和 top_k；对 no-answer 先调 eval/prompt。

### answer_keyword_mismatch

- case: paper002_q008, paper003_q005, paper005_q008
- 代表 case: paper003_q005。
- 失败原因: 检索有部分相关内容，但答案没有覆盖关键数字、比较对象或未来方向关键词。
- 是否是真 RAG 问题: 一部分是生成覆盖不足，一部分是检索片段不完整。
- 是否是评测规则问题: 次要因素。paper003_q005 需要精确数字和比较对象，属于合理评测要求。
- 后续优先方向: 优先 prompt 强化“回答必须覆盖数字、对象、比较关系”，再考虑 rerank/top_k；chunk 策略不是第一优先。

### 其他

- no_retrieval: 0
- wrong_document: 0
- timeout: 0
- rag_error: 0

## 6. retrieval_context_weak 专项分析

### paper001_q010

- 问题类型: no-answer 型。
- 当前 heading 检索上下文为什么弱: no-answer 题的 expected keywords 是“没有提供/未提到/无法从论文中得出”，这些短语通常不会出现在原文 retrieved chunks 中。评测脚本在 relaxed no-answer 不通过后，又用 expected keywords 检查上下文，因此容易把正确拒答误标成 `retrieval_context_weak`。
- 可能原因判断: 主要是评测脚本/拒答措辞问题，不是 top_k、threshold 或 chunk 粒度问题。
- 后续更适合尝试: eval keyword 调整和 prompt 固定拒答模板；暂不建议用 top_k/threshold 处理。

### paper003_q007

- 问题类型: 实验型 / result 型。
- 当前 heading 检索上下文为什么弱: heading 召回到实验结果段落、数据划分和混淆矩阵附近，但没有稳定覆盖“平均准确率提高 5.24%”和“运行时间缩短 68.25 秒”的比较结论。
- 可能原因判断: top_k 有可能不够；排序更关键；chunk 粒度也可能把“实验结果”和“对比分析/效率结论”拆散。
- 后续更适合尝试: rerank、query rewrite、提高 top_k。query rewrite 可把“主要实验结果”扩展为“准确率、F1、运行时间、基准模型对比”。

### paper004_q002

- 问题类型: 总结型 / overview 型。
- 当前 heading 检索上下文为什么弱: heading top chunk 实际包含“网络架构、监督范式、数据集、评估指标、定性/定量/运行效率”等概览信息，但回答只命中“运行效率”，说明问题不完全在 retrieval，也有答案组织和关键词匹配问题。
- 可能原因判断: section 不匹配影响较小；chunk 粒度尚可；更像 prompt 没有按 gold answer 的“三个方面”组织。
- 后续更适合尝试: eval keyword 调整、prompt 约束“按问题枚举维度”；其次是 heading metadata 加权，让 Introduction/Abstract 的 overview chunk 更稳定靠前。

### paper004_q008

- 问题类型: 总结型 / conclusion 型。
- 当前 heading 检索上下文为什么弱: 召回到英文摘要里的 challenge/future analysis 句子，但没有稳定命中中文 expected keywords，如“不同场景”“算法局限性”“研究建议”“后续研究”。
- 可能原因判断: section 不匹配和排序问题更明显，结论/建议类问题需要 Conclusion 或 abstract conclusion 的高权重。
- 后续更适合尝试: heading metadata 加权、rerank、query rewrite。query rewrite 可补充“conclusion, future work, challenges, suggestions”等英文/中文同义词。

## 7. no-answer 退化分析

退化 case 是 paper001_q010。

- question: 这篇论文是否提供了每位实验参与者的个人身份信息和联系方式？
- fixed 的回答: 明确回答“没有提供任何实验参与者的个人身份信息和联系方式”，并说明该论文是理论图论研究，不涉及实验参与者，末尾有“当前上传文档中没有找到直接依据”式表达，因此 strict/relaxed 都通过。
- heading 的回答: 同样明确回答“没有提供任何实验参与者的个人身份信息和联系方式”，并说明论文不涉及人类受试者、数据收集或隐私信息。但措辞更多使用“没有提供”“不涉及”“不存在、也无需提供”，没有命中评测脚本 strict/relaxed no-evidence 词表中的短语。
- heading 是否召回了不该召回的上下文: 没有明显召回实验参与者或隐私类误导上下文。top chunks 主要是题名/引用、关键词、理论背景和结语片段。
- 是否需要提高拒答阈值: 不建议优先调阈值。这不是相似度过低导致的错误。
- 是否需要对 reference section / 背景段落降权: 不是第一优先；本例没有明显 reference section 干扰。
- 是否是评测脚本判定问题: 是。no-answer 的 expected keywords 被用于 context weak 判断，而这些关键词本来不应出现在原文证据中；同时 no-evidence phrase 词表缺少“没有提供”。

## 8. 下一步建议

1. 先修正评测口径和 no-answer 判定：给 no-answer 增加“没有提供”等拒答短语，且 no-answer 不再用 expected answer keywords 判断 retrieval_context_weak。
2. 针对 paper003_q007、paper004_q008 做 retrieval 定向实验：先比较提高 top_k 与 rerank/query rewrite 的效果，不要直接大改 chunk。
3. 为 `likely_eval_keyword_too_strict` 扩充同义关键词和标准术语别名，再用同一份结果重算 strict/relaxed 差异，避免把语义正确误判成 RAG 失败。
