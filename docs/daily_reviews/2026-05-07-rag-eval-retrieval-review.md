# 2026-05-07 PaperPilot RAG 评测闭环与检索优化复盘

## 1. 今日目标

今天的目标不是继续堆 RAG 功能，而是补齐 parser/chunker 优化后的评测闭环。具体包括：

- 归档 fixed baseline；
- 重新确认 heading 结果；
- 做 fixed vs heading badcase 对齐；
- 修正 eval_v2；
- 补 expected_keyword_groups；
- 做 retrieval debug；
- 判断下一步是否进入 top_k=8 全量实验。

## 2. 起始问题：代码优化后没有有效评测闭环

parser/chunker 已经完成优化，但旧评测结果早于优化提交，不能直接代表优化后的系统表现。旧结果只能作为 fixed baseline 使用。heading 策略需要设置 `CHUNK_STRATEGY=heading` 后，重新入库并重新评测，才能和 fixed baseline 做有效对比。

本质问题是：代码优化和评测结果没有闭环。

风险包括：

- 容易误把旧结果当新结果；
- 容易盲目继续加功能；
- 无法判断优化是否有效。

## 3. 评测归档

今天将评测产物整理到 `eval/results` 目录结构下，避免 `eval` 根目录继续混乱：

- `baseline_fixed_20260503` 存 fixed baseline；
- `heading_20260504` 存 heading 结果；
- `heading_topk8_20260507` 存 top_k=8 单变量实验结果；
- `comparison` 存 fixed vs heading 对比和 badcase 分析。

结构如下：

```text
eval/results/
  baseline_fixed_20260503/
  heading_20260504/
  heading_topk8_20260507/
  comparison/
```

## 4. heading 初始评测结果

| 指标 | fixed baseline | heading |
|---|---:|---:|
| total | 50 | 50 |
| pass | 32 | 34 |
| pass_rate | 0.64 | 0.68 |
| avg_keyword_hit_rate | 0.446 | 0.427 |
| no-answer strict pass | 8/10 | 9/10 |
| no-answer relaxed pass | 10/10 | 9/10 |

heading 相比 fixed baseline 小幅提升，从 32/50 到 34/50。但 `avg_keyword_hit_rate` 下降，no-answer relaxed pass 也从 10/10 下降到 9/10。

因此不能只看总分。heading 的收益需要通过 badcase 对齐拆开看，判断哪些是真实检索收益，哪些是评测口径、prompt 表述或关键词映射问题。

## 5. badcase 对齐分析

| 类型 | 数量 |
|---|---:|
| fixed 失败 heading 通过 | 5 |
| fixed 通过 heading 失败 | 3 |
| 两者都失败 | 13 |
| 两者都通过 | 29 |

heading 净增 2 题，说明确实有收益，但也出现了退化。后续分析必须区分 retrieval、eval、prompt、关键词问题，避免把所有失败都当成检索系统问题。

重点 case：

- `paper004_q001`：heading 对主题/摘要类问题有效，属于真实提升；
- `paper001_q010`：heading 回答语义正确，但 no-answer 判定失败，属于 eval 问题；
- `paper003_q005`：heading 漏掉完整实验比较关系，属于真实退化或答案覆盖不足。

## 6. 错误尝试与修正一：一开始想直接改 retrieval_service.py

看到 heading 提升不大时，很容易直接上 query rewrite、rerank、metadata 加权、TopK/threshold 调参。

但当时还没有分清失败来源：到底是 eval 问题、retrieval 问题，还是 prompt 和关键词覆盖问题。如果直接改 `retrieval_service.py`，会混入新变量，后续无法归因，也无法判断 heading chunk 本身到底有没有收益。

最终修正为：先 badcase 对齐，再 eval_v2，再 retrieval debug，再做单变量 top_k 实验。

经验：RAG 优化不能一看到分数低就堆功能，要先定位问题类型，再做最小变量实验。

## 7. eval_v2：修正 no-answer 判定

新增脚本：

- `eval/recompute_rag_eval_v2.py`

eval_v2 规则：

- 扩充 no-answer 拒答短语；
- no-answer 不再用 expected_keywords 判断 `retrieval_context_weak`；
- 支持 `expected_keyword_groups`；
- 普通题 `keyword_hit_rate` 逻辑保持；
- 不重新调用后端，只基于已有 result jsonl 重算。

| 指标 | fixed eval_v1 | fixed eval_v2 | heading eval_v1 | heading eval_v2 |
|---|---:|---:|---:|---:|
| pass | 32 | 34 | 34 | 35 |
| pass_rate | 0.64 | 0.68 | 0.68 | 0.70 |
| no-answer strict pass | 8/10 | 10/10 | 9/10 | 10/10 |
| no-answer relaxed pass | 10/10 | 10/10 | 9/10 | 10/10 |

