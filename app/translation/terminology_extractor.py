from __future__ import annotations

import json
import re
from typing import Any

from app.services.llm_service import LLMService
from app.translation.terminology_store import deduplicate_terms, source_key


KNOWN_METRICS = {
    "BLEU",
    "ROUGE",
    "MRR",
    "MAP",
    "NDCG",
    "Recall@K",
    "Precision@K",
    "F1",
    "AUC",
}
KNOWN_ACRONYMS = {"RAG", "LLM", "NLP", "QA", "MARL", "PPO", "DDPG", "DQN", "SFT", "RLHF", "LoRA"}
STOP_PHRASES = {
    "this paper",
    "our method",
    "the proposed",
    "in this",
    "as shown",
    "et al",
}


def extract_candidate_terms(texts: list[str], max_terms: int = 50) -> list[str]:
    joined = "\n".join(text for text in texts if text)
    candidates: list[str] = []

    candidates.extend(re.findall(r"\b[A-Z][A-Z0-9]{1,8}(?:@[A-Z])?\b", joined))
    candidates.extend(re.findall(r"\b[A-Za-z]+(?:-[A-Za-z]+){1,4}\b", joined))
    candidates.extend(re.findall(r"\b(?:Recall|Precision|Hit|NDCG|MAP|MRR)@[0-9Kk]+\b", joined))
    candidates.extend(re.findall(r"\b[A-Z][A-Za-z0-9]+(?:Net|Former|BERT|GPT|Graph|Agent|RAG)\b", joined))

    noun_phrase_pattern = re.compile(
        r"\b(?:[a-z]+(?:al|ive|ed|ing|ion|ment|ity|ic|ical)?\s+){1,3}"
        r"(?:assignment|generation|retrieval|ranking|embedding|alignment|reasoning|planning|search|learning|attention|evaluation|benchmark|dataset|agent|workflow|reranking)\b",
        re.IGNORECASE,
    )
    candidates.extend(match.group(0) for match in noun_phrase_pattern.finditer(joined))
    candidates.extend(term for term in KNOWN_METRICS if term in joined)
    candidates.extend(term for term in KNOWN_ACRONYMS if re.search(rf"\b{re.escape(term)}\b", joined))

    normalized: list[dict[str, Any]] = []
    for candidate in candidates:
        term = re.sub(r"\s+", " ", candidate).strip(" .,;:()[]{}")
        if not _looks_like_term(term):
            continue
        normalized.append(
            {
                "source_term": term,
                "target_term": "",
                "category": _guess_category(term),
                "explanation": "",
                "confidence_score": _rule_confidence(term),
                "source": "extracted",
            }
        )
    return [item["source_term"] for item in deduplicate_terms(normalized)[:max_terms]]


def extract_terms_from_segments(
    segments: list[dict[str, Any]],
    existing_terms: list[dict[str, Any]] | None = None,
    llm_service: LLMService | None = None,
    max_terms: int = 40,
) -> list[dict[str, Any]]:
    existing_keys = {source_key(item.get("source_term", "")) for item in existing_terms or []}
    texts = [segment.get("source_text", "") for segment in segments]
    candidates = [term for term in extract_candidate_terms(texts, max_terms=max_terms) if source_key(term) not in existing_keys]
    if not candidates:
        return []

    llm_terms = _suggest_terms_with_llm(candidates, texts, llm_service) if llm_service else []
    if llm_terms:
        return deduplicate_terms(llm_terms)
    return deduplicate_terms([_fallback_term(term) for term in candidates])


def _suggest_terms_with_llm(candidates: list[str], texts: list[str], llm_service: LLMService | None) -> list[dict[str, Any]]:
    if llm_service is None:
        return []
    sample_text = "\n\n".join(texts)[:8000]
    prompt = json.dumps(
        {
            "candidate_terms": candidates,
            "paper_excerpt": sample_text,
            "output_schema": [
                {
                    "source_term": "English term from candidates",
                    "target_term": "中文译名",
                    "category": "method/model/metric/dataset/task/general",
                    "explanation": "简短解释",
                    "confidence_score": 0.8,
                }
            ],
        },
        ensure_ascii=False,
    )
    try:
        response = llm_service.generate(
            system_prompt=(
                "你是严谨的学术论文术语提取助手。只能基于候选术语和原文片段给出中文译名，"
                "不要新增原文没有出现的术语。输出 JSON 数组，不要输出额外解释。"
            ),
            user_prompt=prompt,
        )
        data = _parse_json_array(response)
        return [item for item in data if item.get("source_term")]
    except Exception:
        return []


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    data = json.loads(cleaned)
    return data if isinstance(data, list) else []


def _fallback_term(term: str) -> dict[str, Any]:
    category = _guess_category(term)
    common_translations = {
        "retrieval-augmented generation": "检索增强生成",
        "credit assignment": "信用分配",
        "large language model": "大语言模型",
        "multi-agent reinforcement learning": "多智能体强化学习",
        "question answering": "问答",
    }
    target = common_translations.get(term.casefold(), term)
    return {
        "source_term": term,
        "target_term": target,
        "category": category,
        "explanation": "基于规则抽取的候选术语，建议人工确认译名。",
        "confidence_score": 0.55 if target == term else 0.75,
        "source": "extracted",
    }


def _looks_like_term(term: str) -> bool:
    lowered = term.casefold()
    if len(term) < 2 or len(term) > 80:
        return False
    if lowered in STOP_PHRASES:
        return False
    if sum(1 for char in term if char.isalpha()) < 2:
        return False
    if len(term.split()) > 5:
        return False
    return True


def _guess_category(term: str) -> str:
    lowered = term.casefold()
    if term in KNOWN_METRICS or "@" in term or any(word in lowered for word in ["score", "accuracy", "recall", "precision", "rouge", "bleu"]):
        return "metric"
    if any(word in lowered for word in ["dataset", "benchmark", "corpus"]):
        return "dataset"
    if any(word in lowered for word in ["model", "bert", "gpt", "network", "net", "former"]):
        return "model"
    if any(word in lowered for word in ["generation", "retrieval", "learning", "assignment", "reranking", "planning", "search"]):
        return "method"
    if any(word in lowered for word in ["task", "question answering", "classification"]):
        return "task"
    return "general"


def _rule_confidence(term: str) -> float:
    if term in KNOWN_ACRONYMS or term in KNOWN_METRICS:
        return 0.8
    if "-" in term or "@" in term:
        return 0.75
    if len(term.split()) >= 2:
        return 0.65
    return 0.55
