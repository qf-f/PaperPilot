from __future__ import annotations

import re

from app.review.issue_schema import ReviewIssue


OVERCLAIM_TERMS = ["显著提升", "大幅降低", "实验表明", "结果证明", "优于所有方法", "明显优于", "取得最佳"]
PERCENT_RE = re.compile(r"(提升|提高|降低|减少)\s*\d+(\.\d+)?\s*%")
DATASET_RE = re.compile(r"(数据集|dataset)\s*[:：]?\s*([A-Za-z0-9_\-]+)", re.IGNORECASE)


def check_experiment_support(text: str, has_real_results: bool = False) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    content = text or ""

    for term in OVERCLAIM_TERMS:
        if term in content and not has_real_results:
            issues.append(
                ReviewIssue(
                    issue_type="overclaim",
                    severity="must_fix",
                    location="实验或结论相关表述",
                    original_text=term,
                    problem="文本使用了强实验结论表达，但当前材料中没有真实实验结果支撑。",
                    suggestion="改为实验设计或预期验证方式，避免写成已完成实验结论。",
                    revised_text="后续将通过对比实验和人工评价验证该模块的有效性。",
                    evidence={"term": term},
                )
            )

    for match in PERCENT_RE.finditer(content):
        issues.append(
            ReviewIssue(
                issue_type="experiment_support",
                severity="must_fix",
                location="实验结果表述",
                original_text=match.group(0),
                problem="出现百分比提升/降低，但未检测到对应实验依据。",
                suggestion="若尚未完成实验，请删除具体百分比；若已完成实验，需要补充数据来源、实验设置和统计方式。",
                evidence={"matched_text": match.group(0)},
            )
        )

    if "baseline" in content.lower() and not any(term in content for term in ["对比方法", "基线", "Baseline", "baseline 包括"]):
        issues.append(
            ReviewIssue(
                issue_type="experiment_support",
                severity="should_fix",
                location="实验方案",
                problem="提到了 baseline，但没有清楚定义对比方法。",
                suggestion="列出 baseline 名称、选择原因和对比维度。",
            )
        )

    return issues
