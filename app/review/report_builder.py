from __future__ import annotations

from typing import Any

from app.review.issue_schema import ReviewIssue


def calculate_score(issues: list[ReviewIssue], content_length: int) -> int:
    score = 100
    for issue in issues:
        if issue.severity == "must_fix":
            score -= 12
        elif issue.severity == "should_fix":
            score -= 6
        else:
            score -= 2
    score = max(score, 30)
    if content_length < 200:
        score = min(score, 50)
    return min(max(score, 0), 100)


def build_review_report(
    issues: list[ReviewIssue],
    target_info: dict[str, Any],
    strengths: list[str] | None = None,
    risks: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    strengths = strengths or _infer_strengths(issues)
    risks = risks or _infer_risks(issues)
    next_actions = next_actions or _infer_next_actions(issues)
    score = calculate_score(issues, content_length=target_info.get("content_length", 0))

    issue_dicts = [issue.model_dump() for issue in issues]
    summary = _summary(score, issues)

    lines = [
        "# 论文质量审查报告",
        "",
        f"- 审查对象：{target_info.get('target_title') or target_info.get('target_id')}",
        f"- 审查类型：{target_info.get('review_type')}",
        f"- 完成度风险评分：{score}/100",
        "",
        "## 总体评价",
        summary,
        "",
        "## 优点",
        *[f"- {item}" for item in strengths],
        "",
        "## 必须修改",
        *_format_issues([issue for issue in issues if issue.severity == "must_fix"]),
        "",
        "## 建议修改",
        *_format_issues([issue for issue in issues if issue.severity == "should_fix"]),
        "",
        "## 可选优化",
        *_format_issues([issue for issue in issues if issue.severity == "nice_to_have"]),
        "",
        "## 风险",
        *[f"- {item}" for item in risks],
        "",
        "## 下一步行动",
        *[f"- {item}" for item in next_actions],
    ]

    review_json = {
        "review_type": target_info.get("review_type"),
        "target_type": target_info.get("target_type"),
        "target_id": target_info.get("target_id"),
        "target_title": target_info.get("target_title"),
        "summary": summary,
        "score": score,
        "issues": issue_dicts,
        "strengths": strengths,
        "risks": risks,
        "next_actions": next_actions,
        "target_info": target_info,
    }
    return "\n".join(lines), review_json


def _format_issues(issues: list[ReviewIssue]) -> list[str]:
    if not issues:
        return ["- 暂未发现。"]
    lines = []
    for index, issue in enumerate(issues, start=1):
        lines.append(f"{index}. **{issue.location or issue.issue_type}**：{issue.problem}")
        lines.append(f"   - 建议：{issue.suggestion}")
        if issue.revised_text:
            lines.append(f"   - 可替换写法：{issue.revised_text}")
    return lines


def _summary(score: int, issues: list[ReviewIssue]) -> str:
    must = sum(1 for issue in issues if issue.severity == "must_fix")
    should = sum(1 for issue in issues if issue.severity == "should_fix")
    if must:
        return f"当前材料存在 {must} 个必须修改问题和 {should} 个建议修改问题，建议先修复引用、实验支撑和结论夸大等高风险内容。"
    if should:
        return f"当前材料主体可继续推进，但仍有 {should} 个建议修改问题，需要增强依据、结构或表达质量。"
    return "当前材料风险较低，可继续在细节表达、引用完整性和实验说明上打磨。"


def _infer_strengths(issues: list[ReviewIssue]) -> list[str]:
    if not issues:
        return ["结构和引用风险较低", "当前文本可以作为后续修改基础"]
    return ["已形成可审查的文本基础", "部分问题可以通过补充依据和调整表达解决"]


def _infer_risks(issues: list[ReviewIssue]) -> list[str]:
    risks = []
    if any(issue.issue_type == "citation" for issue in issues):
        risks.append("引用不可追溯会影响相关工作可信度。")
    if any(issue.issue_type in {"experiment_support", "overclaim"} for issue in issues):
        risks.append("实验支撑不足会削弱创新点和结论的成立性。")
    if any(issue.issue_type == "ai_style" for issue in issues):
        risks.append("模板化表达会降低论文写作的专业感。")
    return risks or ["暂无明显高风险，但仍需结合导师意见继续修改。"]


def _infer_next_actions(issues: list[ReviewIssue]) -> list[str]:
    actions = []
    if any(issue.issue_type == "citation" for issue in issues):
        actions.append("核对所有引用编号，并从项目文献库中选择真实来源替换。")
    if any(issue.issue_type in {"experiment_support", "overclaim"} for issue in issues):
        actions.append("把实验结果式表述改为实验设计或补充真实实验数据。")
    if any(issue.issue_type in {"writing_quality", "ai_style"} for issue in issues):
        actions.append("重写模板化段落，增加具体研究对象、技术路径和评价指标。")
    return actions or ["继续补充文献依据、实验方案和章节细节。"]
