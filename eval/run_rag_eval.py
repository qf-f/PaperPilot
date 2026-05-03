from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_DATASET_PATH = REPO_ROOT / "eval" / "rag_eval_dataset.jsonl"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "eval" / "rag_eval_result.jsonl"
DEFAULT_DOCUMENTS_MAP_PATH = REPO_ROOT / "eval" / "rag_eval_documents.json"
DEFAULT_SUMMARY_OUTPUT_PATH = REPO_ROOT / "eval" / "rag_eval_summary.json"
DEFAULT_BADCASES_OUTPUT_PATH = REPO_ROOT / "eval" / "rag_eval_badcases.jsonl"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
STRICT_NO_EVIDENCE_PHRASES = [
    "论文中未提供相关信息",
    "当前上传文档中没有找到直接依据",
    "没有找到直接依据",
    "不能根据本文得出",
    "无法根据本文得出",
    "文中未提供",
    "未提供相关信息",
]
RELAXED_NO_EVIDENCE_PHRASES = [
    *STRICT_NO_EVIDENCE_PHRASES,
    "未提供",
    "没有提到",
    "未明确说明",
    "无法根据本文得出",
    "文档中没有相关依据",
    "不能根据本文得出",
    "没有相关依据",
    "未提到",
]
CHINESE_STOPWORDS = {
    "这篇",
    "论文",
    "作者",
    "是否",
    "什么",
    "哪些",
    "如何",
    "主要",
    "根据",
    "给出",
    "得到",
    "报告",
    "分析",
    "介绍",
    "一个",
    "一种",
    "以及",
    "还是",
    "不是",
    "中的",
    "该文",
    "综述",
}
WEAK_RETRIEVAL_TOP_SCORE = 0.3


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                samples.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
    return samples


def normalize_text(value: str) -> str:
    return value.casefold().strip()


