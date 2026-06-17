from eval.recompute_rag_eval_v2 import evaluate_sample_v2


def test_no_answer_accepts_expanded_refusal_phrases_without_context_keyword_match():
    sample = {
        "id": "paper001_q010",
        "is_answerable": False,
        "expected_keywords": ["没有提供", "未提到", "无法从论文中得出"],
    }
    answer = "否，论文没有提供实验参与者的个人身份信息和联系方式，也不涉及人类受试者。"

    result = evaluate_sample_v2(
        sample=sample,
        answer=answer,
        retrieved_chunks=[
            {
                "text_preview": "极小k-可扩二部图，极小k-强连通图，次模性，最小度",
                "score": 0.42,
            }
        ],
    )

    assert result["pass"] is True
    assert result["relaxed_pass"] is True
    assert result["fail_reason"] is None


def test_expected_keyword_groups_count_synonym_groups_for_answerable_samples():
    sample = {
        "id": "grouped",
        "is_answerable": True,
        "expected_keywords": ["实验参与者"],
        "expected_keyword_groups": [
            ["实验参与者", "受试者", "参与者"],
            ["没有提供", "未提供", "没有说明"],
        ],
    }
    answer = "文中未提供受试者的联系方式。"

    result = evaluate_sample_v2(
        sample=sample,
        answer=answer,
        retrieved_chunks=[{"text_preview": "受试者 联系方式 未提供", "score": 0.9}],
        min_keyword_hit_rate=0.5,
    )

    assert result["keyword_hit_count"] == 2
    assert result["keyword_hit_rate"] == 1.0
    assert result["keyword_hits"] == ["实验参与者|受试者|参与者", "没有提供|未提供|没有说明"]
    assert result["pass"] is True


def test_answerable_samples_still_use_context_keywords_for_retrieval_weakness():
    sample = {
        "id": "paper003_q007",
        "is_answerable": True,
        "expected_keywords": ["平均准确率", "5.24%", "运行时间"],
    }
    answer = "论文报告模型具有较好分类性能。"

    result = evaluate_sample_v2(
        sample=sample,
        answer=answer,
        retrieved_chunks=[{"text_preview": "训练集包含1440首歌曲，测试集包含360首。", "score": 0.44}],
        min_keyword_hit_rate=0.5,
    )

    assert result["pass"] is False
    assert result["fail_reason"] == "retrieval_context_weak"
