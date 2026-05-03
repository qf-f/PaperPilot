# 2026-05-03 PaperPilot 问题复盘与解决方案

## 1. RAG 评测闭环缺少统一脚本

**问题现象**

项目已有论文解析、切分、向量化、检索和问答链路，但缺少一个可重复运行的 RAG 评测入口。此前难以稳定记录每个问题的模型回答、关键词命中情况、不可回答问题拒答情况，以及整体通过率。

**原因分析**

RAG 功能主要服务于交互式论文问答，评测逻辑尚未独立成脚本。人工检查回答可以发现问题，但无法形成可量化 baseline，也不便于后续比较 chunk、TopK、similarity threshold、rerank 等优化效果。

**解决方案**

新增并完善 `eval/run_rag_eval.py`。脚本支持：

- 逐行读取 JSONL 评测数据集。
- 调用当前项目的 `ChatService` 或 FastAPI `/api/chat`。
- 记录每条样本的 `answer`。
- 统计 `keyword_hit_count` 和 `keyword_hit_rate`。
- 对 `is_answerable=false` 样本检查模型是否明确拒答。
- 输出逐题结果 JSONL。
- 输出 summary 和 badcases 文件，便于定位失败样本。

**当前状态**

基础评测闭环已经跑通，可以稳定生成 `eval/rag_eval_result_5papers.jsonl` 和 `eval/rag_eval_summary_5papers.json`。

**后续优化建议**

继续保留该脚本作为 RAG 优化前后的统一评测入口。后续每次调整 chunk、检索参数或引用策略后，都应重新运行同一数据集并对比指标变化。

## 2. 数据集文件名不一致导致 FileNotFoundError

**问题现象**

运行评测脚本时曾出现 `FileNotFoundError`。命令中使用的数据集路径为：

```powershell
eval/rag_eval_dataset_5papers.checked.jsonl
```

但项目中实际文件名为：

```powershell
eval/rag_eval_dataset_5papers_checked.jsonl
```

**原因分析**

文件名中的分隔符不一致：命令使用了点号 `.checked`，实际文件使用下划线 `_checked`。评测脚本按用户传入路径直接读取文件，因此无法找到数据集。

**解决方案**

改用正确命令运行：

```powershell
python eval/run_rag_eval.py --project-id 084b24a2-a7a5-4bad-832e-5cb1d2286494 --api-url http://localhost:8000 --dataset eval/rag_eval_dataset_5papers_checked.jsonl --output eval/rag_eval_result_5papers.jsonl
```

**当前状态**

文件路径问题已解决。当前数据集统一使用 `eval/rag_eval_dataset_5papers_checked.jsonl`。

**后续优化建议**

在评测 README 中固定推荐命令，避免再次手工输入错误路径。后续也可以给常用评测命令封装 PowerShell 脚本。

## 3. 多文档评测中出现串文档回答

**问题现象**

上传 5 篇论文后，评测时部分问题答到了其他论文内容。例如 `paper001` 问题关注“次模性在极小图类结构研究中的应用”，模型却回答成“深度学习目标检测算法综述”相关内容。

**原因分析**

早期评测只传入 `project_id`，后端按整个项目检索。多篇论文共处同一项目时，检索召回可能跨文档，导致问题与目标论文不一致。

**解决方案**

新增 `eval/rag_eval_documents.json`，记录：

- `paper_id`
- `document_id`
- `file_name`

同时增强 `eval/run_rag_eval.py`，按每条样本的 `paper_id` 查找目标 `document_id`，并调用后端时传入文档过滤信息。后端 `ChatRequest` 支持 `document_id` 和 `file_name`，再转成已有的 `document_ids` 过滤逻辑。

**当前状态**

多文档串文档问题已明显缓解。当前评测结果中 `wrong_document_count=0`，说明目标文档过滤已经生效。

**后续优化建议**

继续保留文档级过滤作为多文档评测默认行为。后续可以在结果中持续检查 `retrieved_document_ids` 是否只包含目标文档，作为回归验证。

