# RAG Eval Baseline - Fixed Chunk

策略：fixed chunk baseline
状态：优化前评测结果
是否代表 heading 策略：否

## 指标

- total: 50
- pass: 32
- pass_rate: 0.64
- avg_keyword_hit_rate: 0.446
- no-answer: 10
- no-answer strict pass: 8/10
- no-answer relaxed pass: 10/10

## 说明

该结果文件早于 parser/chunker 优化提交，只能作为 fixed baseline。
heading-aware chunk 策略需要重新解析、重新 chunk、重新 embedding 后再评测。
