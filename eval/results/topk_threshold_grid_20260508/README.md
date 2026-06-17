# TopK + Similarity Threshold Grid Experiment - 2026-05-08

## 1. 实验目的

本轮实验验证 heading chunk 策略下，`top_k` 和 `similarity_threshold` 联合调整是否能提升 RAG 评测指标。此前单独把 `top_k` 从 6 提到 8，在 `similarity_threshold=0.25` 下没有稳定提升，说明需要同时观察召回数量和相似度过滤强度。

## 2. 实验设置

- `CHUNK_STRATEGY=heading`
- 使用已有 heading chunks，不重新上传、不重新解析、不重新 embedding
- 不改数据库结构，不接入 rerank/query rewrite/metadata 加权
- 不改 prompt，不改 eval 数据集
- 只改变 `top_k` 和 `similarity_threshold`
- eval_v2 使用 `eval/rag_eval_dataset_5papers_checked.jsonl` 中的 `expected_keyword_groups`

## 3. 总表

| run | top_k | threshold | pass_rate | relaxed_pass_rate | avg_hit | no_retrieval | answer_mismatch | retrieval_weak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| heading_topk6_th030 | 6 | 0.3 | 0.74 | 0.9 | 0.4592 | 0 | 3 | 2 |
| heading_topk4_th030 | 4 | 0.3 | 0.74 | 0.9 | 0.4508 | 0 | 1 | 4 |
| heading_topk6_th025 | 6 | 0.25 | 0.74 | 0.88 | 0.4639 | 0 | 4 | 2 |
| heading_topk4_th035 | 4 | 0.35 | 0.74 | 0.88 | 0.4523 | 0 | 2 | 4 |
| heading_topk8_th035 | 8 | 0.35 | 0.74 | 0.86 | 0.457 | 0 | 6 | 1 |
| heading_topk8_th030 | 8 | 0.3 | 0.72 | 0.86 | 0.4347 | 0 | 6 | 1 |
| heading_topk8_th025 | 8 | 0.25 | 0.7 | 0.88 | 0.448 | 0 | 5 | 1 |
| heading_topk6_th035 | 6 | 0.35 | 0.7 | 0.86 | 0.4521 | 0 | 4 | 3 |
| heading_topk4_th025 | 4 | 0.25 | 0.6 | 0.74 | 0.3375 | 7 | 2 | 4 |

## 4. 最佳组合

- strict pass_rate 最佳组合：`heading_topk6_th030`，top_k=6，similarity_threshold=0.3，pass_rate=0.74。
- relaxed_pass_rate=0.9，avg_keyword_hit_rate=0.4592，retrieval_context_weak_count=2，answer_keyword_mismatch_count=3，unanswerable_pass_rate=1.0。
- 存在多个 strict pass_rate 并列组合，排序进一步参考 relaxed_pass_rate、avg_keyword_hit_rate 和失败类型计数。
- 配置建议：暂不推荐替换当前默认配置。

## 5. 对 top_k 的观察

- top_k=4: avg_pass_rate=0.6933，avg_relaxed_pass_rate=0.84，avg_answer_keyword_mismatch=1.67。
- top_k=6: avg_pass_rate=0.7267，avg_relaxed_pass_rate=0.88，avg_answer_keyword_mismatch=3.67。
- top_k=8: avg_pass_rate=0.72，avg_relaxed_pass_rate=0.8667，avg_answer_keyword_mismatch=5.67。
- 若 top_k 增大没有稳定提升，说明新增上下文并不总能转化为答案关键词命中。
- 需要关注 top_k=8 是否只改善少数 case，同时让部分原本通过的 case 因上下文噪声而退化。

## 6. 对 similarity_threshold 的观察

- threshold=0.25: avg_pass_rate=0.68，avg_no_retrieval=2.33，avg_retrieval_context_weak=2.33。
- threshold=0.3: avg_pass_rate=0.7333，avg_no_retrieval=0.0，avg_retrieval_context_weak=2.33。
- threshold=0.35: avg_pass_rate=0.7267，avg_no_retrieval=0.0，avg_retrieval_context_weak=2.67。
- 本轮 threshold=0.30 的平均 pass_rate 最高；threshold=0.35 没有带来 no_retrieval 增加，但 retrieval_context_weak 略高。
- 当前更像是上下文噪声与评测关键词严格度共同影响，而不是单纯召回不足。

## 7. Badcase 分析

### 多个组合下都失败

- paper001_q002 (likely_eval_keyword_too_strict)
- paper001_q007 (likely_eval_keyword_too_strict)
- paper002_q002 (likely_eval_keyword_too_strict)
- paper002_q004 (answer_keyword_mismatch, likely_eval_keyword_too_strict)
- paper002_q008 (answer_keyword_mismatch)
- paper003_q007 (answer_keyword_mismatch, retrieval_context_weak)
- paper004_q005 (likely_eval_keyword_too_strict, retrieval_context_weak)
- paper004_q006 (likely_eval_keyword_too_strict)
- paper004_q007 (answer_keyword_mismatch, retrieval_context_weak)
- paper005_q008 (answer_keyword_mismatch, likely_eval_keyword_too_strict)

### 只在某些 threshold 下通过

- paper001_q004 at top_k=8: [(0.25, True), (0.3, True), (0.35, False)]
- paper001_q005 at top_k=4: [(0.25, False), (0.3, True), (0.35, True)]
- paper001_q005 at top_k=8: [(0.25, False), (0.3, False), (0.35, True)]
- paper001_q006 at top_k=8: [(0.25, True), (0.3, False), (0.35, True)]
- paper001_q008 at top_k=8: [(0.25, False), (0.3, True), (0.35, True)]
- paper003_q005 at top_k=6: [(0.25, True), (0.3, False), (0.35, False)]
- paper003_q008 at top_k=4: [(0.25, True), (0.3, False), (0.35, True)]
- paper004_q001 at top_k=6: [(0.25, True), (0.3, True), (0.35, False)]
- paper004_q003 at top_k=8: [(0.25, True), (0.3, False), (0.35, False)]
- paper005_q001 at top_k=4: [(0.25, False), (0.3, True), (0.35, True)]
- paper005_q001 at top_k=8: [(0.25, False), (0.3, True), (0.35, True)]
- paper005_q002 at top_k=4: [(0.25, False), (0.3, True), (0.35, True)]

### top_k 增大后反而失败

- paper001_q005 at threshold=0.25
- paper001_q005 at threshold=0.3
- paper001_q006 at threshold=0.3
- paper001_q008 at threshold=0.25
- paper004_q001 at threshold=0.25
- paper004_q001 at threshold=0.3
- paper004_q003 at threshold=0.3
- paper004_q003 at threshold=0.35
- paper005_q001 at threshold=0.25

## 8. 文件说明

- `runs/heading_topk*_th*/`: 每组 raw result、raw summary、eval_v2 result、eval_v2 summary、eval_v2 badcases。
- `grid_compare.md` / `grid_compare.json`: 9 组汇总对比。
- `badcases/`: 跨组合 badcase 汇总，包括 always failed、threshold sensitive 和 top_k noise cases。
- `archive/`: 本地运行日志目录，日志由 `.gitignore` 忽略，不建议提交。