def normalize_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    normalized = normalized.replace("ᵀ", "t").replace("⊤", "t").replace("transpose", "t")
    normalized = re.sub(r"[，。！？、；：,.!?;:()\[\]{}<>《》“”\"'`~@#$%&*_+=\\|/^-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def compact_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    normalized = normalized.replace("ᵀ", "t").replace("⊤", "t").replace("transpose", "t")
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", normalized)


def formula_variants(value: str) -> set[str]:
    compact = compact_for_match(value)
    variants = {compact} if compact else set()
    if "qk" in compact and "t" in compact:
        variants.add("qkt")
    if "qkt" in compact and "sqrtdk" in compact:
        variants.add("qkt")
    return variants


def keyword_alternatives(keyword: str) -> list[str]:
    return [part.strip() for part in str(keyword).split("|") if part.strip()]


def keyword_hits(answer: str, expected_keywords: list[str]) -> list[str]:
    normalized_answer = normalize_text(answer)
    hits: list[str] = []
    for keyword in expected_keywords:
        normalized_keyword = normalize_text(str(keyword))
        if normalized_keyword and normalized_keyword in normalized_answer:
            hits.append(str(keyword))
    return hits


def relaxed_keyword_hits(answer: str, expected_keywords: list[str]) -> list[str]:
    normalized_answer = normalize_for_match(answer)
    compact_answer = compact_for_match(answer)
    answer_formula_variants = formula_variants(answer)
    hits: list[str] = []
    for keyword in expected_keywords:
        for alternative in keyword_alternatives(str(keyword)):
            normalized_keyword = normalize_for_match(alternative)
            compact_keyword = compact_for_match(alternative)
            keyword_formula_variants = formula_variants(alternative)
            if normalized_keyword and normalized_keyword in normalized_answer:
                hits.append(str(keyword))
                break
            if compact_keyword and compact_keyword in compact_answer:
                hits.append(str(keyword))
                break
            if keyword_formula_variants & answer_formula_variants:
                hits.append(str(keyword))
                break
    return hits


def has_no_evidence_answer(answer: str, relaxed: bool = False) -> bool:
    normalized_answer = normalize_for_match(answer) if relaxed else normalize_text(answer)
    phrases = RELAXED_NO_EVIDENCE_PHRASES if relaxed else STRICT_NO_EVIDENCE_PHRASES
    normalize = normalize_for_match if relaxed else normalize_text
    return any(normalize(phrase) in normalized_answer for phrase in phrases)


def load_documents_map(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    documents = data.get("documents", {})
    if not isinstance(documents, dict):
        raise ValueError(f"Invalid documents map format: {path}")
    return {
        str(paper_id): {
            "document_id": str(info.get("document_id", "")),
            "file_name": str(info.get("file_name", "")),
        }
        for paper_id, info in documents.items()
        if isinstance(info, dict)
    }


def resolve_document_filter(
    sample: dict[str, Any],
    documents_map: dict[str, dict[str, str]],
) -> dict[str, str | bool | None]:
    paper_id = str(sample.get("paper_id") or "")
    document_info = documents_map.get(paper_id) or {}
    target_document_id = document_info.get("document_id") or None
    target_file_name = document_info.get("file_name") or None
    document_filter = bool(target_document_id or target_file_name)
    return {
        "target_document_id": target_document_id,
        "target_file_name": target_file_name,
        "document_filter": document_filter,
        "used_document_filter": document_filter,
    }


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return None


def unique_non_empty(values: list[Any]) -> list[Any]:
    return list(dict.fromkeys(value for value in values if value not in (None, "")))


def normalize_retrieved_chunks(response_payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_chunks = first_non_empty(
        response_payload.get("retrieved_chunks"),
        response_payload.get("sources"),
        response_payload.get("references"),
        response_payload.get("contexts"),
    )
    if not isinstance(raw_chunks, list):
        return []

    chunks: list[dict[str, Any]] = []
    for raw_chunk in raw_chunks:
        if not isinstance(raw_chunk, dict):
            continue
        text = str(
            first_non_empty(
                raw_chunk.get("text_preview"),
                raw_chunk.get("content_preview"),
                raw_chunk.get("content"),
                raw_chunk.get("text"),
            )
            or ""
        )
        chunks.append(
            {
                "text_preview": text[:200],
                "document_id": first_non_empty(raw_chunk.get("document_id"), raw_chunk.get("doc_id")),
                "file_name": first_non_empty(raw_chunk.get("file_name"), raw_chunk.get("filename")),
                "page": first_non_empty(raw_chunk.get("page"), raw_chunk.get("page_number")),
                "score": raw_chunk.get("score"),
                "chunk_id": first_non_empty(raw_chunk.get("chunk_id"), raw_chunk.get("id")),
            }
        )
    return chunks


def classify_error(exc: Exception) -> str:
    error_name = type(exc).__name__.lower()
    error_text = str(exc).lower()
    if isinstance(exc, TimeoutError) or "timeout" in error_name or "timed out" in error_text:
        return "timeout"
    return "rag_error"


def extract_question_terms(question: str) -> list[str]:
    normalized = normalize_for_match(question)
    ascii_terms = re.findall(r"[a-z0-9]{2,}", normalized)
    chinese_segments = re.findall(r"[\u4e00-\u9fff]{2,}", normalized)
    chinese_terms: list[str] = []
    for segment in chinese_segments:
        for stopword in CHINESE_STOPWORDS:
            segment = segment.replace(stopword, " ")
        chinese_terms.extend(term for term in segment.split() if len(term) >= 2)
    return unique_non_empty([*ascii_terms, *chinese_terms])


def question_core_hit_rate(question: str, answer: str) -> float:
    terms = extract_question_terms(question)
    if not terms:
        return 0.0
    compact_answer = compact_for_match(answer)
    hits = sum(1 for term in terms if compact_for_match(term) in compact_answer)
    return hits / len(terms)


def combined_retrieved_text(retrieved_chunks: list[dict[str, Any]]) -> str:
    return "\n".join(str(chunk.get("text_preview") or "") for chunk in retrieved_chunks)


def retrieval_top_score(retrieved_chunks: list[dict[str, Any]]) -> float | None:
    scores: list[float] = []
    for chunk in retrieved_chunks:
        try:
            scores.append(float(chunk.get("score")))
        except (TypeError, ValueError):
            continue
    return max(scores) if scores else None


def is_retrieval_context_weak(
    expected_keywords: list[str],
    retrieved_chunks: list[dict[str, Any]],
) -> bool:
    top_score = retrieval_top_score(retrieved_chunks)
    if top_score is not None and top_score < WEAK_RETRIEVAL_TOP_SCORE:
        return True
    context = combined_retrieved_text(retrieved_chunks)
    if expected_keywords and not relaxed_keyword_hits(context, expected_keywords):
        return True
    return False


def is_likely_eval_keyword_too_strict(
    sample: dict[str, Any],
    answer: str,
    relaxed_keyword_hit_rate: float,
    min_keyword_hit_rate: float,
    retrieved_chunks: list[dict[str, Any]],
) -> bool:
    if relaxed_keyword_hit_rate >= min_keyword_hit_rate and retrieved_chunks:
        return True
    compact_answer = compact_for_match(answer)
    if len(compact_answer) < 80 or not retrieved_chunks:
        return False
    if relaxed_keyword_hit_rate < 0.2:
        return False
    return question_core_hit_rate(str(sample.get("question") or ""), answer) >= 0.35


def determine_fail_reason(
    passed: bool,
    relaxed_passed: bool,
    is_answerable: bool,
    answer: str,
    keyword_hit_rate: float,
    relaxed_keyword_hit_rate: float,
    min_keyword_hit_rate: float,
    retrieved_chunks: list[dict[str, Any]],
    target_document_id: str | None,
    error_type: str | None,
    expected_keywords: list[str],
    sample: dict[str, Any],
) -> str | None:
    if passed:
        return None
    if error_type == "timeout":
        return "timeout"
    if not retrieved_chunks:
        return "no_retrieval"

    if target_document_id:
        retrieved_document_ids = [
            str(chunk.get("document_id"))
            for chunk in retrieved_chunks
            if chunk.get("document_id") not in (None, "")
        ]
        if any(document_id != target_document_id for document_id in retrieved_document_ids):
            return "wrong_document"

    if relaxed_passed:
        return "likely_eval_keyword_too_strict"
    if is_retrieval_context_weak(expected_keywords, retrieved_chunks):
        return "retrieval_context_weak"
    if not is_answerable and not has_no_evidence_answer(answer, relaxed=True):
        return "unanswerable_failed"
    if is_answerable and keyword_hit_rate < min_keyword_hit_rate:
        return "answer_keyword_mismatch"
    return "unknown"


def evaluate_sample(
    sample: dict[str, Any],
    answer: str,
    min_keyword_hit_rate: float,
    retrieved_chunks: list[dict[str, Any]] | None = None,
    document_filter: dict[str, Any] | None = None,
    error_type: str | None = None,
) -> dict[str, Any]:
    retrieved_chunks = retrieved_chunks or []
    document_filter = document_filter or {}
    expected_keywords = [str(item) for item in sample.get("expected_keywords", [])]
    hits = keyword_hits(answer, expected_keywords)
    keyword_hit_count = len(hits)
    keyword_hit_rate = keyword_hit_count / len(expected_keywords) if expected_keywords else 0.0
    relaxed_hits = relaxed_keyword_hits(answer, expected_keywords)
    relaxed_keyword_hit_count = len(relaxed_hits)
    relaxed_keyword_hit_rate = relaxed_keyword_hit_count / len(expected_keywords) if expected_keywords else 0.0
    is_answerable = bool(sample.get("is_answerable", True))

    if is_answerable:
        passed = keyword_hit_rate >= min_keyword_hit_rate
        relaxed_passed = passed or is_likely_eval_keyword_too_strict(
            sample=sample,
            answer=answer,
            relaxed_keyword_hit_rate=relaxed_keyword_hit_rate,
            min_keyword_hit_rate=min_keyword_hit_rate,
            retrieved_chunks=retrieved_chunks,
        )
    else:
        passed = has_no_evidence_answer(answer)
        relaxed_passed = has_no_evidence_answer(answer, relaxed=True)

    target_document_id = document_filter.get("target_document_id")
    target_file_name = document_filter.get("target_file_name")
    fail_reason = determine_fail_reason(
        passed=passed,
        relaxed_passed=relaxed_passed,
        is_answerable=is_answerable,
        answer=answer,
        keyword_hit_rate=keyword_hit_rate,
        relaxed_keyword_hit_rate=relaxed_keyword_hit_rate,
        min_keyword_hit_rate=min_keyword_hit_rate,
        retrieved_chunks=retrieved_chunks,
        target_document_id=str(target_document_id) if target_document_id else None,
        error_type=error_type,
        expected_keywords=expected_keywords,
        sample=sample,
    )

    retrieved_document_ids = unique_non_empty([chunk.get("document_id") for chunk in retrieved_chunks])
    retrieved_file_names = unique_non_empty([chunk.get("file_name") for chunk in retrieved_chunks])
    retrieved_pages = unique_non_empty([chunk.get("page") for chunk in retrieved_chunks])
    retrieved_scores = [chunk.get("score") for chunk in retrieved_chunks if chunk.get("score") not in (None, "")]

    return {
        "id": sample.get("id"),
        "paper_id": sample.get("paper_id"),
        "paper_title": sample.get("paper_title"),
        "question": sample.get("question"),
        "answer": answer,
        "keyword_hit_count": keyword_hit_count,
        "keyword_hit_rate": round(keyword_hit_rate, 4),
        "keyword_hits": hits,
        "relaxed_keyword_hit_count": relaxed_keyword_hit_count,
        "relaxed_keyword_hit_rate": round(relaxed_keyword_hit_rate, 4),
        "relaxed_keyword_hits": relaxed_hits,
        "is_answerable": is_answerable,
        "pass": passed,
        "strict_pass": passed,
        "relaxed_pass": relaxed_passed,
        "retrieved_chunks": retrieved_chunks,
        "retrieved_chunk_count": len(retrieved_chunks),
        "retrieved_document_ids": retrieved_document_ids,
        "retrieved_file_names": retrieved_file_names,
        "retrieved_pages": retrieved_pages,
        "retrieved_scores": retrieved_scores,
        "target_document_id": target_document_id,
        "target_file_name": target_file_name,
        "document_filter": bool(document_filter.get("document_filter")),
        "used_document_filter": bool(document_filter.get("used_document_filter", document_filter.get("document_filter"))),
        "error_type": error_type,
        "fail_reason": fail_reason,
    }


def build_chat_payload(
    question: str,
    args: argparse.Namespace,
    target_document_id: str | None = None,
    target_file_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "project_id": args.project_id,
        "user_id": args.user_id,
        "query": question,
    }
    if target_document_id:
        payload["document_id"] = target_document_id
        payload["document_ids"] = [target_document_id]
    elif args.document_ids:
        payload["document_ids"] = args.document_ids
    if target_file_name:
        payload["file_name"] = target_file_name
    if args.top_k is not None:
        payload["top_k"] = args.top_k
    if args.similarity_threshold is not None:
        payload["similarity_threshold"] = args.similarity_threshold
    return payload


def resolve_chat_url(api_url: str) -> str:
    normalized = api_url.rstrip("/")
    if normalized.endswith("/api/chat"):
        return normalized
    return f"{normalized}/api/chat"


def ask_via_api(
    question: str,
    args: argparse.Namespace,
    target_document_id: str | None = None,
    target_file_name: str | None = None,
) -> dict[str, Any]:
    import httpx

    with httpx.Client(timeout=args.timeout, trust_env=False) as client:
        response = client.post(
            resolve_chat_url(args.api_url),
            json=build_chat_payload(question, args, target_document_id, target_file_name),
        )
        response.raise_for_status()
        return response.json()


def ask_via_service(
    question: str,
    args: argparse.Namespace,
    target_document_id: str | None = None,
    target_file_name: str | None = None,
) -> dict[str, Any]:
    from app.db.session import SessionLocal
    from app.schemas.chat_schema import ChatRequest
    from app.services.chat_service import ChatService

    db = SessionLocal()
    try:
        request = ChatRequest(**build_chat_payload(question, args, target_document_id, target_file_name))
        response = ChatService(db).chat(request)
        if hasattr(response, "model_dump"):
            return response.model_dump(mode="json")
        return response.dict()
    finally:
        db.close()


def build_answer_fn(args: argparse.Namespace) -> Callable[[str, str | None, str | None], dict[str, Any]]:
    if args.api_url:
        return lambda question, document_id, file_name: ask_via_api(question, args, document_id, file_name)
    return lambda question, document_id, file_name: ask_via_service(question, args, document_id, file_name)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for row in results if row["pass"])
    relaxed_passed = sum(1 for row in results if row.get("relaxed_pass", row.get("pass")))
    unanswerable = [row for row in results if not row["is_answerable"]]
    unanswerable_passed = sum(1 for row in unanswerable if row["pass"])
    relaxed_unanswerable_passed = sum(1 for row in unanswerable if row.get("relaxed_pass", row.get("pass")))
    pass_rate = passed / total if total else 0.0
    relaxed_pass_rate = relaxed_passed / total if total else 0.0
    unanswerable_pass_rate = unanswerable_passed / len(unanswerable) if unanswerable else 0.0
    relaxed_unanswerable_pass_rate = (
        relaxed_unanswerable_passed / len(unanswerable) if unanswerable else 0.0
    )
    avg_keyword_hit_rate = (
        sum(float(row.get("keyword_hit_rate", 0.0)) for row in results) / total if total else 0.0
    )
    avg_relaxed_keyword_hit_rate = (
        sum(float(row.get("relaxed_keyword_hit_rate", row.get("keyword_hit_rate", 0.0))) for row in results) / total
        if total
        else 0.0
    )

    fail_reasons = [
        "no_retrieval",
        "wrong_document",
        "answer_keyword_mismatch",
        "likely_eval_keyword_too_strict",
        "unanswerable_failed",
        "retrieval_context_weak",
        "timeout",
        "rag_error",
        "unknown",
    ]
    by_fail_reason = {
        fail_reason: sum(1 for row in results if row.get("fail_reason") == fail_reason)
        for fail_reason in fail_reasons
    }

    by_paper: dict[str, dict[str, Any]] = {}
    for row in results:
        paper_id = str(row.get("paper_id") or "unknown")
        paper_summary = by_paper.setdefault(
            paper_id,
            {
                "total": 0,
                "passed": 0,
                "relaxed_passed": 0,
                "pass_rate": 0.0,
                "strict_pass_rate": 0.0,
                "relaxed_pass_rate": 0.0,
                "avg_keyword_hit_rate": 0.0,
                "avg_relaxed_keyword_hit_rate": 0.0,
                "no_retrieval_count": 0,
                "wrong_document_count": 0,
                "answer_keyword_mismatch_count": 0,
                "likely_eval_keyword_too_strict_count": 0,
                "retrieval_context_weak_count": 0,
                "timeout_count": 0,
            },
        )
        paper_summary["total"] += 1
        paper_summary["passed"] += int(bool(row.get("pass")))
        paper_summary["relaxed_passed"] += int(bool(row.get("relaxed_pass", row.get("pass"))))
        paper_summary["avg_keyword_hit_rate"] += float(row.get("keyword_hit_rate", 0.0))
        paper_summary["avg_relaxed_keyword_hit_rate"] += float(
            row.get("relaxed_keyword_hit_rate", row.get("keyword_hit_rate", 0.0))
        )
        paper_summary["no_retrieval_count"] += int(row.get("fail_reason") == "no_retrieval")
        paper_summary["wrong_document_count"] += int(row.get("fail_reason") == "wrong_document")
        paper_summary["answer_keyword_mismatch_count"] += int(row.get("fail_reason") == "answer_keyword_mismatch")
        paper_summary["likely_eval_keyword_too_strict_count"] += int(
            row.get("fail_reason") == "likely_eval_keyword_too_strict"
        )
        paper_summary["retrieval_context_weak_count"] += int(row.get("fail_reason") == "retrieval_context_weak")
        paper_summary["timeout_count"] += int(row.get("fail_reason") == "timeout")

    for paper_summary in by_paper.values():
        paper_total = paper_summary["total"]
        paper_summary["pass_rate"] = round(paper_summary["passed"] / paper_total, 4) if paper_total else 0.0
        paper_summary["strict_pass_rate"] = paper_summary["pass_rate"]
        paper_summary["relaxed_pass_rate"] = (
            round(paper_summary["relaxed_passed"] / paper_total, 4) if paper_total else 0.0
        )
        paper_summary["avg_keyword_hit_rate"] = (
            round(paper_summary["avg_keyword_hit_rate"] / paper_total, 4) if paper_total else 0.0
        )
        paper_summary["avg_relaxed_keyword_hit_rate"] = (
            round(paper_summary["avg_relaxed_keyword_hit_rate"] / paper_total, 4) if paper_total else 0.0
        )

    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(pass_rate, 4),
        "strict_pass_rate": round(pass_rate, 4),
        "relaxed_passed": relaxed_passed,
        "relaxed_pass_rate": round(relaxed_pass_rate, 4),
        "avg_keyword_hit_rate": round(avg_keyword_hit_rate, 4),
        "avg_relaxed_keyword_hit_rate": round(avg_relaxed_keyword_hit_rate, 4),
        "unanswerable_total": len(unanswerable),
        "unanswerable_passed": unanswerable_passed,
        "unanswerable_pass_rate": round(unanswerable_pass_rate, 4),
        "relaxed_unanswerable_passed": relaxed_unanswerable_passed,
        "relaxed_unanswerable_pass_rate": round(relaxed_unanswerable_pass_rate, 4),
        "no_retrieval_count": by_fail_reason["no_retrieval"],
        "wrong_document_count": by_fail_reason["wrong_document"],
        "answer_keyword_mismatch_count": by_fail_reason["answer_keyword_mismatch"],
        "likely_eval_keyword_too_strict_count": by_fail_reason["likely_eval_keyword_too_strict"],
        "retrieval_context_weak_count": by_fail_reason["retrieval_context_weak"],
        "timeout_count": by_fail_reason["timeout"],
        "by_paper": by_paper,
        "by_fail_reason": by_fail_reason,
    }


def print_summary(results: list[dict[str, Any]]) -> None:
    summary = build_summary(results)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal RAG evaluation over a JSONL dataset.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT_PATH)
    parser.add_argument("--save-badcases", type=Path, default=DEFAULT_BADCASES_OUTPUT_PATH)
    parser.add_argument("--documents-map", type=Path, default=DEFAULT_DOCUMENTS_MAP_PATH)
    parser.add_argument("--project-id", default=os.getenv("RAG_EVAL_PROJECT_ID"))
    parser.add_argument("--user-id", default=os.getenv("RAG_EVAL_USER_ID", DEFAULT_USER_ID))
    parser.add_argument("--document-id", dest="document_ids", action="append")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--similarity-threshold", type=float, default=None)
    parser.add_argument("--api-url", default=os.getenv("RAG_EVAL_API_URL"))
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--min-keyword-hit-rate", type=float, default=0.5)
    args = parser.parse_args(argv)
    if not args.project_id:
        parser.error("project_id is required. Pass --project-id or set RAG_EVAL_PROJECT_ID.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    samples = iter_jsonl(args.dataset)
    documents_map = load_documents_map(args.documents_map)
    if documents_map:
        print(f"Loaded documents map: {args.documents_map}")
    else:
        print(f"Documents map not found or empty, running without per-paper document filters: {args.documents_map}")
    answer_question = build_answer_fn(args)
    results: list[dict[str, Any]] = []

    for sample in samples:
        question = str(sample.get("question", ""))
        document_filter = resolve_document_filter(sample, documents_map)
        target_document_id = document_filter["target_document_id"]
        target_file_name = document_filter["target_file_name"]
        try:
            response_payload = answer_question(
                question,
                str(target_document_id) if target_document_id else None,
                str(target_file_name) if target_file_name else None,
            )
            answer = str(response_payload.get("answer", ""))
            retrieved_chunks = normalize_retrieved_chunks(response_payload)
            error_type = None
        except Exception as exc:
            error_type = classify_error(exc)
            answer = "RAG 调用失败：timed out" if error_type == "timeout" else f"RAG 调用失败：{exc}"
            retrieved_chunks = []
        result = evaluate_sample(
            sample=sample,
            answer=answer,
            min_keyword_hit_rate=args.min_keyword_hit_rate,
            retrieved_chunks=retrieved_chunks,
            document_filter=document_filter,
            error_type=error_type,
        )
        results.append(result)
        print(
            f"{result['id']}: pass={result['pass']} "
            f"relaxed_pass={result['relaxed_pass']} "
            f"keyword_hit_rate={result['keyword_hit_rate']} "
            f"relaxed_keyword_hit_rate={result['relaxed_keyword_hit_rate']} "
            f"retrieved={result['retrieved_chunk_count']} "
            f"fail_reason={result['fail_reason']} "
            f"document_filter={result['document_filter']}"
        )

    write_jsonl(args.output, results)
    badcases = [row for row in results if not row["pass"]]
    write_jsonl(args.save_badcases, badcases)
    summary = build_summary(results)
    write_json(args.summary_output, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved results to {args.output}")
    print(f"Saved summary to {args.summary_output}")
    print(f"Saved badcases to {args.save_badcases}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
