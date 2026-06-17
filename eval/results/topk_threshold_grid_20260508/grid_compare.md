# TopK + Similarity Threshold Grid Compare

按 `pass_rate`、`relaxed_pass_rate`、`avg_keyword_hit_rate` 降序排序。

| run | top_k | threshold | passed | pass_rate | relaxed_passed | relaxed_pass_rate | avg_hit | avg_relaxed_hit | unanswerable_pass_rate | no_retrieval | answer_mismatch | keyword_too_strict | retrieval_weak | timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| heading_topk6_th030 | 6 | 0.3 | 37 | 0.74 | 45 | 0.9 | 0.4592 | 0.4779 | 1.0 | 0 | 3 | 8 | 2 | 0 |
| heading_topk4_th030 | 4 | 0.3 | 37 | 0.74 | 45 | 0.9 | 0.4508 | 0.4614 | 1.0 | 0 | 1 | 8 | 4 | 0 |
| heading_topk6_th025 | 6 | 0.25 | 37 | 0.74 | 44 | 0.88 | 0.4639 | 0.4826 | 1.0 | 0 | 4 | 7 | 2 | 0 |
| heading_topk4_th035 | 4 | 0.35 | 37 | 0.74 | 44 | 0.88 | 0.4523 | 0.463 | 1.0 | 0 | 2 | 7 | 4 | 0 |
| heading_topk8_th035 | 8 | 0.35 | 37 | 0.74 | 43 | 0.86 | 0.457 | 0.4757 | 1.0 | 0 | 6 | 6 | 1 | 0 |
| heading_topk8_th030 | 8 | 0.3 | 36 | 0.72 | 43 | 0.86 | 0.4347 | 0.4533 | 1.0 | 0 | 6 | 7 | 1 | 0 |
| heading_topk8_th025 | 8 | 0.25 | 35 | 0.7 | 44 | 0.88 | 0.448 | 0.4627 | 1.0 | 0 | 5 | 9 | 1 | 0 |
| heading_topk6_th035 | 6 | 0.35 | 35 | 0.7 | 43 | 0.86 | 0.4521 | 0.4668 | 1.0 | 0 | 4 | 8 | 3 | 0 |
| heading_topk4_th025 | 4 | 0.25 | 30 | 0.6 | 37 | 0.74 | 0.3375 | 0.3482 | 1.0 | 7 | 2 | 7 | 4 | 0 |

## Best

- best_run: `heading_topk6_th030`
- top_k: 6
- similarity_threshold: 0.3
- pass_rate: 0.74
- relaxed_pass_rate: 0.9
