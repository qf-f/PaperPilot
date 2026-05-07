from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.models.document import Document  # noqa: E402
from app.db.models.document_chunk import DocumentChunk  # noqa: E402
from app.db.models.project import PaperProject  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402


DEFAULT_CASE_IDS = ["paper003_q007", "paper004_q002", "paper004_q008"]
DEFAULT_PARAMETER_SETS = [
    {"top_k": 6, "similarity_threshold": 0.25},
    {"top_k": 8, "similarity_threshold": 0.25},
    {"top_k": 10, "similarity_threshold": 0.25},
    {"top_k": 10, "similarity_threshold": 0.20},
    {"top_k": 12, "similarity_threshold": 0.20},
]
DEFAULT_DATASET_PATH = REPO_ROOT / "eval" / "rag_eval_dataset_5papers_checked.jsonl"
DEFAULT_DOCUMENTS_PATH = REPO_ROOT / "eval" / "rag_eval_documents.json"
DEFAULT_RESULT_PATH = REPO_ROOT / "eval" / "results" / "heading_20260504" / "rag_eval_result_heading_eval_v2.jsonl"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "eval" / "results" / "heading_20260504" / "retrieval_debug_cases.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "eval" / "results" / "heading_20260504" / "retrieval_debug_cases.md"

INITIAL_ASSESSMENTS = {
    "paper003_q007": "真实实验结果检索问题",
    "paper004_q002": "prompt / eval keyword / retrieval 组织混合问题",
    "paper004_q008": "结论/建议类检索问题",
}

FOCUS_KEYWORDS = {
    "paper003_q007": ["5.24%", "68.25 秒", "准确率", "运行时间", "平均准确率", "基准模型"],
    "paper004_q002": ["网络架构", "监督范式", "数据集", "评估指标", "定性分析", "定量分析", "运行效率"],
    "paper004_q008": [
        "conclusion",
        "future work",
        "challenge",
        "suggestion",
        "后续研究",
        "算法局限性",
        "研究建议",
        "不同场景",
    ],
}

CRITICAL_KEYWORDS = {
    "paper003_q007": ["5.24%", "68.25 秒"],
    "paper004_q002": ["网络架构", "监督范式", "数据集", "评估指标", "定性分析", "定量分析", "运行效率"],
    "paper004_q008": FOCUS_KEYWORDS["paper004_q008"],
}

ALLOWED_NEXT_STEPS = [
    "提高 top_k",
    "降低 similarity_threshold",
    "metadata 加权",
    "rerank",
    "query rewrite",
    "hybrid search",
    "prompt 约束",
    "eval keyword 调整",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Debug retrieval chunks for selected RAG eval cases without calling chat or LLM answer generation.",
    )
    parser.add_argument("--project-id", required=True, help="PaperPilot project UUID.")
    parser.add_argument("--cases", nargs="+", default=DEFAULT_CASE_IDS, help="One or more eval case IDs.")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="Path for JSON debug output.")
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD), help="Path for Markdown debug output.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Eval dataset JSONL path.")
    parser.add_argument("--documents", default=str(DEFAULT_DOCUMENTS_PATH), help="Eval document map JSON path.")
    parser.add_argument("--result-jsonl", default=str(DEFAULT_RESULT_PATH), help="Heading eval v2 result JSONL path.")
    parser.add_argument(
        "--no-document-filter",
        action="store_true",
        help="Do not restrict retrieval to the case target document. Defaults to eval document filtering.",
    )
    return parser.parse_args()


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number} in {path}: {exc}") from exc
    return rows


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def index_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = str(row.get("id") or row.get("case_id") or "")
        if row_id:
            indexed[row_id] = row
    return indexed


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def keyword_matches(keyword: Any, content: str) -> bool:
    keyword_text = str(keyword or "").strip()
    if not keyword_text:
        return False
    if contains_cjk(keyword_text):
        return keyword_text in content
    return keyword_text.casefold() in content.casefold()


def matched_keywords(content: str, keywords: list[Any]) -> list[str]:
    return [str(keyword) for keyword in keywords if keyword_matches(keyword, content)]