## 4. keyword_hit_rate 偏低，部分语义正确回答被判失败

**问题现象**

当前 50 条样本中，部分回答语义上基本正确，但因为没有逐字命中 `expected_keywords`，导致 `pass=false`，失败原因集中在 `answer_keyword_mismatch`。

**原因分析**

早期评测使用较严格的字符串包含匹配。中文表达、英文术语、公式写法、空格和标点差异都会影响命中。例如同一概念可能写成中文、英文或不同公式格式。

**解决方案**

保留原始 strict 指标，同时新增 relaxed 辅助判断：

- 关键词归一化，包括大小写、空格和中英文标点。
- 支持 `A|B|C` 同义词组。
- 对 `QKT`、`QK^T`、`QK^T / sqrt(dk)` 等公式表达做简单近似匹配。
- 对疑似评测关键词过严的样本标记 `likely_eval_keyword_too_strict`，不直接混入 strict pass。

**当前状态**

最新一次评测中，strict 通过率为 `0.64`，relaxed 通过率为 `0.86`。其中 `likely_eval_keyword_too_strict_count=11`，说明不少失败样本更适合进入人工复核或优化评测题，而不是直接归因于 RAG 链路失败。

**后续优化建议**

保留 strict 作为硬指标，relaxed 作为人工分析参考。对 `likely_eval_keyword_too_strict` 样本应优先检查 `expected_keywords` 是否需要补充同义词或更贴近论文表达。

## 5. 不可回答问题的拒答句式过窄

**问题现象**

部分无答案样本中，模型回答了“未提供”“没有提到”等拒答表达，但没有命中固定拒答句式，导致被误判为失败。

**原因分析**

不可回答样本最初只匹配少数固定句式，未覆盖常见拒答变体。RAG 模型在表达“不知道”时可能使用不同措辞。

**解决方案**

扩展无答案判断规则，识别：

- 未提供
- 没有提到
- 未明确说明
- 无法根据本文得出
- 文档中没有相关依据
- 不能根据本文得出

并保留 strict 与 relaxed 两套口径。

**当前状态**

最新评测中，strict 无答案通过率为 `0.80`，relaxed 无答案通过率为 `1.00`。这说明基础拒答能力已经具备，但 strict 句式仍偏硬。

**后续优化建议**

无答案场景应继续优化 prompt 和 evidence 注入，使模型稳定输出清晰的拒答格式，同时避免在缺少依据时给出肯定答案。

## 6. 当前评测结果暴露出的 RAG 链路优化方向

**问题现象**

虽然基础评测闭环已经跑通，但仍存在：

- 部分 `keyword_hit_rate` 偏低。
- 部分样本 `pass=false`。
- 部分失败属于评测关键词过严。
- 部分失败属于检索上下文不足或召回片段不够聚焦。

**原因分析**

失败样本可能来自两类来源：

1. 评测题或关键词设计问题：标准关键词过窄，没有覆盖同义表达。
2. RAG 链路问题：chunk 切分粒度、标题结构、TopK、相似度阈值、证据注入和拒答策略仍有优化空间。

**解决方案**

本次已将评测结果扩展为可观测输出，包括检索 chunk、页码、score、目标文档、失败原因和 badcases 文件，便于逐条定位问题。

**当前状态**

当前结果可以作为优化前 baseline。评测链路、数据集、文档映射和结果输出均已具备可复现性。

**后续优化建议**

下一步应进入 RAG 链路优化，重点包括：

1. 将 `chunker.py` 从固定长度切分升级为 heading-aware chunking 和语义切分。
2. 调整 `top_k` 和 `similarity_threshold`。
3. 预留或接入 Milvus 向量库入口。
4. 增强 source citation 和 evidence 注入。
5. 优化 no-answer 场景，减少无依据回答。
6. 建立优化前后对比表，用同一数据集持续衡量变化。
