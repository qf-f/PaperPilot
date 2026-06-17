# Heading TopK=8 Eval

本实验只验证一个变量：`top_k` 从 6 调整为 8。其余条件保持不变：

- `CHUNK_STRATEGY=heading`
- `similarity_threshold=0.25`
- 使用已入库 heading chunks
- 不重新上传、不重新解析、不重新 embedding
- 不接入 rerank / query rewrite / metadata 加权

## 输出文件

- `rag_eval_result_heading_topk8.jsonl`
- `rag_eval_summary_heading_topk8.json`
- `rag_eval_badcases_heading_topk8.jsonl`
- `rag_eval_result_heading_topk8_eval_v2.jsonl`
- `rag_eval_summary_heading_topk8_eval_v2.json`
- `rag_eval_badcases_heading_topk8_eval_v2.jsonl`

## 指标对比

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

## 重点 Case

| case_id | top_k=6 | top_k=8 | 观察 |
|---|---|---|---|
| paper003_q007 | pass=false, retrieval_context_weak | pass=false, answer_keyword_mismatch | top_k=8 召回了实验对比片段，但答案仍未命中 5.24% / 68.25 秒 |
| paper004_q002 | pass=true | pass=true | expected_keyword_groups 修正后保持通过 |
| paper004_q008 | pass=true | pass=true | expected_keyword_groups 修正后保持通过 |
| paper003_q005 | pass=false | pass=true | top_k=8 下该准确率提升题通过 |
| paper005_q007 | pass=false | pass=true | top_k=8 下该综述认识题通过 |
| paper001_q005 | pass=true | pass=false | top_k=8 下答案关键词覆盖下降 |
| paper001_q006 | pass=true | pass=false | top_k=8 下答案关键词覆盖下降 |
| paper004_q001 | pass=true | pass=false | top_k=8 下答案关键词覆盖下降 |
| paper004_q003 | pass=true | pass=false | top_k=8 下答案关键词覆盖下降 |

## 结论

`top_k=8` 对 `paper003_q007` 的检索弱问题有局部改善，但没有让该 case 通过；整体 eval_v2_groups 从 37/50 降到 36/50。单变量实验结果不支持把 heading 默认 `top_k` 从 6 调到 8。
