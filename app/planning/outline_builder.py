from __future__ import annotations


def default_outline_for_paper_type(paper_type: str) -> list[dict]:
    if paper_type == "proposal":
        return [
            {"chapter": "一、选题背景与研究意义", "sections": ["研究背景", "研究意义", "国内外研究现状"]},
            {"chapter": "二、研究内容与研究目标", "sections": ["研究问题", "研究目标", "研究内容"]},
            {"chapter": "三、技术路线与研究方法", "sections": ["总体技术路线", "关键方法", "可行性分析"]},
            {"chapter": "四、实验方案与预期成果", "sections": ["实验设计", "评价指标", "预期成果"]},
            {"chapter": "五、进度安排与风险控制", "sections": ["进度计划", "风险分析"]},
        ]
    if paper_type in {"journal_paper", "conference_paper", "small_paper"}:
        return [
            {"chapter": "1 Introduction", "sections": ["Background", "Problem", "Contributions"]},
            {"chapter": "2 Related Work", "sections": ["RAG", "Agent Workflow", "Academic Writing Assistance"]},
            {"chapter": "3 Method", "sections": ["Framework", "Retrieval", "Agent Orchestration"]},
            {"chapter": "4 Experiments", "sections": ["Settings", "Baselines", "Metrics", "Results Analysis"]},
            {"chapter": "5 Conclusion", "sections": ["Summary", "Limitations", "Future Work"]},
        ]
    return [
        {"chapter": "第 1 章 绪论", "sections": ["研究背景", "研究意义", "国内外研究现状", "本文主要工作"]},
        {"chapter": "第 2 章 相关技术与研究现状", "sections": ["RAG 技术", "Agent 编排", "论文写作辅助系统"]},
        {"chapter": "第 3 章 系统需求分析", "sections": ["功能需求", "非功能需求", "业务流程分析"]},
        {"chapter": "第 4 章 系统设计", "sections": ["总体架构", "数据库设计", "Agent 工作流设计", "RAG 知识库设计"]},
        {"chapter": "第 5 章 核心模块实现", "sections": ["文档解析", "向量检索", "论文总结", "文献管理", "写作辅助"]},
        {"chapter": "第 6 章 实验与结果分析", "sections": ["实验目标", "测试集构建", "对比实验", "消融实验", "系统性能测试"]},
        {"chapter": "第 7 章 总结与展望", "sections": ["工作总结", "不足分析", "未来工作"]},
    ]
