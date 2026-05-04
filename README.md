# PaperPilot
## 项目界面预览

![Uploading b990deeb6697b4733098489785311677.png…]()

<img width="1253" height="713" alt="58fab009a3a355af8517469803c40cdd" src="https://github.com/user-attachments/assets/ed6e6b63-c372-44ce-9a4d-25c3695a75f2" />

<img width="1218" height="684" alt="f619b5715e01d399dd27054f2b3dc353" src="https://github.com/user-attachments/assets/41c5a801-2599-4894-8ef3-9889221463d5" />

PaperPilot is a FastAPI-based academic paper assistant system.

Current MVP scope:

- project creation and query APIs
- document upload metadata persistence
- PostgreSQL + pgvector migration
- Redis + RQ background parsing queue
- PDF/DOCX/TXT/MD parsing
- chunk persistence
- asynchronous chunk embedding
- pgvector retrieval
- minimal LangGraph knowledge-base QA flow
- paper summary agent
- generated output history
- Markdown and Word export

LangGraph planning, translation, review, writing, and web search agents are intentionally reserved for later stages.

## Embedding Dimension

The current database column is `document_chunks.embedding vector(768)`.

This MVP keeps that structure unchanged. Configure a 768-dimension OpenAI-compatible embedding model, for example:

- `nomic-embed-text` through Ollama/OpenAI-compatible `/v1` endpoint
- a bge-base-compatible embedding service

If you use OpenAI `text-embedding-3-small`, its default dimension is 1536. In that case, set `EMBEDDING_DIM=1536` and add a migration to change `document_chunks.embedding` to `vector(1536)`.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-chat-api-key
CHAT_MODEL=gpt-4o-mini

EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_KEY=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768
```

Start infrastructure and run migrations:

```powershell
docker compose up -d
alembic upgrade head
```

Start FastAPI:

```powershell
uvicorn app.main:app --reload
```

Start RQ worker in another terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m app.workers.worker
```

## RAG Evaluation

Prepare a backend-only evaluation project and upload/index local PDFs:

```powershell
python eval/prepare_eval_project.py --api-url http://localhost:8000 --papers-dir paper
```

The prepare script prints `PROJECT_ID` and writes `eval/rag_eval_documents.json`, which maps `paper001`, `paper002`, ... to backend `document_id` values. The evaluator uses this map to restrict each question to its target paper and avoid cross-document retrieval.

Run the multi-paper evaluation:

```powershell
python eval/run_rag_eval.py --project-id <PROJECT_ID> --api-url http://localhost:8000 --dataset eval/rag_eval_dataset_5papers_checked.jsonl --documents-map eval/rag_eval_documents.json --output eval/rag_eval_result_5papers.jsonl --summary-output eval/rag_eval_summary_5papers.json --save-badcases eval/rag_eval_badcases_5papers.jsonl
```

The result JSONL includes retrieved chunk previews, document/page/score lists, target document filters, `error_type`, and `fail_reason`. The badcases JSONL keeps only failed samples for manual review.

`python -m py_compile` and `--help` are only smoke checks. The command above is a RAG integration evaluation, not a normal unit test.

## curl Examples

Create project:

```powershell
curl.exe -X POST "http://localhost:8000/api/projects" `
  -H "Content-Type: application/json" `
  -d "{\"title\":\"RAG 学术论文写作辅助系统\",\"research_direction\":\"AI Agent 与 RAG\",\"keywords\":[\"RAG\",\"LangGraph\",\"论文写作\"]}"
```

Upload document:

```powershell
curl.exe -X POST "http://localhost:8000/api/projects/<project_id>/documents/upload" `
  -F "file=@F:\path\to\paper.pdf"
