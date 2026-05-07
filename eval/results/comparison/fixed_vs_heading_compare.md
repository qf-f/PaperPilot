# Fixed Baseline vs Heading Chunk

| 指标 | fixed baseline | heading 新结果 | 变化 |
|---|---:|---:|---:|
| total | 50 | 50 | 0 |
| pass | 32 | 34 | +2 |
| pass_rate | 0.64 | 0.68 | +0.04 |
| avg_keyword_hit_rate | 0.446 | 0.427 | -0.019 |
| no-answer strict pass | 8/10 | 9/10 | +1 |
| no-answer relaxed pass | 10/10 | 9/10 | -1 |

## Heading 按论文结果

| paper | pass | total | pass_rate |
|---|---:|---:|---:|
| paper001 | 6 | 10 | 0.6 |
| paper002 | 7 | 10 | 0.7 |
| paper003 | 8 | 10 | 0.8 |
| paper004 | 5 | 10 | 0.5 |
| paper005 | 8 | 10 | 0.8 |

## Heading 失败类型

| fail_reason | count |
|---|---:|
| likely_eval_keyword_too_strict | 9 |
| retrieval_context_weak | 4 |
| answer_keyword_mismatch | 3 |
