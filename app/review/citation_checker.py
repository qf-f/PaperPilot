from __future__ import annotations

import re
from typing import Any

from app.review.issue_schema import ReviewIssue


VALID_CITATION_RE = re.compile(r"\[(\d+)\]")
ABNORMAL_CITATION_RE = re.compile(r"\[([A-Za-z][A-Za-z0-9_-]*)\]")


def extract_citation_numbers(text: str) -> list[int]:
    return [int(match.group(1)) for match in VALID_CITATION_RE.finditer(text or "")]


def check_citations(
    text: str,
    existing_citations: list[dict[str, Any]],
    section_type: str | None = None,
) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    citation_numbers = extract_citation_numbers(text)
    existing_count = len(existing_citations)

    for match in ABNORMAL_CITATION_RE.finditer(text or ""):
        issues.append(
            ReviewIssue(
                issue_type="citation",
                severity="must_fix",
                location="全文引用",
                original_text=match.group(0),
                problem="检测到非数字引用编号，无法对应项目文献库。",
                suggestion="删除该引用，或改为项目文献库中真实存在的数字编号。",
                evidence={"citation": match.group(0)},
            )
        )

    for number in sorted(set(citation_numbers)):
        if number < 1 or number > existing_count:
            issues.append(
                ReviewIssue(
                    issue_type="citation",
                    severity="must_fix",
                    location="全文引用",
                    original_text=f"[{number}]",
                    problem=f"引用 [{number}] 在项目已有文献/参考文献中不存在。",
                    suggestion="删除该引用，或先通过文献检索/参考文献管理补充真实来源后再引用。",
                    evidence={"citation_number": number, "existing_count": existing_count},
                )
            )

    if citation_numbers:
        expected = set(range(1, max(citation_numbers) + 1))
        missing = sorted(expected - set(citation_numbers))
        if missing:
            issues.append(
                ReviewIssue(
                    issue_type="citation",
                    severity="nice_to_have",
                    location="全文引用",
                    problem=f"引用编号存在跳号：缺少 {missing}。",
                    suggestion="检查引用编号是否需要重新排序，或确认是否删除了部分引用。",
                    evidence={"missing_numbers": missing},
                )
            )

    if section_type == "related_work" and len(set(citation_numbers)) < 2:
        issues.append(
            ReviewIssue(
                issue_type="missing_evidence",
                severity="should_fix",
                location="相关工作",
                problem="相关工作部分引用数量过少，难以支撑文献综述。",
                suggestion="补充已检索文献中的代表性工作，并按方法类别组织引用。",
                evidence={"citation_count": len(set(citation_numbers))},
            )
        )

    return issues
