from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agents.graph import run_knowledge_qa_graph  # noqa: E402
from eval.recompute_rag_eval_v2 import recompute_results_v2  # noqa: E402
from eval.run_rag_eval import (  # noqa: E402
    DEFAULT_USER_ID,
    build_summary,
    classify_error,
    evaluate_sample,
    iter_jsonl,
    load_documents_map,
    normalize_retrieved_chunks,
    resolve_document_filter,
    write_json,
    write_jsonl,
)


GRID = [
    (4, 0.25),
    (4, 0.30),
    (4, 0.35),
    (6, 0.25),
    (6, 0.30),
    (6, 0.35),
    (8, 0.25),
    (8, 0.30),
    (8, 0.35),
]


def threshold_slug(value: float) -> str:
    return f"{int(round(value * 100)):03d}"


def run_slug(top_k: int, threshold: float) -> str:
    return f"heading_topk{top_k}_th{threshold_slug(threshold)}"


def result_paths(base_dir: Path, top_k: int, threshold: float) -> dict[str, Path]:
    slug = run_slug(top_k, threshold)
    run_dir = base_dir / "runs" / slug
    return {
        "run_dir": run_dir,
        "raw_result": run_dir / f"rag_eval_result_{slug}.jsonl",
        "raw_summary": run_dir / f"rag_eval_summary_{slug}.json",
        "v2_result": run_dir / f"rag_eval_result_{slug}_eval_v2.jsonl",
        "v2_summary": run_dir / f"rag_eval_summary_{slug}_eval_v2.json",
        "v2_badcases": run_dir / f"rag_eval_badcases_{slug}_eval_v2.jsonl",
        "metadata": run_dir / "run_metadata.json",
    }


def answer_with_graph(
    *,
    project_id: str,
    user_id: str,
    question: str,
    document_id: str | None,
    top_k: int,
    similarity_threshold: float,
) -> dict[str, Any]:
    state = run_knowledge_qa_graph(
        {
            "user_id": user_id,
            "project_id": project_id,
            "session_id": "00000000-0000-0000-0000-000000000000",
            "query": question,
            "document_ids": [document_id] if document_id else [],
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "trace": [],
        }
    )
    return {
        "answer": state.get("answer", ""),
        "retrieved_chunks": state.get("retrieved_chunks", []),
    }


def run_one(
    *,
    base_dir: Path,
    dataset_rows: list[dict[str, Any]],
    documents_map: dict[str, dict[str, str]],
    project_id: str,
    user_id: str,
    top_k: int,
    similarity_threshold: float,
    min_keyword_hit_rate: float,
) -> dict[str, Any]:
    paths = result_paths(base_dir, top_k, similarity_threshold)
    paths["run_dir"].mkdir(parents=True, exist_ok=True)
    slug = run_slug(top_k, similarity_threshold)
    print(f"=== Running {slug} ===", flush=True)

    raw_rows: list[dict[str, Any]] = []
    total = len(dataset_rows)
    for index, sample in enumerate(dataset_rows, start=1):
        question = str(sample.get("question") or "")
        document_filter = resolve_document_filter(sample, documents_map)
        target_document_id = document_filter["target_document_id"]
        try:
            response_payload = answer_with_graph(
                project_id=project_id,
                user_id=user_id,
                question=question,
                document_id=str(target_document_id) if target_document_id else None,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
            answer = str(response_payload.get("answer") or "")
            retrieved_chunks = normalize_retrieved_chunks(response_payload)
            error_type = None
        except Exception as exc:  # keep the grid running and let eval classify failures.
            error_type = classify_error(exc)
            answer = "RAG 调用失败：timed out" if error_type == "timeout" else f"RAG 调用失败：{exc}"
            retrieved_chunks = []

        result = evaluate_sample(
            sample=sample,
            answer=answer,
            min_keyword_hit_rate=min_keyword_hit_rate,
            retrieved_chunks=retrieved_chunks,
            document_filter=document_filter,
            error_type=error_type,
        )
        raw_rows.append(result)
        print(
            f"{slug} {index:02d}/{total} {result['id']}: "
            f"pass={result['pass']} relaxed={result['relaxed_pass']} "
            f"retrieved={result['retrieved_chunk_count']} reason={result['fail_reason']}",
            flush=True,
        )

    write_jsonl(paths["raw_result"], raw_rows)
    raw_summary = build_summary(raw_rows)
    raw_summary.update(
        {
            "run_slug": slug,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
        }
    )
    write_json(paths["raw_summary"], raw_summary)

    v2_rows = recompute_results_v2(
        result_rows=raw_rows,
        dataset_rows=dataset_rows,
        min_keyword_hit_rate=min_keyword_hit_rate,
    )
    write_jsonl(paths["v2_result"], v2_rows)
    v2_summary = build_summary(v2_rows)
    v2_summary.update(
        {
            "eval_version": "v2",
            "run_slug": slug,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "source_result": str(paths["raw_result"]),
            "dataset": "eval/rag_eval_dataset_5papers_checked.jsonl",
        }
    )
    write_json(paths["v2_summary"], v2_summary)
    v2_badcases = [row for row in v2_rows if not row.get("pass")]
    write_jsonl(paths["v2_badcases"], v2_badcases)
    write_json(
        paths["metadata"],
        {
            "run_slug": slug,
            "project_id": project_id,
            "chunk_strategy": "heading",
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "min_keyword_hit_rate": min_keyword_hit_rate,
            "raw_result": str(paths["raw_result"]),
            "raw_summary": str(paths["raw_summary"]),
            "eval_v2_result": str(paths["v2_result"]),
            "eval_v2_summary": str(paths["v2_summary"]),
            "eval_v2_badcases": str(paths["v2_badcases"]),
            "notes": [
                "Runs the existing knowledge QA LangGraph directly to avoid ChatService persistence.",
                "Does not upload, parse, re-chunk, or re-embed documents.",
            ],
        },
    )
    print(
        f"=== Finished {slug}: pass_rate={v2_summary['pass_rate']} "
        f"relaxed_pass_rate={v2_summary['relaxed_pass_rate']} ===",
        flush=True,
    )
    return v2_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run heading top_k / similarity_threshold grid eval.")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("eval/results/topk_threshold_grid_20260508"),
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("eval/rag_eval_dataset_5papers_checked.jsonl"),
    )
    parser.add_argument(
        "--documents-map",
        type=Path,
        default=Path("eval/results/heading_20260504/rag_eval_documents.json"),
    )
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--min-keyword-hit-rate", type=float, default=0.5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.base_dir.mkdir(parents=True, exist_ok=True)
    dataset_rows = iter_jsonl(args.dataset)
    documents_map_payload = json.loads(args.documents_map.read_text(encoding="utf-8"))
    project_id = args.project_id or str(documents_map_payload.get("project_id") or "")
    if not project_id:
        raise ValueError("project_id is required, pass --project-id or include it in documents map.")
    documents_map = load_documents_map(args.documents_map)

    summaries = []
    for top_k, threshold in GRID:
        summaries.append(
            run_one(
                base_dir=args.base_dir,
                dataset_rows=dataset_rows,
                documents_map=documents_map,
                project_id=project_id,
                user_id=args.user_id,
                top_k=top_k,
                similarity_threshold=threshold,
                min_keyword_hit_rate=args.min_keyword_hit_rate,
            )
        )

    write_json(
        args.base_dir / "archive" / "grid_run_summaries.raw.json",
        {"runs": summaries},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
