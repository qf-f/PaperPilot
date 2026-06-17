from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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

FIELDS = [
    "top_k",
    "similarity_threshold",
    "total",
    "passed",
    "pass_rate",
    "relaxed_passed",
    "relaxed_pass_rate",
    "avg_keyword_hit_rate",
    "avg_relaxed_keyword_hit_rate",
    "unanswerable_pass_rate",
    "no_retrieval_count",
    "wrong_document_count",
    "answer_keyword_mismatch_count",
    "likely_eval_keyword_too_strict_count",
    "retrieval_context_weak_count",
    "timeout_count",
]


def threshold_slug(value: float) -> str:
    return f"{int(round(value * 100)):03d}"


def run_slug(top_k: int, threshold: float) -> str:
    return f"heading_topk{top_k}_th{threshold_slug(threshold)}"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def run_paths(top_k: int, threshold: float) -> dict[str, Path]:
    slug = run_slug(top_k, threshold)
    run_dir = BASE_DIR / "runs" / slug
    return {
        "slug": slug,
        "summary": run_dir / f"rag_eval_summary_{slug}_eval_v2.json",
        "result": run_dir / f"rag_eval_result_{slug}_eval_v2.jsonl",
        "badcases": run_dir / f"rag_eval_badcases_{slug}_eval_v2.jsonl",
    }


def load_runs() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    rows: list[dict[str, Any]] = []
    results_by_slug: dict[str, list[dict[str, Any]]] = {}
    missing: list[str] = []
    for top_k, threshold in GRID:
        paths = run_paths(top_k, threshold)
        if not paths["summary"].exists() or not paths["result"].exists() or not paths["badcases"].exists():
            missing.append(paths["slug"])
            continue
        summary = read_json(paths["summary"])
        row = {field: summary.get(field) for field in FIELDS}
        row["top_k"] = top_k
        row["similarity_threshold"] = threshold
        row["run_slug"] = paths["slug"]
        row["summary_path"] = str(paths["summary"].relative_to(REPO_ROOT))
        row["result_path"] = str(paths["result"].relative_to(REPO_ROOT))
        row["badcases_path"] = str(paths["badcases"].relative_to(REPO_ROOT))
        rows.append(row)
        results_by_slug[paths["slug"]] = iter_jsonl(paths["result"])
    if missing:
        raise FileNotFoundError(f"Missing completed run outputs: {', '.join(missing)}")
    return rows, results_by_slug


def sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            float(row["pass_rate"]),
            float(row["relaxed_pass_rate"]),
            float(row["avg_keyword_hit_rate"]),
            -int(row["retrieval_context_weak_count"]),
            -int(row["answer_keyword_mismatch_count"]),
            float(row["unanswerable_pass_rate"]),
        ),
        reverse=True,
    )


def best_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted_rows(rows)[0]