def metadata_value(metadata: dict[str, Any], key: str) -> Any:
    return metadata[key] if key in metadata else None


def chunk_to_debug_row(
    *,
    rank: int,
    chunk: DocumentChunk,
    distance: float,
    similarity: float,
    expected_keywords: list[Any],
) -> dict[str, Any]:
    metadata = chunk.chunk_metadata if isinstance(chunk.chunk_metadata, dict) else {}
    content = chunk.content or ""
    hits = matched_keywords(content, expected_keywords)
    page_number = chunk.page_number if chunk.page_number is not None else metadata_value(metadata, "page_number")
    section_title = chunk.section_title or metadata_value(metadata, "section_title")

    return {
        "rank": rank,
        "document_id": str(chunk.document_id),
        "chunk_id": str(chunk.id),
        "distance": round(float(distance), 6),
        "similarity": round(float(similarity), 6),
        "page_number": page_number,
        "section_title": section_title if section_title not in ("", None) else None,
        "section_path": metadata_value(metadata, "section_path"),
        "is_reference_section": metadata_value(metadata, "is_reference_section"),
        "content_preview": content[:500],
        "keyword_hit": bool(hits),
        "matched_keywords": hits,
    }


def retrieve_chunks(
    db: Session,
    *,
    project_id: UUID,
    query_embedding: list[float],
    top_k: int,
    similarity_threshold: float,
    document_id: str | None,
    expected_keywords: list[Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    raw_distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    distance_expr = raw_distance.label("distance")
    similarity_expr = (1 - raw_distance).label("similarity")

    stmt = (
        select(DocumentChunk, distance_expr, similarity_expr)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(
            DocumentChunk.project_id == project_id,
            Document.parse_status == "parsed",
            Document.index_status == "indexed",
            DocumentChunk.embedding.is_not(None),
            raw_distance <= (1 - similarity_threshold),
        )
        .order_by(raw_distance.asc())
        .limit(top_k)
    )

    if document_id:
        stmt = stmt.where(DocumentChunk.document_id == UUID(document_id))

    rows = db.execute(stmt).all()
    chunks: list[dict[str, Any]] = []
    full_contents: list[str] = []
    for index, (chunk, distance, similarity) in enumerate(rows, start=1):
        chunks.append(
            chunk_to_debug_row(
                rank=index,
                chunk=chunk,
                distance=float(distance),
                similarity=float(similarity or 0.0),
                expected_keywords=expected_keywords,
            )
        )
        full_contents.append(chunk.content or "")
    return chunks, full_contents


def run_keyword_summary(full_contents: list[str], keywords: list[str]) -> dict[str, Any]:
    combined_text = "\n".join(full_contents)
    hits = matched_keywords(combined_text, keywords)
    first_rank = None
    for index, content in enumerate(full_contents, start=1):
        if matched_keywords(content, keywords):
            first_rank = index
            break
    return {
        "matched_keywords": hits,
        "hit_count": len(hits),
        "first_hit_rank": first_rank,
    }


def recall_label(matched: list[str], critical_keywords: list[str]) -> str:
    if not critical_keywords:
        return "无判断关键词"
    matched_set = set(matched)
    critical_set = set(critical_keywords)
    if critical_set.issubset(matched_set):
        return "是"
    if matched_set & critical_set:
        return "部分"
    return "否"


def params_key(run: dict[str, Any]) -> tuple[int, float]:
    params = run["params"]
    return int(params["top_k"]), float(params["similarity_threshold"])


def build_case_conclusion(case_payload: dict[str, Any]) -> dict[str, str]:
    case_id = case_payload["case_id"]
    runs = {params_key(run): run for run in case_payload.get("runs", [])}
    focus_keywords = FOCUS_KEYWORDS.get(case_id, list(case_payload.get("expected_keywords") or []))
    critical_keywords = CRITICAL_KEYWORDS.get(case_id, focus_keywords)
    baseline = runs.get((6, 0.25))
    top_k_candidates = [runs[key] for key in [(8, 0.25), (10, 0.25)] if key in runs]
    threshold_pair = (runs.get((10, 0.25)), runs.get((10, 0.20)))
    all_runs = list(runs.values())

    if not baseline:
        return {
            "case_id": case_id,
            "问题类型": INITIAL_ASSESSMENTS.get(case_id, "未分类"),
            "baseline 是否召回关键片段": "无法判断",
            "提高 top_k 是否改善": "无法判断",
            "降低 threshold 是否改善": "无法判断",
            "主要瓶颈": "诊断未完成",
            "下一步建议": "query rewrite",
        }

    baseline_focus = baseline["focus_keyword_summary"]["matched_keywords"]
    baseline_label = recall_label(baseline_focus, critical_keywords)
    baseline_count = len(set(baseline_focus))
    best_top_k_count = max(
        [len(set(run["focus_keyword_summary"]["matched_keywords"])) for run in top_k_candidates] or [baseline_count]
    )
    top_k_improved = best_top_k_count > baseline_count

    threshold_improved = False
    if threshold_pair[0] and threshold_pair[1]:
        before = len(set(threshold_pair[0]["focus_keyword_summary"]["matched_keywords"]))
        after = len(set(threshold_pair[1]["focus_keyword_summary"]["matched_keywords"]))
        threshold_improved = after > before

    best_any_count = max(
        [len(set(run["focus_keyword_summary"]["matched_keywords"])) for run in all_runs] or [baseline_count]
    )
    first_focus_rank = min(
        [
            int(run["focus_keyword_summary"]["first_hit_rank"])
            for run in all_runs
            if run["focus_keyword_summary"]["first_hit_rank"] is not None
        ],
        default=None,
    )

    if top_k_improved:
        bottleneck = "top_k 偏小，相关片段在后排"
        next_step = "提高 top_k"
    elif threshold_improved:
        bottleneck = "similarity_threshold 偏高"
        next_step = "降低 similarity_threshold"
    elif baseline_label in {"是", "部分"}:
        if case_id == "paper004_q002":
            bottleneck = "检索已有概览片段，回答或 eval keyword 更可能是瓶颈"
            next_step = "eval keyword 调整"
        elif case_id == "paper004_q008":
            bottleneck = "结论挑战片段已召回，中文 eval keyword 与原文表述映射更可能是瓶颈"
            next_step = "eval keyword 调整"
        elif first_focus_rank and first_focus_rank > 3:
            bottleneck = "关键片段已召回但排序不够靠前"
            next_step = "rerank"
        else:
            bottleneck = "关键片段已召回，生成约束更可能是瓶颈"
            next_step = "prompt 约束"
    elif best_any_count > 0:
        bottleneck = "关键片段弱召回，排序和组织不足"
        next_step = "rerank"
    else:
        bottleneck = "语义召回未覆盖关键片段"
        next_step = "query rewrite"

    return {
        "case_id": case_id,
        "问题类型": INITIAL_ASSESSMENTS.get(case_id, "未分类"),
        "baseline 是否召回关键片段": baseline_label,
        "提高 top_k 是否改善": "是" if top_k_improved else "否",
        "降低 threshold 是否改善": "是" if threshold_improved else "否",
        "主要瓶颈": bottleneck,
        "下一步建议": next_step,
    }


def get_target_document(documents_map: dict[str, Any], paper_id: str) -> tuple[str | None, str | None]:
    documents = documents_map.get("documents")
    if not isinstance(documents, dict):
        return None, None
    paper_entry = documents.get(paper_id)
    if not isinstance(paper_entry, dict):
        return None, None
    document_id = paper_entry.get("document_id")
    file_name = paper_entry.get("file_name")
    return str(document_id) if document_id else None, str(file_name) if file_name else None


def diagnose_case(
    db: Session,
    embedding_service: EmbeddingService,
    *,
    project_id: UUID,
    case_id: str,
    sample: dict[str, Any],
    result_row: dict[str, Any] | None,
    documents_map: dict[str, Any],
    use_document_filter: bool,
) -> dict[str, Any]:
    paper_id = str(sample.get("paper_id") or "")
    target_document_id, target_file_name = get_target_document(documents_map, paper_id)
    active_document_id = target_document_id if use_document_filter else None
    question = str(sample.get("question") or "")
    expected_keywords = sample.get("expected_keywords") if isinstance(sample.get("expected_keywords"), list) else []
    focus_keywords = FOCUS_KEYWORDS.get(case_id, [str(keyword) for keyword in expected_keywords])

    case_payload: dict[str, Any] = {
        "case_id": case_id,
        "paper_id": paper_id,
        "paper_title": sample.get("paper_title"),
        "question": question,
        "expected_keywords": expected_keywords,
        "focus_keywords": focus_keywords,
        "fail_reason": (result_row or {}).get("fail_reason"),
        "initial_assessment": INITIAL_ASSESSMENTS.get(case_id, "未分类"),
        "target_document_id": target_document_id,
        "target_file_name": target_file_name,
        "used_document_filter": bool(active_document_id),
        "runs": [],
    }

    try:
        query_embedding = embedding_service.embed_text(question)
        case_payload["query_embedding_dimension"] = len(query_embedding)
    except Exception as exc:  # noqa: BLE001 - diagnostic script should report environment blockers.
        case_payload["error"] = {
            "stage": "embedding",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        return case_payload

    for params in DEFAULT_PARAMETER_SETS:
        run_payload: dict[str, Any] = {"params": params}
        try:
            chunks, full_contents = retrieve_chunks(
                db,
                project_id=project_id,
                query_embedding=query_embedding,
                top_k=int(params["top_k"]),
                similarity_threshold=float(params["similarity_threshold"]),
                document_id=active_document_id,
                expected_keywords=expected_keywords,
            )
            run_payload["retrieved_count"] = len(chunks)
            run_payload["expected_keyword_summary"] = run_keyword_summary(
                full_contents,
                [str(keyword) for keyword in expected_keywords],
            )
            run_payload["focus_keyword_summary"] = run_keyword_summary(full_contents, focus_keywords)
            run_payload["chunks"] = chunks
        except Exception as exc:  # noqa: BLE001 - keep later cases diagnosable.
            run_payload["error"] = {
                "stage": "retrieval",
                "type": type(exc).__name__,
                "message": str(exc),
            }
        case_payload["runs"].append(run_payload)

    return case_payload


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    dataset_path = resolve_path(args.dataset)
    documents_path = resolve_path(args.documents)
    result_path = resolve_path(args.result_jsonl)

    dataset_by_id = index_by_id(iter_jsonl(dataset_path))
    result_by_id = index_by_id(iter_jsonl(result_path))
    documents_map = load_json(documents_path)
    project_id = UUID(str(args.project_id))

    payload: dict[str, Any] = {
        "title": "Retrieval Debug for Heading Eval V2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": str(project_id),
        "dataset_path": str(dataset_path.relative_to(REPO_ROOT)),
        "result_path": str(result_path.relative_to(REPO_ROOT)),
        "documents_path": str(documents_path.relative_to(REPO_ROOT)),
        "parameter_sets": DEFAULT_PARAMETER_SETS,
        "document_filter": not args.no_document_filter,
        "cases": [],
        "errors": [],
    }

    missing_cases = [case_id for case_id in args.cases if case_id not in dataset_by_id]
    if missing_cases:
        raise ValueError(f"Case ID not found in dataset: {', '.join(missing_cases)}")

    try:
        embedding_service = EmbeddingService()
    except Exception as exc:  # noqa: BLE001
        payload["errors"].append(
            {
                "stage": "embedding_service_init",
                "type": type(exc).__name__,
                "message": str(exc),
            }
        )
        for case_id in args.cases:
            sample = dataset_by_id[case_id]
            case_payload = {
                "case_id": case_id,
                "paper_id": sample.get("paper_id"),
                "paper_title": sample.get("paper_title"),
                "question": sample.get("question"),
                "expected_keywords": sample.get("expected_keywords", []),
                "focus_keywords": FOCUS_KEYWORDS.get(case_id, sample.get("expected_keywords", [])),
                "fail_reason": result_by_id.get(case_id, {}).get("fail_reason"),
                "initial_assessment": INITIAL_ASSESSMENTS.get(case_id, "未分类"),
                "runs": [],
                "error": payload["errors"][-1],
            }
            payload["cases"].append(case_payload)
        payload["conclusion_rows"] = [build_case_conclusion(case_payload) for case_payload in payload["cases"]]
        return payload

    with SessionLocal() as db:
        project = db.get(PaperProject, project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")

        for case_id in args.cases:
            case_payload = diagnose_case(
                db,
                embedding_service,
                project_id=project_id,
                case_id=case_id,
                sample=dataset_by_id[case_id],
                result_row=result_by_id.get(case_id),
                documents_map=documents_map,
                use_document_filter=not args.no_document_filter,
            )
            if case_payload.get("error"):
                payload["errors"].append({"case_id": case_id, **case_payload["error"]})
            for run in case_payload.get("runs", []):
                if run.get("error"):
                    payload["errors"].append({"case_id": case_id, "params": run.get("params"), **run["error"]})
            payload["cases"].append(case_payload)

    payload["conclusion_rows"] = [build_case_conclusion(case_payload) for case_payload in payload["cases"]]
    return payload


def md_escape(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(text.split())
    return text.replace("|", "\\|")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(value) for value in row) + " |")
    return "\n".join(lines)


def run_label(run: dict[str, Any]) -> str:
    params = run.get("params", {})
    return f"top_k={params.get('top_k')}, threshold={params.get('similarity_threshold')}"


def build_case_markdown(case_payload: dict[str, Any], section_number: int) -> str:
    case_id = case_payload["case_id"]
    lines = [f"## {section_number}. {case_id} 诊断", ""]
    lines.extend(
        [
            f"- 初步判断：{case_payload.get('initial_assessment')}",
            f"- fail_reason：{case_payload.get('fail_reason')}",
            f"- target_document_id：{case_payload.get('target_document_id') or ''}",
            f"- 关注关键词：{', '.join(case_payload.get('focus_keywords') or [])}",
            "",
        ]
    )

    if case_payload.get("error"):
        error = case_payload["error"]
        lines.extend(
            [
                f"诊断阻塞：{error.get('stage')} / {error.get('type')} / {error.get('message')}",
                "",
            ]
        )
        return "\n".join(lines)

    summary_rows = []
    for run in case_payload.get("runs", []):
        if run.get("error"):
            summary_rows.append([run_label(run), "ERROR", "", "", run["error"].get("message")])
            continue
        focus = run.get("focus_keyword_summary", {})
        expected = run.get("expected_keyword_summary", {})
        summary_rows.append(
            [
                run_label(run),
                run.get("retrieved_count"),
                ", ".join(focus.get("matched_keywords") or []),
                ", ".join(expected.get("matched_keywords") or []),
                focus.get("first_hit_rank"),
            ]
        )
    lines.append(
        md_table(
            ["参数", "retrieved_count", "focus keyword hits", "expected keyword hits", "first focus rank"],
            summary_rows,
        )
    )
    lines.append("")

    conclusion = build_case_conclusion(case_payload)
    lines.extend(
        [
            f"- baseline 参数 top_k=6, threshold=0.25 召回判断：{conclusion['baseline 是否召回关键片段']}",
            f"- 提高 top_k 是否改善：{conclusion['提高 top_k 是否改善']}",
            f"- 降低 threshold 是否改善：{conclusion['降低 threshold 是否改善']}",
            f"- 主要瓶颈：{conclusion['主要瓶颈']}",
            f"- 下一步建议：{conclusion['下一步建议']}",
            "",
        ]
    )

    for run in case_payload.get("runs", []):
        lines.extend([f"### {run_label(run)}", ""])
        if run.get("error"):
            lines.extend([f"ERROR: {run['error'].get('message')}", ""])
            continue
        chunk_rows = []
        for chunk in run.get("chunks", []):
            chunk_rows.append(
                [
                    chunk.get("rank"),
                    chunk.get("document_id"),
                    chunk.get("chunk_id"),
                    chunk.get("distance"),
                    chunk.get("similarity"),
                    chunk.get("page_number"),
                    chunk.get("section_title"),
                    json.dumps(chunk.get("section_path"), ensure_ascii=False)
                    if chunk.get("section_path") is not None
                    else "",
                    chunk.get("is_reference_section"),
                    "true" if chunk.get("keyword_hit") else "false",
                    ", ".join(chunk.get("matched_keywords") or []),
                    chunk.get("content_preview"),
                ]
            )
        lines.append(
            md_table(
                [
                    "rank",
                    "document_id",
                    "chunk_id",
                    "distance",
                    "similarity",
                    "page_number",
                    "section_title",
                    "section_path",
                    "is_reference_section",
                    "keyword_hit",
                    "matched_keywords",
                    "content_preview",
                ],
                chunk_rows,
            )
        )
        lines.append("")

    return "\n".join(lines)


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Retrieval Debug for Heading Eval V2",
        "",
        "## 1. 实验目标",
        "",
        "本实验只诊断 retrieval 行为：不修改 RAG 主链路，不调用 chat 接口，不调用 LLM 生成答案，不重新上传、解析或 embedding 文档。脚本仅对问题做 query embedding，并用只读 pgvector 查询观察不同 top_k 与 similarity_threshold 下召回的 chunks。",
        "",
        "## 2. 参数组合",
        "",
        md_table(
            ["top_k", "similarity_threshold"],
            [[params["top_k"], params["similarity_threshold"]] for params in payload.get("parameter_sets", [])],
        ),
        "",
        "## 3. Case 总览",
        "",
        md_table(
            ["case_id", "question", "fail_reason", "初步判断"],
            [
                [
                    case.get("case_id"),
                    case.get("question"),
                    case.get("fail_reason"),
                    case.get("initial_assessment"),
                ]
                for case in payload.get("cases", [])
            ],
        ),
        "",
    ]

    for index, case_payload in enumerate(payload.get("cases", []), start=4):
        lines.append(build_case_markdown(case_payload, index))
        lines.append("")

    lines.extend(
        [
            f"## {4 + len(payload.get('cases', []))}. 结论表",
            "",
            md_table(
                [
                    "case_id",
                    "问题类型",
                    "baseline 是否召回关键片段",
                    "提高 top_k 是否改善",
                    "降低 threshold 是否改善",
                    "主要瓶颈",
                    "下一步建议",
                ],
                [
                    [
                        row.get("case_id"),
                        row.get("问题类型"),
                        row.get("baseline 是否召回关键片段"),
                        row.get("提高 top_k 是否改善"),
                        row.get("降低 threshold 是否改善"),
                        row.get("主要瓶颈"),
                        row.get("下一步建议"),
                    ]
                    for row in payload.get("conclusion_rows", [])
                ],
            ),
            "",
            "允许的下一步建议集合：" + "、".join(ALLOWED_NEXT_STEPS),
            "",
        ]
    )

    if payload.get("errors"):
        lines.extend(
            [
                "## 运行错误",
                "",
                md_table(
                    ["case_id", "stage", "type", "message"],
                    [
                        [
                            error.get("case_id", ""),
                            error.get("stage"),
                            error.get("type"),
                            error.get("message"),
                        ]
                        for error in payload["errors"]
                    ],
                ),
                "",
            ]
        )

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    output_json = resolve_path(args.output_json)
    output_md = resolve_path(args.output_md)

    try:
        payload = build_payload(args)
    except Exception as exc:  # noqa: BLE001
        payload = {
            "title": "Retrieval Debug for Heading Eval V2",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_id": args.project_id,
            "parameter_sets": DEFAULT_PARAMETER_SETS,
            "cases": [],
            "conclusion_rows": [],
            "errors": [
                {
                    "stage": "fatal",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            ],
        }
        write_json(output_json, payload)
        write_text(output_md, build_markdown(payload))
        print(f"Retrieval debug failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"Wrote error report JSON: {output_json}", file=sys.stderr)
        print(f"Wrote error report Markdown: {output_md}", file=sys.stderr)
        return 1

    write_json(output_json, payload)
    write_text(output_md, build_markdown(payload))
    print(f"Wrote JSON: {output_json}")
    print(f"Wrote Markdown: {output_md}")

    if payload.get("errors"):
        print("Retrieval debug completed with errors. See output files for details.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