```

Query parse task:

```powershell
curl.exe "http://localhost:8000/api/tasks/<task_id>"
```

Wait until the document has:

- `parse_status=parsed`
- `index_status=indexed`

Ask the knowledge base:

```powershell
curl.exe -X POST "http://localhost:8000/api/chat" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"00000000-0000-0000-0000-000000000001\",\"query\":\"这篇论文提出的方法是什么？\",\"top_k\":6,\"similarity_threshold\":0.25}"
```

Ask with specific documents:

```powershell
curl.exe -X POST "http://localhost:8000/api/chat" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"query\":\"实验部分使用了哪些数据集？\",\"document_ids\":[\"<document_id>\"],\"top_k\":6}"
```

Generate a standard paper summary:

```powershell
curl.exe -X POST "http://localhost:8000/api/paper/summary" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"document_id\":\"<document_id>\",\"user_id\":\"demo-user\",\"summary_type\":\"standard\",\"project_topic\":\"基于RAG与多Agent编排的论文助手系统设计\"}"
```

List generated outputs:

```powershell
curl.exe -X GET "http://localhost:8000/api/projects/<project_id>/outputs?output_type=paper_summary"
```

Get generated output detail:

```powershell
curl.exe -X GET "http://localhost:8000/api/outputs/<output_id>"
```

Export Word:

```powershell
curl.exe -X POST "http://localhost:8000/api/outputs/<output_id>/export" `
  -H "Content-Type: application/json" `
  -d "{\"export_type\":\"word\"}"
```

Export Markdown:

```powershell
curl.exe -X POST "http://localhost:8000/api/outputs/<output_id>/export" `
  -H "Content-Type: application/json" `
  -d "{\"export_type\":\"markdown\"}"
```

## pgvector Retrieval SQL

The retrieval service uses cosine distance. pgvector `<=>` returns distance, not similarity.

```sql
SELECT
  dc.id,
  dc.content,
  dc.chunk_index,
  dc.page_number,
  dc.section_title,
  d.original_filename,
  1 - (dc.embedding <=> :query_embedding) AS score
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE dc.project_id = :project_id
  AND dc.embedding IS NOT NULL
ORDER BY dc.embedding <=> :query_embedding
LIMIT :top_k;
```

With document filtering:

```sql
AND dc.document_id = ANY(:document_ids)
```

## Troubleshooting

- `Embedding dimension mismatch`: your embedding model output dimension does not match `EMBEDDING_DIM` and `vector(768)`.
- `Document is not indexed yet`: wait for the RQ worker to finish `embed_document_chunks`.
- `OPENAI_API_KEY is not configured`: set chat API credentials in `.env`.
- `EMBEDDING_API_KEY is not configured`: set embedding API credentials in `.env`; Ollama-compatible endpoints can use `ollama`.
- Empty retrieval result: lower `RAG_SIMILARITY_THRESHOLD`, specify `document_ids`, or confirm chunks have non-null embeddings.
- `Document has no chunks`: re-run parsing or re-upload the document.
- Summary says `原文中未找到明确依据`: the relevant section was not present in the parsed chunks, or the parser did not extract it cleanly.
- Word export only supports MVP Markdown syntax: headings, paragraphs, bullet/numbered lists, simple tables, and basic `**bold**`.

## 第四阶段：联网文献检索与参考文献管理

第四阶段提供最小闭环：

- 基于项目或用户 query 检索相关论文
- arXiv 检索 AI/CS 预印本文献
- Crossref 补充 DOI、作者、年份、期刊/会议等元数据
- Semantic Scholar 可选接入，未配置 API Key 时使用公开接口能力，失败时降级
- 将检索结果保存到项目文献库
- 从上传论文 chunks 中识别 References / 参考文献区域
- 解析、去重、格式化项目参考文献
- 基于已保存文献推荐扩展引用
- 基于已保存文献生成文献综述素材

### 环境变量

```env
ARXIV_BASE_URL=http://export.arxiv.org/api/query
CROSSREF_BASE_URL=https://api.crossref.org/works
SEMANTIC_SCHOLAR_BASE_URL=https://api.semanticscholar.org/graph/v1
SEMANTIC_SCHOLAR_API_KEY=
WEB_SEARCH_PROVIDER=none
WEB_SEARCH_API_KEY=
LITERATURE_SEARCH_MAX_RESULTS=10
LITERATURE_SEARCH_TIMEOUT_SECONDS=20
LITERATURE_SEARCH_RECENT_YEARS=3

