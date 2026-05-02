from __future__ import annotations

from collections import Counter

from app.review.issue_schema import ReviewIssue


AI_STYLE_PHRASES = [
    "随着人工智能技术的快速发展",
    "具有重要意义",
    "具有广阔应用前景",
    "极大提高效率",
    "有效提升性能",
    "本文提出一种新方法",
    "国内外学者进行了大量研究",
    "综上所述",
]


def check_writing_style(text: str) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    content = text or ""

    for phrase in AI_STYLE_PHRASES:
        if phrase in content:
            issues.append(
                ReviewIssue(
                    issue_type="ai_style",
                    severity="should_fix",
                    location="写作表达",
                    original_text=phrase,
                    problem="该表达较模板化，容易呈现 AI 味或空泛表达。",
                    suggestion="改为描述具体研究对象、具体问题和具体技术路径。",
                    revised_text="可改为围绕具体场景说明：现有论文写作辅助工具在引用溯源、项目级知识隔离和多步骤写作流程管理方面仍存在不足。",
                    evidence={"phrase": phrase},
                )
            )

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    for index, paragraph in enumerate(paragraphs, start=1):
        if len(paragraph) > 700:
            issues.append(
                ReviewIssue(
                    issue_type="writing_quality",
                    severity="nice_to_have",
                    location=f"第 {index} 段",
                    problem="段落过长，影响阅读和论证层次。",
                    suggestion="拆分为背景、问题、方法或结论等更清晰的小段。",
                    evidence={"length": len(paragraph)},
                )
            )

    first_words = [p[:12] for p in paragraphs if len(p) >= 12]
    repeated = [text for text, count in Counter(first_words).items() if count >= 3]
    for prefix in repeated:
        issues.append(
            ReviewIssue(
                issue_type="writing_quality",
                severity="nice_to_have",
                location="段落开头",
                original_text=prefix,
                problem="多个段落开头句式重复。",
                suggestion="调整段落开头，让论证关系更自然，例如使用问题导向、方法导向或对比导向展开。",
            )
        )

    return issues
