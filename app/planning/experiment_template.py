from __future__ import annotations


def default_experiment_plan(topic: str) -> dict:
    return {
        "experiment_goals": [
            "验证系统在论文阅读、问答、总结、文献管理和写作规划流程中的有效性",
            "验证 RAG 引用溯源对回答可信性的提升",
            "验证 Agent 工作流对论文写作任务拆解的帮助",
        ],
        "datasets_or_testsets": [
            "自建论文项目测试集：包含不同领域 PDF/DOCX/TXT/Markdown 文档",
            "人工标注问答集：围绕方法、实验、结论、局限性构造问题",
            "写作任务样例集：选题规划、文献综述素材、章节草稿生成任务",
        ],
        "baselines": [
            "普通 LLM 直接问答",
            "无 metadata filter 的 RAG 问答",
            "无 Agent 工作流的单轮生成方式",
        ],
        "metrics": [
            "答案引用准确率",
            "上下文命中率",
            "无依据回答拒答率",
            "总结结构完整性",
            "人工可用性评分",
            "接口响应时间",
        ],
        "ablation": [
            "去除 rerank 或相似度阈值控制",
            "去除项目级 metadata filter",
            "去除章节分组总结流程",
            "去除引用校验策略",
        ],
        "note": f"上述实验设计用于支撑题目“{topic}”，不能直接写成已完成实验结果。",
    }