REFERENCE_EXTRACT_MAX_CHARS=50000
REFERENCE_MATCH_THRESHOLD=0.82
REFERENCE_DEDUP_THRESHOLD=0.9
LITERATURE_REVIEW_MAX_ITEMS=20
```

arXiv 和 Crossref 不需要 API Key。Semantic Scholar API Key 可选；未配置或请求失败时，系统会记录降级信息，不会伪造文献。

### 联网检索相关论文

```powershell
curl.exe -X POST "http://localhost:8000/api/literature/search" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"query\":\"multi-agent reinforcement learning credit assignment\",\"search_mode\":\"recent\",\"max_results\":10,\"generate_review_material\":true}"
```

### 查看项目文献库

```powershell
curl.exe -X GET "http://localhost:8000/api/projects/<project_id>/literatures?limit=20"
```

### 查看文献详情

```powershell
curl.exe -X GET "http://localhost:8000/api/literatures/<literature_id>"
```

### 从上传论文抽取参考文献

```powershell
curl.exe -X POST "http://localhost:8000/api/references/extract" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"document_id\":\"<document_id>\",\"user_id\":\"demo-user\"}"
```

### 查看项目参考文献

```powershell
curl.exe -X GET "http://localhost:8000/api/projects/<project_id>/references"
```

### 格式化 GB/T 7714

```powershell
curl.exe -X POST "http://localhost:8000/api/references/format" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"style\":\"gb_t_7714\"}"
```

支持 `gb_t_7714`、`ieee`、`apa`、`bibtex` 四种简化格式。

### 推荐扩展参考文献

```powershell
curl.exe -X POST "http://localhost:8000/api/references/recommend" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\"}"
```

### 生成综述素材

```powershell
curl.exe -X POST "http://localhost:8000/api/literature/review-material" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"topic\":\"基于RAG与多Agent编排的论文助手系统\"}"
```

## 第五阶段：论文规划与章节写作

第五阶段提供最小闭环：

- 根据题目、项目上下文、论文总结、文献库和参考文献生成论文规划
- 输出题目可行性、研究问题、研究目标、创新点、技术路线、实验方案和论文大纲
- 根据规划和项目上下文生成章节草稿
- 草稿保存到 `generated_outputs`，可复用 `/api/outputs/{output_id}/export` 导出 Markdown 或 Word

### 生成论文规划

```powershell
curl.exe -X POST "http://localhost:8000/api/planning/topic" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"topic\":\"基于RAG与多Agent编排的论文助手系统设计与实现\",\"paper_type\":\"thesis\",\"research_direction\":\"RAG, 多Agent, 论文写作辅助\",\"requirements\":\"希望适合硕士毕业论文，偏工程系统实现，但要有一定创新点\"}"
```

### 查询项目规划

```powershell
curl.exe -X GET "http://localhost:8000/api/projects/<project_id>/plans"
```

### 查询规划详情

```powershell
curl.exe -X GET "http://localhost:8000/api/plans/<output_id>"
```

### 生成绪论草稿

```powershell
curl.exe -X POST "http://localhost:8000/api/writing/section" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"section_type\":\"introduction\",\"section_title\":\"绪论\",\"topic\":\"基于RAG与多Agent编排的论文助手系统设计与实现\",\"plan_output_id\":\"<plan_output_id>\",\"requirements\":\"生成硕士论文风格的绪论，包括研究背景、研究意义、国内外研究现状和本文工作\"}"
```

### 生成相关工作草稿

```powershell
curl.exe -X POST "http://localhost:8000/api/writing/section" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"section_type\":\"related_work\",\"section_title\":\"相关工作\",\"plan_output_id\":\"<plan_output_id>\",\"requirements\":\"根据已检索文献，按方法类别组织相关工作\"}"
```

### 生成实验设计章节草稿

```powershell
curl.exe -X POST "http://localhost:8000/api/writing/section" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"section_type\":\"experiment\",\"section_title\":\"实验设计\",\"plan_output_id\":\"<plan_output_id>\",\"requirements\":\"只写实验设计，不编造实验结果\"}"
```

### 查询章节草稿

```powershell
curl.exe -X GET "http://localhost:8000/api/projects/<project_id>/drafts"
```

### 查询草稿详情

```powershell
curl.exe -X GET "http://localhost:8000/api/drafts/<draft_output_id>"
```

### 导出章节草稿 Word

```powershell
curl.exe -X POST "http://localhost:8000/api/outputs/<draft_output_id>/export" `
  -H "Content-Type: application/json" `
  -d "{\"export_type\":\"word\"}"