eval_v2 后，heading 仍比 fixed 好，但优势从 eval_v1 的 +2 缩小到 +1。这说明一部分提升来自 no-answer 评测口径修正，而不完全是 heading chunk 的系统能力提升。

## 8. expected_keyword_groups 修正

本轮只修改：

- `eval/rag_eval_dataset_5papers_checked.jsonl`

修改范围只包括：

- `paper004_q002`
- `paper004_q008`

处理方式：

- 只补 `expected_keyword_groups`；
- 原 `expected_keywords` 保留；
- 不重新调用 LLM；
- 不重新上传、解析或 embedding。

修正原因：

- `paper004_q002` 已经召回网络架构、监督范式、评估指标、运行效率等核心信息；
- `paper004_q008` rank1 已经召回 conclusion、challenges、forecasting analysis 等核心片段；
- 但原 expected_keywords 的中英文映射过硬，导致语义正确的召回和回答被错误判为弱。

修正后：

- heading 提升到 37/50；
- `pass_rate=0.74`；
- `retrieval_context_weak` 只剩 `paper003_q007`。

这一步是评测口径修正，不是系统检索能力提升。

## 9. 错误尝试与修正二：误把 paper004_q002 / paper004_q008 当成检索问题

`paper004_q002` 和 `paper004_q008` 一开始被标记为 `retrieval_context_weak`，但 retrieval debug 显示，baseline 已经召回核心片段。

进一步看，top_k 提高和 threshold 降低都没有明显改善这两个 case。最后判断它们主要是 eval keyword 和中英文表达映射问题，而不是真正的检索失败。

经验：`fail_reason` 只是初步标签，必须结合 retrieved chunks 做人工诊断。

## 10. retrieval debug 诊断

新增脚本：

- `eval/debug_retrieval_cases.py`

诊断特点：

- 不调用 LLM；
- 不重新入库；
- 只做 query embedding + pgvector 检索；
- 对比不同 top_k / threshold 下 retrieved chunks。

参数组合：

- `top_k=6, threshold=0.25`
- `top_k=8, threshold=0.25`
- `top_k=10, threshold=0.25`
- `top_k=10, threshold=0.20`
- `top_k=12, threshold=0.20`

| case_id | 判断 | 下一步 |
|---|---|---|
| `paper003_q007` | top_k=6 没召回完整实验结论，top_k=8 后相关片段出现 | 提高 top_k |
| `paper004_q002` | 已召回概览片段 | eval keyword / prompt |
| `paper004_q008` | rank1 已召回 conclusion/challenges | eval keyword |

降低 `similarity_threshold` 没有明显改善，当前更值得验证的是 top_k 单变量。

## 11. top_k=8 实验状态

已确认文件：

- `eval/results/heading_topk8_20260507/README.md`

README 中有明确 top_k=8 指标：

| 指标 | heading top_k=6 eval_v2_groups | heading top_k=8 eval_v2_groups |
|---|---:|---:|
| total | 50 | 50 |
| passed | 37 | 36 |
| pass_rate | 0.74 | 0.72 |
| relaxed_passed | 46 | 43 |
| relaxed_pass_rate | 0.92 | 0.86 |
| avg_keyword_hit_rate | 0.457 | 0.4442 |
| answer_keyword_mismatch | 3 | 6 |
| likely_eval_keyword_too_strict | 9 | 7 |
| retrieval_context_weak | 1 | 1 |

README 结论是：`top_k=8` 对 `paper003_q007` 的检索弱问题有局部改善，但没有让该 case 通过；整体 eval_v2_groups 从 37/50 降到 36/50。单变量实验结果不支持把 heading 默认 `top_k` 从 6 调到 8。

同时，独立的完整 comparison 文件缺失：

- `eval/results/comparison/heading_topk6_vs_topk8_compare.md`
- `eval/results/comparison/heading_topk6_vs_topk8_compare.json`

另外，当前未发现文件名包含 `eval_v2_groups` 的独立 summary。也就是说，top_k=8 实验目录已存在且 README 有指标，但后续仍需要补齐 top_k=6 vs top_k=8 的全量对比文件和命名一致的 eval_v2_groups summary。

## 12. 今日最终结论

1. heading chunk 有小幅收益，但不是决定性提升；
2. 原始评测存在 no-answer 和关键词过严问题；
3. eval_v2 后 heading 仍略优于 fixed，但真实提升变小；
4. expected_keyword_groups 修正后 heading 达到 37/50；
5. `paper004_q002` 和 `paper004_q008` 不再认为是真 retrieval 问题；
6. 当前真正剩余的 retrieval 问题主要是 `paper003_q007`；
7. retrieval debug 证明 `paper003_q007` 受 top_k 影响；
8. top_k=8 README 显示全局指标下降到 36/50，因此下一步应补齐 top_k=6 vs top_k=8 全量对比，而不是直接上 Query Rewrite / Rerank。

