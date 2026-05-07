# RAG Eval - Heading Chunk

策略：heading-aware chunk
状态：已重新解析、重新 embedding、重新评测

输出文件：

- rag_eval_result_heading.jsonl
- rag_eval_summary_heading.json
- rag_eval_badcases_heading.jsonl
- rag_eval_documents.json

## 指标

- total: 50
- pass: 34
- pass_rate: 0.68
- avg_keyword_hit_rate: 0.427
- no-answer: 10
- no-answer strict pass: 9/10
- no-answer relaxed pass: 9/10
- badcases: 16

## 入库确认

- project_id: 1a636e72-447b-411d-9f44-a401d1e23d48
- CHUNK_STRATEGY: heading
- total chunks: 425
- embedded chunks: 425
- chunk_strategy metadata: heading