```

## 第六阶段：论文质量审查与引用一致性检查

第六阶段提供最小闭环：

- 审查 `generated_outputs` 中的论文规划、章节草稿、综述素材或论文总结
- 审查上传论文初稿，基于 `document_chunks` 拼接可审查文本
- 检查结构一致性、引用真实性、实验支撑、结论夸大、AI 味和格式风险
- 审查报告保存为 `generated_outputs.output_type=review_report`
- 审查报告可复用 `/api/outputs/{output_id}/export` 导出 Markdown 或 Word

### 审查章节草稿

```powershell
curl.exe -X POST "http://localhost:8000/api/review" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"target_output_id\":\"<draft_output_id>\",\"review_type\":\"full\",\"requirements\":\"重点检查引用真实性、实验结论是否夸大、AI味表达\"}"
```

### 审查论文规划

```powershell
curl.exe -X POST "http://localhost:8000/api/review" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"target_output_id\":\"<plan_output_id>\",\"review_type\":\"structure\",\"requirements\":\"检查创新点是否和实验方案对应\"}"
```

### 审查上传论文初稿

```powershell
curl.exe -X POST "http://localhost:8000/api/review" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"document_id\":\"<document_id>\",\"review_type\":\"full\"}"
```

### 单独检查引用

```powershell
curl.exe -X POST "http://localhost:8000/api/review/citations/check" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"text\":\"相关工作中提到该方法能够提升检索准确性 [1]，但另一处引用不存在 [99]。\",\"section_type\":\"related_work\"}"
```

### 查询项目审查报告

```powershell
curl.exe -X GET "http://localhost:8000/api/projects/<project_id>/reviews"
```

### 查询审查报告详情

```powershell
curl.exe -X GET "http://localhost:8000/api/reviews/<review_output_id>"
```

### 导出审查报告 Word

```powershell
curl.exe -X POST "http://localhost:8000/api/outputs/<review_output_id>/export" `
  -H "Content-Type: application/json" `
  -d "{\"export_type\":\"word\"}"
```

## 第七阶段：英文论文翻译与术语表一致性管理

第七阶段提供最小闭环：

- 选择已解析的英文论文文档进行全文、页码范围或 chunk 范围翻译
- 支持 `faithful` 忠实直译和 `polished` 学术润色两种模式
- 支持 `bilingual` 中英对照和 `chinese_only` 纯中文译文
- 自动抽取并持久化项目级术语表 `terminologies`
- 翻译时优先使用项目术语表，并生成术语一致性 warnings
- 翻译结果保存为 `generated_outputs.output_type=translation`
- 可复用 `/api/outputs/{output_id}/export` 导出 Markdown 或 Word

### 翻译整篇论文，中英对照

```powershell
curl.exe -X POST "http://localhost:8000/api/translation/document" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"document_id\":\"<document_id>\",\"user_id\":\"demo-user\",\"translation_mode\":\"faithful\",\"output_style\":\"bilingual\",\"range_type\":\"full\",\"requirements\":\"保持学术表达，保留公式、图表编号和引用编号\"}"
```

### 翻译指定页码范围

```powershell
curl.exe -X POST "http://localhost:8000/api/translation/document" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"document_id\":\"<document_id>\",\"user_id\":\"demo-user\",\"translation_mode\":\"polished\",\"output_style\":\"chinese_only\",\"range_type\":\"pages\",\"page_from\":2,\"page_to\":5}"
```

### 翻译指定 chunk 范围

```powershell
curl.exe -X POST "http://localhost:8000/api/translation/document" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"document_id\":\"<document_id>\",\"user_id\":\"demo-user\",\"translation_mode\":\"faithful\",\"output_style\":\"bilingual\",\"range_type\":\"chunks\",\"chunk_from\":0,\"chunk_to\":10}"
```

### 查询项目翻译历史

```powershell
curl.exe -X GET "http://localhost:8000/api/projects/<project_id>/translations"
```

### 查询翻译详情

```powershell
curl.exe -X GET "http://localhost:8000/api/translations/<output_id>"
```

### 查询项目术语表

```powershell
curl.exe -X GET "http://localhost:8000/api/projects/<project_id>/terminologies"
```

### 手动新增术语

```powershell
curl.exe -X POST "http://localhost:8000/api/projects/<project_id>/terminologies" `
  -H "Content-Type: application/json" `
  -d "{\"source_term\":\"retrieval-augmented generation\",\"target_term\":\"检索增强生成\",\"category\":\"method\",\"explanation\":\"一种将检索结果引入生成模型的技术\"}"
