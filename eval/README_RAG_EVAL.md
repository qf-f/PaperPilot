# PaperPilot RAG Evaluation

本目录包含 PaperPilot 的 RAG 集成评测脚本、数据集和结果文件。该评测不是普通单元测试，而是会调用当前项目的 RAG 问答链路，用于观察检索命中、回答正确性、引用证据和无答案拒答能力。

## 关键文件

```text
eval/run_rag_eval.py
eval/rag_eval_dataset_5papers_checked.jsonl
eval/rag_eval_documents.json
eval/rag_eval_result_5papers.jsonl
eval/rag_eval_summary_5papers.json
eval/rag_eval_badcases_5papers.jsonl
```

## 前置条件

1. 启动 PostgreSQL、Redis 和后端服务。
2. 启动 RQ worker，确保论文已解析、切分、embedding 并完成索引。
3. 使用 `eval/prepare_eval_project.py` 上传论文并生成 `eval/rag_eval_documents.json`。

示例：

```powershell
python eval/prepare_eval_project.py --api-url http://localhost:8000 --papers-dir paper
```

## 运行评测

推荐命令：

```powershell
python eval/run_rag_eval.py --project-id 084b24a2-a7a5-4bad-832e-5cb1d2286494 --api-url http://localhost:8000 --dataset eval/rag_eval_dataset_5papers_checked.jsonl --documents-map eval/rag_eval_documents.json --output eval/rag_eval_result_5papers.jsonl --summary-output eval/rag_eval_summary_5papers.json --save-badcases eval/rag_eval_badcases_5papers.jsonl
```

最小命令：

```powershell
python eval/run_rag_eval.py --project-id <PROJECT_ID> --api-url http://localhost:8000
```

## 参数说明

- `--project-id`：PaperPilot 项目 ID。
- `--api-url`：FastAPI 后端地址，默认常用 `http://localhost:8000`。
- `--dataset`：JSONL 评测数据集路径。
- `--documents-map`：`paper_id` 到 `document_id` 的映射文件，用于多文档评测过滤。
- `--output`：逐题评测结果 JSONL。
- `--summary-output`：整体统计 JSON。
- `--save-badcases`：只保存 strict `pass=false` 样本的 JSONL 文件。
- `--top-k`：可选，覆盖后端默认召回数量。
- `--similarity-threshold`：可选，覆盖后端默认相似度阈值。
- `--min-keyword-hit-rate`：可选，strict 关键词命中通过阈值，默认 `0.5`。

## 输出结果含义

逐题结果主要字段：

- `answer`：模型回答。
- `keyword_hit_count`：strict 关键词命中数量。
- `keyword_hit_rate`：strict 关键词命中率。
- `pass` / `strict_pass`：strict 是否通过。
- `relaxed_keyword_hit_rate`：归一化、同义词组和公式近似后的关键词命中率。
- `relaxed_pass`：辅助判断结果，仅用于人工参考。
- `retrieved_chunks`：召回片段预览，包括 `text_preview`、`document_id`、`file_name`、`page`、`score` 和 `chunk_id`。
- `target_document_id` / `target_file_name`：当前样本应该检索的目标论文。
- `document_filter`：是否启用了文档级过滤。
- `fail_reason`：失败原因，如 `answer_keyword_mismatch`、`likely_eval_keyword_too_strict`、`retrieval_context_weak`、`wrong_document`、`no_retrieval`、`timeout`。

## 如何用于优化前后对比

1. 固定同一份数据集和同一组 PDF。
2. 每次修改 RAG 链路后重新运行相同命令。
3. 对比 `rag_eval_summary_5papers.json` 中的：
   - `strict_pass_rate`
   - `relaxed_pass_rate`
   - `avg_keyword_hit_rate`
   - `wrong_document_count`
   - `retrieval_context_weak_count`
   - `answer_keyword_mismatch_count`
   - `likely_eval_keyword_too_strict_count`
4. 重点查看 `rag_eval_badcases_5papers.jsonl`，区分是评测关键词设计问题，还是检索/生成链路问题。

## 当前 baseline 结论

当前基础评测闭环已经跑通，可以作为优化前 baseline。后续优化建议优先围绕 heading-aware chunking、语义切分、检索参数调优、Milvus 接入、引用证据增强和无答案拒答稳定性展开。