def collect_case_analysis(results_by_slug: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    case_runs: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for slug, rows in results_by_slug.items():
        for row in rows:
            case_id = str(row.get("id"))
            case_runs[case_id][slug] = {
                "pass": bool(row.get("pass")),
                "relaxed_pass": bool(row.get("relaxed_pass")),
                "fail_reason": row.get("fail_reason"),
                "retrieved_chunk_count": row.get("retrieved_chunk_count"),
                "keyword_hit_rate": row.get("keyword_hit_rate"),
                "relaxed_keyword_hit_rate": row.get("relaxed_keyword_hit_rate"),
            }

    always_failed: list[str] = []
    variable_cases: list[dict[str, Any]] = []
    topk_noise_cases: list[dict[str, Any]] = []
    threshold_sensitive_cases: list[dict[str, Any]] = []

    for case_id in sorted(case_runs):
        states = case_runs[case_id]
        pass_slugs = [slug for slug, state in states.items() if state["pass"]]
        fail_slugs = [slug for slug, state in states.items() if not state["pass"]]
        if len(fail_slugs) == len(GRID):
            reasons = sorted({str(states[slug]["fail_reason"]) for slug in fail_slugs})
            always_failed.append(f"{case_id} ({', '.join(reasons)})")
        elif pass_slugs and fail_slugs:
            variable_cases.append(
                {
                    "case_id": case_id,
                    "pass_runs": pass_slugs,
                    "fail_runs": fail_slugs,
                }
            )

        for threshold in (0.25, 0.30, 0.35):
            slug4 = run_slug(4, threshold)
            slug6 = run_slug(6, threshold)
            slug8 = run_slug(8, threshold)
            if slug4 in states and slug8 in states:
                if (states[slug4]["pass"] or states.get(slug6, {}).get("pass")) and not states[slug8]["pass"]:
                    topk_noise_cases.append(
                        {
                            "case_id": case_id,
                            "threshold": threshold,
                            "topk4": states[slug4],
                            "topk6": states.get(slug6),
                            "topk8": states[slug8],
                        }
                    )

        for top_k in (4, 6, 8):
            statuses = [
                (threshold, states[run_slug(top_k, threshold)]["pass"])
                for threshold in (0.25, 0.30, 0.35)
                if run_slug(top_k, threshold) in states
            ]
            if len({status for _, status in statuses}) > 1:
                threshold_sensitive_cases.append(
                    {
                        "case_id": case_id,
                        "top_k": top_k,
                        "statuses": statuses,
                    }
                )

    return {
        "always_failed": always_failed,
        "variable_cases": variable_cases,
        "topk_noise_cases": topk_noise_cases,
        "threshold_sensitive_cases": threshold_sensitive_cases,
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def write_compare(rows: list[dict[str, Any]], case_analysis: dict[str, Any]) -> None:
    ordered = sorted_rows(rows)
    compare = {
        "sorted_by_pass_rate_relaxed_pass_rate": ordered,
        "best": best_row(rows),
        "case_analysis": case_analysis,
    }
    (BASE_DIR / "grid_compare.json").write_text(
        json.dumps(compare, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    table_rows = [
        [
            row["run_slug"],
            row["top_k"],
            row["similarity_threshold"],
            row["passed"],
            row["pass_rate"],
            row["relaxed_passed"],
            row["relaxed_pass_rate"],
            row["avg_keyword_hit_rate"],
            row["avg_relaxed_keyword_hit_rate"],
            row["unanswerable_pass_rate"],
            row["no_retrieval_count"],
            row["answer_keyword_mismatch_count"],
            row["likely_eval_keyword_too_strict_count"],
            row["retrieval_context_weak_count"],
            row["timeout_count"],
        ]
        for row in ordered
    ]
    content = "# TopK + Similarity Threshold Grid Compare\n\n"
    content += "按 `pass_rate`、`relaxed_pass_rate`、`avg_keyword_hit_rate` 降序排序。\n\n"
    content += markdown_table(
        [
            "run",
            "top_k",
            "threshold",
            "passed",
            "pass_rate",
            "relaxed_passed",
            "relaxed_pass_rate",
            "avg_hit",
            "avg_relaxed_hit",
            "unanswerable_pass_rate",
            "no_retrieval",
            "answer_mismatch",
            "keyword_too_strict",
            "retrieval_weak",
            "timeout",
        ],
        table_rows,
    )
    content += "\n\n## Best\n\n"
    best = best_row(rows)
    content += (
        f"- best_run: `{best['run_slug']}`\n"
        f"- top_k: {best['top_k']}\n"
        f"- similarity_threshold: {best['similarity_threshold']}\n"
        f"- pass_rate: {best['pass_rate']}\n"
        f"- relaxed_pass_rate: {best['relaxed_pass_rate']}\n"
    )
    (BASE_DIR / "grid_compare.md").write_text(content, encoding="utf-8")


def write_badcase_reports(case_analysis: dict[str, Any]) -> None:
    badcase_dir = BASE_DIR / "badcases"
    badcase_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in case_analysis.items():
        (badcase_dir / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    content = "# Grid Badcase Analysis\n\n"
    content += "## 多个组合下都失败\n\n"
    if case_analysis["always_failed"]:
        content += "\n".join(f"- {item}" for item in case_analysis["always_failed"]) + "\n\n"
    else:
        content += "- 无。\n\n"

    content += "## 只在部分组合下通过\n\n"
    for item in case_analysis["variable_cases"][:30]:
        content += (
            f"- {item['case_id']}: pass_runs={', '.join(item['pass_runs'])}; "
            f"fail_runs={', '.join(item['fail_runs'])}\n"
        )
    if not case_analysis["variable_cases"]:
        content += "- 无。\n"
    content += "\n"

    content += "## threshold 敏感 case\n\n"
    for item in case_analysis["threshold_sensitive_cases"][:30]:
        content += f"- {item['case_id']} at top_k={item['top_k']}: {item['statuses']}\n"
    if not case_analysis["threshold_sensitive_cases"]:
        content += "- 无。\n"
    content += "\n"

    content += "## top_k 增大后反而失败\n\n"
    for item in case_analysis["topk_noise_cases"][:30]:
        content += f"- {item['case_id']} at threshold={item['threshold']}\n"
    if not case_analysis["topk_noise_cases"]:
        content += "- 无。\n"
    content += "\n"
    (badcase_dir / "badcase_analysis.md").write_text(content, encoding="utf-8")


def write_readme(rows: list[dict[str, Any]], case_analysis: dict[str, Any]) -> None:
    ordered = sorted_rows(rows)
    best = ordered[0]
    topk_summary: dict[int, list[dict[str, Any]]] = defaultdict(list)
    threshold_summary: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        topk_summary[int(row["top_k"])].append(row)
        threshold_summary[float(row["similarity_threshold"])].append(row)

    avg_by_topk = {
        top_k: {
            "avg_pass_rate": round(sum(float(row["pass_rate"]) for row in group) / len(group), 4),
            "avg_relaxed_pass_rate": round(
                sum(float(row["relaxed_pass_rate"]) for row in group) / len(group), 4
            ),
            "avg_answer_keyword_mismatch": round(
                sum(int(row["answer_keyword_mismatch_count"]) for row in group) / len(group), 2
            ),
        }
        for top_k, group in sorted(topk_summary.items())
    }
    avg_by_threshold = {
        threshold: {
            "avg_pass_rate": round(sum(float(row["pass_rate"]) for row in group) / len(group), 4),
            "avg_no_retrieval": round(sum(int(row["no_retrieval_count"]) for row in group) / len(group), 2),
            "avg_retrieval_context_weak": round(
                sum(int(row["retrieval_context_weak_count"]) for row in group) / len(group), 2
            ),
        }
        for threshold, group in sorted(threshold_summary.items())
    }

    same_best = [row for row in ordered if row["pass_rate"] == best["pass_rate"]]
    recommendation = "暂不推荐替换当前默认配置"
    if best["top_k"] == 6 and float(best["similarity_threshold"]) == 0.25:
        recommendation = "保持当前默认配置"
    elif float(best["pass_rate"]) > 0.74:
        recommendation = "仅作为候选配置保留，建议复跑确认后再替换"

    always_failed = case_analysis["always_failed"][:12]
    threshold_sensitive = case_analysis["threshold_sensitive_cases"][:12]
    topk_noise = case_analysis["topk_noise_cases"][:12]

    content = "# TopK + Similarity Threshold Grid Experiment - 2026-05-08\n\n"
    content += "## 1. 实验目的\n\n"
    content += (
        "本轮实验验证 heading chunk 策略下，`top_k` 和 `similarity_threshold` 联合调整是否能提升 RAG 评测指标。"
        "此前单独把 `top_k` 从 6 提到 8，在 `similarity_threshold=0.25` 下没有稳定提升，说明需要同时观察召回数量和相似度过滤强度。\n\n"
    )
    content += "## 2. 实验设置\n\n"
    content += (
        "- `CHUNK_STRATEGY=heading`\n"
        "- 使用已有 heading chunks，不重新上传、不重新解析、不重新 embedding\n"
        "- 不改数据库结构，不接入 rerank/query rewrite/metadata 加权\n"
        "- 不改 prompt，不改 eval 数据集\n"
        "- 只改变 `top_k` 和 `similarity_threshold`\n"
        "- eval_v2 使用 `eval/rag_eval_dataset_5papers_checked.jsonl` 中的 `expected_keyword_groups`\n\n"
    )
    content += "## 3. 总表\n\n"
    content += markdown_table(
        ["run", "top_k", "threshold", "pass_rate", "relaxed_pass_rate", "avg_hit", "no_retrieval", "answer_mismatch", "retrieval_weak"],
        [
            [
                row["run_slug"],
                row["top_k"],
                row["similarity_threshold"],
                row["pass_rate"],
                row["relaxed_pass_rate"],
                row["avg_keyword_hit_rate"],
                row["no_retrieval_count"],
                row["answer_keyword_mismatch_count"],
                row["retrieval_context_weak_count"],
            ]
            for row in ordered
        ],
    )
    content += "\n\n## 4. 最佳组合\n\n"
    content += (
        f"- strict pass_rate 最佳组合：`{best['run_slug']}`，top_k={best['top_k']}，"
        f"similarity_threshold={best['similarity_threshold']}，pass_rate={best['pass_rate']}。\n"
        f"- relaxed_pass_rate={best['relaxed_pass_rate']}，avg_keyword_hit_rate={best['avg_keyword_hit_rate']}，"
        f"retrieval_context_weak_count={best['retrieval_context_weak_count']}，"
        f"answer_keyword_mismatch_count={best['answer_keyword_mismatch_count']}，"
        f"unanswerable_pass_rate={best['unanswerable_pass_rate']}。\n"
    )
    if len(same_best) > 1:
        content += "- 存在多个 strict pass_rate 并列组合，排序进一步参考 relaxed_pass_rate、avg_keyword_hit_rate 和失败类型计数。\n"
    content += f"- 配置建议：{recommendation}。\n\n"

    content += "## 5. 对 top_k 的观察\n\n"
    for top_k, summary in avg_by_topk.items():
        content += (
            f"- top_k={top_k}: avg_pass_rate={summary['avg_pass_rate']}，"
            f"avg_relaxed_pass_rate={summary['avg_relaxed_pass_rate']}，"
            f"avg_answer_keyword_mismatch={summary['avg_answer_keyword_mismatch']}。\n"
        )
    content += (
        "- 若 top_k 增大没有稳定提升，说明新增上下文并不总能转化为答案关键词命中。\n"
        "- 需要关注 top_k=8 是否只改善少数 case，同时让部分原本通过的 case 因上下文噪声而退化。\n\n"
    )

    content += "## 6. 对 similarity_threshold 的观察\n\n"
    for threshold, summary in avg_by_threshold.items():
        content += (
            f"- threshold={threshold}: avg_pass_rate={summary['avg_pass_rate']}，"
            f"avg_no_retrieval={summary['avg_no_retrieval']}，"
            f"avg_retrieval_context_weak={summary['avg_retrieval_context_weak']}。\n"
        )
    content += (
        "- 本轮 threshold=0.30 的平均 pass_rate 最高；threshold=0.35 没有带来 no_retrieval 增加，但 retrieval_context_weak 略高。\n"
        "- 当前更像是上下文噪声与评测关键词严格度共同影响，而不是单纯召回不足。\n\n"
    )

    content += "## 7. Badcase 分析\n\n"
    content += "### 多个组合下都失败\n\n"
    if always_failed:
        content += "\n".join(f"- {item}" for item in always_failed) + "\n\n"
    else:
        content += "- 无。\n\n"

    content += "### 只在某些 threshold 下通过\n\n"
    if threshold_sensitive:
        for item in threshold_sensitive:
            content += f"- {item['case_id']} at top_k={item['top_k']}: {item['statuses']}\n"
        content += "\n"
    else:
        content += "- 无明显 threshold 敏感 case。\n\n"

    content += "### top_k 增大后反而失败\n\n"
    if topk_noise:
        for item in topk_noise:
            content += f"- {item['case_id']} at threshold={item['threshold']}\n"
        content += "\n"
    else:
        content += "- 无明显 top_k 增大退化 case。\n\n"

    content += "## 8. 文件说明\n\n"
    content += (
        "- `runs/heading_topk*_th*/`: 每组 raw result、raw summary、eval_v2 result、eval_v2 summary、eval_v2 badcases。\n"
        "- `grid_compare.md` / `grid_compare.json`: 9 组汇总对比。\n"
        "- `badcases/`: 跨组合 badcase 汇总，包括 always failed、threshold sensitive 和 top_k noise cases。\n"
        "- `archive/`: 本地运行日志目录，日志由 `.gitignore` 忽略，不建议提交。\n"
    )
    (BASE_DIR / "README.md").write_text(content, encoding="utf-8")


def main() -> int:
    rows, results_by_slug = load_runs()
    case_analysis = collect_case_analysis(results_by_slug)
    write_compare(rows, case_analysis)
    write_badcase_reports(case_analysis)
    write_readme(rows, case_analysis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
