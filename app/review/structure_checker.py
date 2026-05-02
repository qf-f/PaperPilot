from __future__ import annotations

from typing import Any

from app.review.issue_schema import ReviewIssue


REQUIRED_THESIS_HEADINGS = ["绪论", "相关", "设计", "实验", "总结"]


def check_structure(target_content: str, target_json: dict[str, Any] | None = None, output_type: str | None = None) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    data = target_json or {}
    text = target_content or ""

    if output_type == "topic_plan" or data.get("topic_analysis"):
        if not data.get("research_questions"):
            issues.append(_missing("structure", "研究问题", "规划中缺少明确研究问题。", "补充 RQ1-RQ3，并让每个问题对应研究内容。"))
        if not data.get("innovations"):
            issues.append(_missing("structure", "创新点", "规划中缺少创新点。", "补充可验证的创新点，避免只罗列系统功能。"))
        if not data.get("experiment_plan"):
            issues.append(_missing("experiment_support", "实验方案", "规划中缺少实验方案。", "为每个创新点设计评价指标、baseline 和消融实验。"))
        else:
            _check_innovation_experiment_alignment(data, issues)

    if output_type == "section_draft":
        section_type = data.get("section_type")
        if section_type == "related_work" and "[1]" not in text:
            issues.append(
                ReviewIssue(
                    issue_type="missing_evidence",
                    severity="should_fix",
                    location="相关工作",
                    problem="相关工作草稿缺少明确引用支撑。",
                    suggestion="基于已保存文献按类别补充引用，而不是泛泛描述研究现状。",
                )
            )
        if section_type == "experiment" and "实验结果" in text and "预期" not in text:
            issues.append(
                ReviewIssue(
                    issue_type="overclaim",
                    severity="must_fix",
                    location="实验章节",
                    problem="实验草稿可能把实验设计写成了已完成结果。",
                    suggestion="未完成实验时，只能写实验目标、设置、指标和预期分析方式。",
                )
            )

    if len(text.strip()) < 200:
        issues.append(
            ReviewIssue(
                issue_type="structure",
                severity="should_fix",
                location="全文",
                problem="目标文本过短，无法充分审查论文结构和论证质量。",
                suggestion="补充研究背景、方法、实验或结论等必要内容后再审查。",
            )
        )

    return issues


def check_uploaded_document_structure(text: str) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    missing = [heading for heading in REQUIRED_THESIS_HEADINGS if heading not in text]
    if missing:
        issues.append(
            ReviewIssue(
                issue_type="structure",
                severity="should_fix",
                location="全文结构",
                problem=f"上传论文初稿可能缺少必要章节线索：{missing}。",
                suggestion="检查论文是否包含绪论、相关工作、系统/方法设计、实验分析、总结展望等基本部分。",
                evidence={"missing_headings": missing},
            )
        )
    return issues


def _missing(issue_type: str, location: str, problem: str, suggestion: str) -> ReviewIssue:
    return ReviewIssue(issue_type=issue_type, severity="must_fix", location=location, problem=problem, suggestion=suggestion)


def _check_innovation_experiment_alignment(data: dict[str, Any], issues: list[ReviewIssue]) -> None:
    innovations = data.get("innovations") or []
    experiment_text = str(data.get("experiment_plan") or "")
    for innovation in innovations:
        name = innovation.get("name") if isinstance(innovation, dict) else str(innovation)
        if name and name[:6] not in experiment_text and "validation" not in innovation:
            issues.append(
                ReviewIssue(
                    issue_type="experiment_support",
                    severity="should_fix",
                    location="创新点与实验方案",
                    problem=f"创新点“{name}”缺少明确实验验证方式。",
                    suggestion="为该创新点补充对应实验、指标或消融设计。",
                    evidence={"innovation": innovation},
                )
            )
