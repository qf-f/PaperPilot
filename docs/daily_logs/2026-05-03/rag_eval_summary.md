# 2026-05-03 RAG 评测结果归档

## 本次评测目的

本次评测用于验证 PaperPilot 在多论文场景下的 RAG 问答能力，并形成后续 RAG 链路优化前的 baseline。重点观察：

- 检索是否命中目标论文。
- 回答是否覆盖标准答案关键词。
- 引用和证据是否来自对应文档。
- 不可回答问题是否明确拒答。
- 失败样本主要来自评测关键词过严，还是来自检索或生成链路问题。

## 数据集文件

```text
eval/rag_eval_dataset_5papers_checked.jsonl
```

该数据集包含 5 篇论文，每篇 10 条样本，共 50 条。样本字段包括 `paper_id`、`paper_title`、`question`、`gold_answer`、`expected_keywords`、`expected_section`、`expected_page`、`type`、`difficulty`、`is_answerable` 等。

## 运行命令

推荐命令：

```powershell
python eval/run_rag_eval.py --project-id 084b24a2-a7a5-4bad-832e-5cb1d2286494 --api-url http://localhost:8000 --dataset eval/rag_eval_dataset_5papers_checked.jsonl --documents-map eval/rag_eval_documents.json --output eval/rag_eval_result_5papers.jsonl --summary-output eval/rag_eval_summary_5papers.json --save-badcases eval/rag_eval_badcases_5papers.jsonl
```

## 输出文件

```text
eval/rag_eval_result_5papers.jsonl
eval/rag_eval_summary_5papers.json
eval/rag_eval_badcases_5papers.jsonl
eval/rag_eval_documents.json
```

其中：

- `rag_eval_result_5papers.jsonl`：逐题结果，包含回答、关键词命中、检索 chunk、score、页码、目标文档和失败原因。
- `rag_eval_summary_5papers.json`：整体统计、按论文统计、按失败原因统计。
- `rag_eval_badcases_5papers.jsonl`：只保留 strict `pass=false` 的样本，便于人工分析。
- `rag_eval_documents.json`：`paper_id` 到 `document_id` 和 `file_name` 的映射，用于避免多文档串文档。

## 指标说明

- `keyword_hit_count`：模型回答中命中的 `expected_keywords` 数量。
- `keyword_hit_rate`：`keyword_hit_count / expected_keywords 总数`。
- `pass`：strict 评测结果。可回答样本要求关键词命中率达到阈值；不可回答样本要求模型明确拒答。
- `is_answerable=false`：无答案样本。模型应说明论文未提供相关依据，不能凭空回答。
- `relaxed_pass`：辅助评测结果。允许关键词归一化、同义词组和更宽的拒答表达，仅用于人工参考，不替代 strict baseline。
- `fail_reason`：失败原因，包括 `answer_keyword_mismatch`、`likely_eval_keyword_too_strict`、`retrieval_context_weak`、`wrong_document`、`no_retrieval`、`timeout` 等。

## 当前结果理解

最新一次评测结果：

- 总样本数：50
- strict 通过数：32
- strict 通过率：0.64
- relaxed 通过数：43
- relaxed 通过率：0.86
- strict 无答案通过率：0.80
- relaxed 无答案通过率：1.00
- `wrong_document_count=0`
- `no_retrieval_count=0`
- `likely_eval_keyword_too_strict_count=11`
- `retrieval_context_weak_count=4`
- `answer_keyword_mismatch_count=3`

结果说明：

1. 多文档串文档问题已经基本解决，当前没有出现 wrong document 统计。
2. 一部分 strict 失败样本属于关键词字面匹配过硬，已通过 relaxed 逻辑标记为 `likely_eval_keyword_too_strict`。
3. 仍有少量样本属于 `retrieval_context_weak` 或 `answer_keyword_mismatch`，需要进入 RAG 链路优化。
4. 无答案问题在 relaxed 口径下全部通过，说明拒答能力基本可用，但 strict 句式仍可继续统一。

## 为什么可作为优化前 baseline

本次评测已经具备以下条件：

- 数据集固定，便于重复运行。
- 文档映射固定，避免多文档串文档。
- 逐题结果包含检索证据，便于定位失败原因。
- summary 提供整体、按论文和按失败原因统计。
- badcases 可直接用于人工复核。

因此，本次结果可以作为 RAG 链路优化前 baseline。后续每次调整 chunk、检索、向量库或 prompt 后，都应在同一数据集上重新运行，并对比 strict 与 relaxed 指标变化。

## 后续优化方向

1. 优化 `chunker.py`，从固定长度切分升级为标题感知和语义切分，降低上下文断裂。
2. 调整 `top_k` 和 `similarity_threshold`，观察召回数量、score 和回答准确率的变化。
3. 增加 Milvus 向量库接入入口，为更大规模论文库检索做准备。
4. 增强 source citation 和 evidence 注入，让回答更稳定引用目标 chunk。
5. 优化 no-answer 场景，减少无依据回答，并统一拒答格式。
6. 增加优化前后对比表，持续记录 strict pass rate、relaxed pass rate、badcase 分布和失败原因变化。
