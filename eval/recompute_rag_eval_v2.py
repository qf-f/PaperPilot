from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.run_rag_eval import (  # noqa: E402
    WEAK_RETRIEVAL_TOP_SCORE,
    build_summary,
    compact_for_match,
    formula_variants,
    normalize_for_match,
    normalize_text,
    question_core_hit_rate,
    retrieval_top_score,
    unique_non_empty,
)


DEFAULT_DATASET_PATH = REPO_ROOT / "eval" / "rag_eval_dataset_5papers_checked.jsonl"
DEFAULT_MIN_KEYWORD_HIT_RATE = 0.5
EVAL_VERSION = "v2"

V2_NO_EVIDENCE_PHRASES = [
    "没有提供",
    "未提供",
    "没有说明",
    "未说明",
    "没有提到",
    "未提到",
    "没有找到",
    "未找到",
    "没有直接依据",
    "未找到直接依据",
    "无法从论文中得出",
    "无法从文档中得出",
    "无法根据当前文档判断",
    "当前上传文档中没有找到",
    "文中没有相关信息",
    "不涉及",
    "没有相关信息",
    "不存在相关描述",
    "不包含相关内容",
]

FAIL_REASONS = [
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def has_no_evidence_answer_v2(answer: str) -> bool:
    normalized_answer = normalize_for_match(answer)
    return any(normalize_for_match(phrase) in normalized_answer for phrase in V2_NO_EVIDENCE_PHRASES)


def _alternatives_from_keyword(keyword: Any) -> list[str]:
    return [part.strip() for part in str(keyword).split("|") if part.strip()]


def keyword_groups(sample: dict[str, Any]) -> list[list[str]]:
    raw_groups = sample.get("expected_keyword_groups")
    groups: list[list[str]] = []
    if isinstance(raw_groups, list):
        for raw_group in raw_groups:
            if isinstance(raw_group, list):
                group = [str(item).strip() for item in raw_group if str(item).strip()]
            else:
                group = _alternatives_from_keyword(raw_group)
            if group:
                groups.append(group)
    if groups:
        return groups

    raw_keywords = sample.get("expected_keywords", [])
    if not isinstance(raw_keywords, list):
        return []
    return [_alternatives_from_keyword(keyword) for keyword in raw_keywords if _alternatives_from_keyword(keyword)]


def _group_label(group: list[str]) -> str:
    return "|".join(group)


def _strict_group_hit(text: str, group: list[str]) -> bool:
    normalized_text = normalize_text(text)
    return any(normalize_text(alternative) in normalized_text for alternative in group)


def _relaxed_group_hit(text: str, group: list[str]) -> bool:
    normalized_text = normalize_for_match(text)
    compact_text = compact_for_match(text)
    text_formula_variants = formula_variants(text)
    for alternative in group:
        normalized_alternative = normalize_for_match(alternative)
        compact_alternative = compact_for_match(alternative)
        alternative_formula_variants = formula_variants(alternative)
        if normalized_alternative and normalized_alternative in normalized_text:
            return True
        if compact_alternative and compact_alternative in compact_text:
            return True
        if alternative_formula_variants & text_formula_variants:
            return True
    return False


def keyword_hits_v2(text: str, groups: list[list[str]], *, relaxed: bool = False) -> list[str]:
    hit_fn = _relaxed_group_hit if relaxed else _strict_group_hit
    return [_group_label(group) for group in groups if hit_fn(text, group)]


def combined_retrieved_text(retrieved_chunks: list[dict[str, Any]]) -> str:
    return "\n".join(str(chunk.get("text_preview") or "") for chunk in retrieved_chunks)


def is_retrieval_context_weak_v2(
    groups: list[list[str]],
    retrieved_chunks: list[dict[str, Any]],
) -> bool:
    top_score = retrieval_top_score(retrieved_chunks)
    if top_score is not None and top_score < WEAK_RETRIEVAL_TOP_SCORE:
        return True
    if groups and not keyword_hits_v2(combined_retrieved_text(retrieved_chunks), groups, relaxed=True):
        return True
    return False


def is_likely_eval_keyword_too_strict_v2(
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


def determine_fail_reason_v2(
    *,
    passed: bool,
    relaxed_passed: bool,
    is_answerable: bool,
    answer: str,
    keyword_hit_rate: float,
    min_keyword_hit_rate: float,
    retrieved_chunks: list[dict[str, Any]],
    target_document_id: str | None,
    error_type: str | None,
    groups: list[list[str]],
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

    if not is_answerable:
        return "unanswerable_failed" if not has_no_evidence_answer_v2(answer) else None

    if relaxed_passed:
        return "likely_eval_keyword_too_strict"
    if is_retrieval_context_weak_v2(groups, retrieved_chunks):
        return "retrieval_context_weak"
    if keyword_hit_rate < min_keyword_hit_rate:
        return "answer_keyword_mismatch"
    return "unknown"


def evaluate_sample_v2(
    sample: dict[str, Any],
    answer: str,
    min_keyword_hit_rate: float = DEFAULT_MIN_KEYWORD_HIT_RATE,
    retrieved_chunks: list[dict[str, Any]] | None = None,
    document_filter: dict[str, Any] | None = None,
    error_type: str | None = None,
) -> dict[str, Any]:
    retrieved_chunks = retrieved_chunks or []
    document_filter = document_filter or {}
    groups = keyword_groups(sample)
    hits = keyword_hits_v2(answer, groups)
    keyword_hit_rate = len(hits) / len(groups) if groups else 0.0
    relaxed_hits = keyword_hits_v2(answer, groups, relaxed=True)
    relaxed_keyword_hit_rate = len(relaxed_hits) / len(groups) if groups else 0.0
    is_answerable = bool(sample.get("is_answerable", True))

    if is_answerable:
        passed = keyword_hit_rate >= min_keyword_hit_rate
        relaxed_passed = passed or is_likely_eval_keyword_too_strict_v2(
            sample=sample,
            answer=answer,
            relaxed_keyword_hit_rate=relaxed_keyword_hit_rate,
            min_keyword_hit_rate=min_keyword_hit_rate,
            retrieved_chunks=retrieved_chunks,
        )
    else:
        passed = has_no_evidence_answer_v2(answer)
        relaxed_passed = passed

    target_document_id = document_filter.get("target_document_id")
    target_file_name = document_filter.get("target_file_name")
    fail_reason = determine_fail_reason_v2(
        passed=passed,
        relaxed_passed=relaxed_passed,
        is_answerable=is_answerable,
        answer=answer,
        keyword_hit_rate=keyword_hit_rate,
        min_keyword_hit_rate=min_keyword_hit_rate,
        retrieved_chunks=retrieved_chunks,
        target_document_id=str(target_document_id) if target_document_id else None,
        error_type=error_type,
        groups=groups,
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
        "keyword_hit_count": len(hits),
        "keyword_hit_rate": round(keyword_hit_rate, 4),
        "keyword_hits": hits,
        "relaxed_keyword_hit_count": len(relaxed_hits),
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
        "eval_version": EVAL_VERSION,
    }


def sample_from_existing_result(row: dict[str, Any], dataset_sample: dict[str, Any]) -> dict[str, Any]:
    merged = dict(dataset_sample)
    for key in ("id", "paper_id", "paper_title", "question", "is_answerable"):
        if key not in merged and key in row:
            merged[key] = row[key]
    return merged


def document_filter_from_result(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_document_id": row.get("target_document_id"),
        "target_file_name": row.get("target_file_name"),
        "document_filter": bool(row.get("document_filter")),
        "used_document_filter": bool(row.get("used_document_filter", row.get("document_filter"))),
    }


def recompute_results_v2(
    result_rows: list[dict[str, Any]],
    dataset_rows: list[dict[str, Any]],
    min_keyword_hit_rate: float = DEFAULT_MIN_KEYWORD_HIT_RATE,
) -> list[dict[str, Any]]:
    samples_by_id = {str(sample.get("id")): sample for sample in dataset_rows}
    recomputed: list[dict[str, Any]] = []
    for row in result_rows:
        row_id = str(row.get("id"))
        if row_id not in samples_by_id:
            raise KeyError(f"Dataset does not include result id: {row_id}")
        sample = sample_from_existing_result(row, samples_by_id[row_id])
        recomputed.append(
            evaluate_sample_v2(
                sample=sample,
                answer=str(row.get("answer") or ""),
                min_keyword_hit_rate=min_keyword_hit_rate,
                retrieved_chunks=list(row.get("retrieved_chunks") or []),
                document_filter=document_filter_from_result(row),
                error_type=row.get("error_type"),
            )
        )
    return recomputed


def save_badcases(path: Path, rows: list[dict[str, Any]]) -> None:
    write_jsonl(path, [row for row in rows if not row.get("pass")])


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recompute PaperPilot RAG eval results with eval_v2 scoring.")
    parser.add_argument("--input-result", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--save-badcases", type=Path)
    parser.add_argument("--min-keyword-hit-rate", type=float, default=DEFAULT_MIN_KEYWORD_HIT_RATE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result_rows = iter_jsonl(args.input_result)
    dataset_rows = iter_jsonl(args.dataset)
    recomputed = recompute_results_v2(
        result_rows=result_rows,
        dataset_rows=dataset_rows,
        min_keyword_hit_rate=args.min_keyword_hit_rate,
    )
    summary = build_summary(recomputed)
    summary["eval_version"] = EVAL_VERSION
    summary["source_result"] = str(args.input_result)
    summary["dataset"] = str(args.dataset)

    write_jsonl(args.output, recomputed)
    write_json(args.summary_output, summary)
    if args.save_badcases:
        save_badcases(args.save_badcases, recomputed)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved eval_v2 results to {args.output}")
    print(f"Saved eval_v2 summary to {args.summary_output}")
    if args.save_badcases:
        print(f"Saved eval_v2 badcases to {args.save_badcases}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
