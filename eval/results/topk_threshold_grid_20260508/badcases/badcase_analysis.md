# Grid Badcase Analysis

## 多个组合下都失败

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

## 只在部分组合下通过

- paper001_q004: pass_runs=heading_topk8_th025, heading_topk8_th030; fail_runs=heading_topk4_th025, heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th035
- paper001_q005: pass_runs=heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th035; fail_runs=heading_topk4_th025, heading_topk8_th025, heading_topk8_th030
- paper001_q006: pass_runs=heading_topk4_th025, heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th025, heading_topk8_th035; fail_runs=heading_topk8_th030
- paper001_q008: pass_runs=heading_topk4_th025, heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk8_th025
- paper003_q005: pass_runs=heading_topk4_th025, heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk8_th025, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk6_th030, heading_topk6_th035
- paper003_q008: pass_runs=heading_topk4_th025, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th025, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk4_th030
- paper004_q001: pass_runs=heading_topk6_th025, heading_topk6_th030; fail_runs=heading_topk4_th025, heading_topk4_th030, heading_topk4_th035, heading_topk6_th035, heading_topk8_th025, heading_topk8_th030, heading_topk8_th035
- paper004_q003: pass_runs=heading_topk4_th025, heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th025; fail_runs=heading_topk8_th030, heading_topk8_th035
- paper005_q001: pass_runs=heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk4_th025, heading_topk8_th025
- paper005_q002: pass_runs=heading_topk4_th030, heading_topk4_th035, heading_topk6_th030, heading_topk8_th025, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk4_th025, heading_topk6_th025, heading_topk6_th035
- paper005_q003: pass_runs=heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th025, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk4_th025
- paper005_q004: pass_runs=heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th025, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk4_th025
- paper005_q005: pass_runs=heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th025, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk4_th025
- paper005_q006: pass_runs=heading_topk4_th030, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th025, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk4_th025
- paper005_q007: pass_runs=heading_topk4_th030, heading_topk8_th030, heading_topk8_th035; fail_runs=heading_topk4_th025, heading_topk4_th035, heading_topk6_th025, heading_topk6_th030, heading_topk6_th035, heading_topk8_th025

## threshold 敏感 case

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
- paper005_q002 at top_k=6: [(0.25, False), (0.3, True), (0.35, False)]
- paper005_q003 at top_k=4: [(0.25, False), (0.3, True), (0.35, True)]
- paper005_q004 at top_k=4: [(0.25, False), (0.3, True), (0.35, True)]
- paper005_q005 at top_k=4: [(0.25, False), (0.3, True), (0.35, True)]
- paper005_q006 at top_k=4: [(0.25, False), (0.3, True), (0.35, True)]
- paper005_q007 at top_k=4: [(0.25, False), (0.3, True), (0.35, False)]
- paper005_q007 at top_k=8: [(0.25, False), (0.3, True), (0.35, True)]

## top_k 增大后反而失败

- paper001_q005 at threshold=0.25
- paper001_q005 at threshold=0.3
- paper001_q006 at threshold=0.3
- paper001_q008 at threshold=0.25
- paper004_q001 at threshold=0.25
- paper004_q001 at threshold=0.3
- paper004_q003 at threshold=0.3
- paper004_q003 at threshold=0.35
- paper005_q001 at threshold=0.25