```

### 导出翻译结果 Word

```powershell
curl.exe -X POST "http://localhost:8000/api/outputs/<translation_output_id>/export" `
  -H "Content-Type: application/json" `
  -d "{\"export_type\":\"word\"}"
```

## 第八阶段：系统工程化与可观测性优化

第八阶段把 Agent 执行从“直接调用 graph”升级为可追踪的 `AgentRun`：

- `agent_runs` 记录 run 状态、token usage 和估算成本
- `tool_traces` 记录节点级输入、输出、耗时、状态和错误信息
- `AgentRunner` 统一创建 run、执行 graph、保存 trace、处理异常和 `partial_success`
- LangGraph 节点统一通过 `trace_node` 包装，支持最多 2 次节点级重试和指数退避
- `planning`、`writing`、`review`、`translation` 支持 `mode=sync|async`
- 异步模式通过 RQ 入队，接口立即返回 `run_id`
- 新增 `/api/runs/{run_id}` 查询 run 详情和节点 trace
- `/api/projects/{project_id}/outputs` 支持分页、排序和 output_type/document_id 过滤
- `LLMService` 增加 Redis 滑动窗口限流，默认每 user_id 每分钟 20 次 LLM 调用

### 环境变量

```env
LLM_RATE_LIMIT_ENABLED=true
LLM_RATE_LIMIT_PER_MINUTE=20
LLM_PROMPT_COST_PER_1K=0
LLM_COMPLETION_COST_PER_1K=0
AGENT_TRACE_DEBUG=false
```

`AGENT_TRACE_DEBUG=false` 时，trace 中的大文本会自动裁剪，避免把全文、译文或 prompt 过量写入数据库。

### 执行迁移

```powershell
alembic upgrade head
```

新增迁移会增强：

- `agent_runs.prompt_tokens`
- `agent_runs.completion_tokens`
- `agent_runs.total_tokens`
- `agent_runs.estimated_cost`
- `tool_traces.node_name`

### 异步生成论文规划

```powershell
curl.exe -X POST "http://localhost:8000/api/planning/topic" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"topic\":\"基于RAG与多Agent编排的论文助手系统设计与实现\",\"paper_type\":\"thesis\",\"mode\":\"async\"}"
```

响应：

```json
{
  "run_id": "<run_id>",
  "status": "queued",
  "message": "Agent run has been queued"
}
```

### 查询 Agent Run

```powershell
curl.exe -X GET "http://localhost:8000/api/runs/<run_id>"
```

返回内容包含：

- run 状态：`queued`、`running`、`success`、`partial_success`、`failed`
- 每个节点的 `node_name`
- 节点输入/输出裁剪预览
- 节点耗时
- token usage
- total_latency_ms

### 异步章节写作

```powershell
curl.exe -X POST "http://localhost:8000/api/writing/section" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"section_type\":\"introduction\",\"section_title\":\"绪论\",\"mode\":\"async\"}"
```

### 异步审查

```powershell
curl.exe -X POST "http://localhost:8000/api/review" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"user_id\":\"demo-user\",\"target_output_id\":\"<draft_output_id>\",\"review_type\":\"full\",\"mode\":\"async\"}"
```

### 异步翻译

```powershell
curl.exe -X POST "http://localhost:8000/api/translation/document" `
  -H "Content-Type: application/json" `
  -d "{\"project_id\":\"<project_id>\",\"document_id\":\"<document_id>\",\"user_id\":\"demo-user\",\"translation_mode\":\"faithful\",\"output_style\":\"bilingual\",\"range_type\":\"full\",\"mode\":\"async\"}"
```

### 分页查询项目输出

```powershell
curl.exe -X GET "http://localhost:8000/api/projects/<project_id>/outputs?output_type=translation&page=1&page_size=20&sort_order=desc"
```

### 启动异步 worker

```powershell
python -m app.workers.worker
```

异步接口只负责入队，真正执行依赖 Redis 和 RQ worker。若 run 长时间停留在 `queued`，优先检查 worker 是否启动。