## 13. 今日新增/修改文件汇总

### 评测归档

已存在：

- `eval/results/baseline_fixed_20260503/README.md`
- `eval/results/baseline_fixed_20260503/rag_eval_summary_5papers.json`
- `eval/results/baseline_fixed_20260503/rag_eval_summary_5papers_eval_v2.json`
- `eval/results/baseline_fixed_20260503/rag_eval_result_5papers.jsonl`
- `eval/results/baseline_fixed_20260503/rag_eval_result_5papers_eval_v2.jsonl`
- `eval/results/heading_20260504/README.md`
- `eval/results/heading_20260504/rag_eval_summary_heading.json`
- `eval/results/heading_20260504/rag_eval_summary_heading_eval_v2.json`
- `eval/results/heading_20260504/rag_eval_result_heading.jsonl`
- `eval/results/heading_20260504/rag_eval_result_heading_eval_v2.jsonl`

### Badcase 分析

已存在：

- `eval/results/comparison/fixed_vs_heading_compare.md`
- `eval/results/comparison/fixed_vs_heading_compare.json`
- `eval/results/comparison/fixed_vs_heading_badcase_analysis.md`
- `eval/results/comparison/fixed_vs_heading_badcase_analysis.json`

### Eval v2

已存在：

- `eval/recompute_rag_eval_v2.py`
- `eval/results/comparison/fixed_vs_heading_eval_v2_compare.md`
- `eval/results/comparison/fixed_vs_heading_eval_v2_compare.json`

### Keyword Groups

已存在：

- `eval/rag_eval_dataset_5papers_checked.jsonl`

说明：该文件中补充了 `paper004_q002` 和 `paper004_q008` 的 `expected_keyword_groups`。

### Retrieval Debug

已存在：

- `eval/debug_retrieval_cases.py`
- `eval/results/heading_20260504/retrieval_debug_cases.md`
- `eval/results/heading_20260504/retrieval_debug_cases.json`

### TopK Experiment

已存在：

- `eval/results/heading_topk8_20260507/README.md`
- `eval/results/heading_topk8_20260507/rag_eval_summary_heading_topk8.json`
- `eval/results/heading_topk8_20260507/rag_eval_summary_heading_topk8_eval_v2.json`
- `eval/results/heading_topk8_20260507/rag_eval_result_heading_topk8.jsonl`
- `eval/results/heading_topk8_20260507/rag_eval_result_heading_topk8_eval_v2.jsonl`
- `eval/results/heading_topk8_20260507/rag_eval_badcases_heading_topk8.jsonl`
- `eval/results/heading_topk8_20260507/rag_eval_badcases_heading_topk8_eval_v2.jsonl`

### 待补齐文件

未发现：

- `eval/results/comparison/heading_topk6_vs_topk8_compare.md`
- `eval/results/comparison/heading_topk6_vs_topk8_compare.json`
- 文件名包含 `eval_v2_groups` 的 top_k=8 独立 summary 或 group summary

## 14. 面试表述版本

这次我没有凭感觉去优化 RAG，也没有一看到分数不高就马上加 Query Rewrite 或 Rerank。我先把旧结果归档成 fixed baseline，再用 heading chunk 重新评测，确认它从 32/50 提到 34/50，但提升并不稳定，所以继续做 fixed vs heading 的 badcase 对齐。

对齐后发现，问题不全在检索。有些是 no-answer 判定口径不合理，有些是 expected_keywords 对中英文表达映射过硬。于是我先做 eval_v2 重算，再补 expected_keyword_groups，最后用不调用 LLM 的 retrieval debug 验证真正剩余的检索问题。最终链路是：heading eval_v2_groups 到 37/50，主要剩余 retrieval case 集中在 `paper003_q007`，并且 debug 显示它受 top_k 影响。这个过程体现的是工程化评测闭环，而不是盲目堆 RAG 功能。

## 15. 文档生成后的最终回复

- 生成的 Markdown 文件路径：`docs/daily_reviews/2026-05-07-rag-eval-retrieval-review.md`
- 是否读取到 top_k=8 完整对比结果：读取到 `heading_topk8_20260507/README.md` 中的明确指标；未读取到独立的 `heading_topk6_vs_topk8_compare.md/json` 完整对比文件。
- 今日最终指标链路：
  - fixed baseline 32/50；
  - heading eval_v1 34/50；
  - heading eval_v2 35/50；
  - heading eval_v2_groups 37/50；
  - heading top_k=8：README 指标为 36/50，pass_rate=0.72，但独立 comparison 文件待补齐。
- 下一步建议：补齐 top_k=6 vs top_k=8 的全量对比文件和命名一致的 eval_v2_groups summary，再决定是否保留 top_k=6 或局部策略化提高 top_k；暂时不建议直接上 Query Rewrite / Rerank。
