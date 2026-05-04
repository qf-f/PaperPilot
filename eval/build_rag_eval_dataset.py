from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz


# Build a draft RAG evaluation dataset from local PDFs.
#
# Usage:
#     python eval/build_rag_eval_dataset.py --papers-dir paper --output eval/rag_eval_dataset_5papers.draft.jsonl
#
# The script is intentionally conservative. It only uses text extracted from the PDF for draft
# gold_answer values. If a useful section cannot be found, it writes TODO placeholders instead.
# Every row has need_review=true so a human can verify gold_answer and expected_keywords before
# using the dataset for eval/run_rag_eval.py.


DEFAULT_PAPERS_DIR = Path("paper")
DEFAULT_OUTPUT = Path("eval/rag_eval_dataset.draft.jsonl")
TODO_ANSWER = "TODO: 请人工根据论文补充标准答案"
TODO_KEYWORDS = ["TODO"]
UNANSWERABLE_ANSWER = "论文中没有提供该问题的明确依据。"
UNANSWERABLE_KEYWORDS = ["没有提供", "未提到", "无法从论文中得出"]


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


@dataclass(frozen=True)
class SectionSnippet:
    section: str
    page_number: int | None
    text: str


QUESTION_PLAN = [
    {
        "type": "overview",
        "difficulty": "easy",
        "section": "Abstract",
        "question": "这篇论文主要研究什么问题，核心目标是什么？",
    },
    {
        "type": "overview",
        "difficulty": "medium",
        "section": "Introduction",
        "question": "这篇论文的主要贡献或核心思路是什么？",
    },
    {
        "type": "method",
        "difficulty": "medium",
        "section": "Method",
        "question": "论文提出的方法或模型由哪些关键组成部分构成？",
    },
    {
        "type": "method",
        "difficulty": "hard",
        "section": "Method",
        "question": "论文中的关键机制是如何工作的？请概括其实现思路。",
    },
    {
        "type": "experiment",
        "difficulty": "medium",
        "section": "Experiment",
        "question": "论文实验使用了哪些任务、数据集或评测设置？",
    },
    {
        "type": "experiment",
        "difficulty": "medium",
        "section": "Experiment",
        "question": "论文在训练或评估时采用了哪些重要配置？",
    },
    {
        "type": "result",
        "difficulty": "medium",
        "section": "Results",
        "question": "论文报告了哪些主要实验结果？",
    },
    {
        "type": "result",
        "difficulty": "medium",
        "section": "Conclusion",
        "question": "作者根据实验和分析得出了什么结论？",
    },
    {
        "type": "unanswerable",
        "difficulty": "easy",
        "section": "N/A",
        "question": "这篇论文是否给出了系统在真实生产环境连续运行一整年的详细成本明细？",
    },
    {
        "type": "unanswerable",
        "difficulty": "medium",
        "section": "N/A",
        "question": "这篇论文是否提供了每位实验参与者的个人身份信息和联系方式？",
    },
]


SECTION_ALIASES = {
    "Abstract": ["abstract"],
    "Introduction": ["introduction"],
    "Method": [
        "method",
        "methods",
        "methodology",
        "approach",
        "model architecture",
        "model",
        "proposed",
        "algorithm",
    ],
    "Experiment": [
        "experiment",
        "experiments",
        "experimental",
        "evaluation",
        "training data",
        "dataset",
        "datasets",
        "implementation details",
    ],
    "Results": ["results", "result", "analysis", "ablation", "discussion"],
    "Conclusion": ["conclusion", "conclusions", "discussion"],
}


STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "based",
    "been",
    "between",
    "can",
    "for",
    "from",
    "has",
    "have",
    "into",
    "its",
    "more",
    "not",
    "our",
    "paper",
    "results",
    "show",
    "that",
    "the",
    "their",
    "these",
    "this",
    "using",
    "was",
    "were",
    "with",
    "本文",
    "论文",
    "方法",
    "模型",
    "实验",
    "结果",
}


def normalize_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def find_pdfs(papers_dir: Path) -> list[Path]:
    if not papers_dir.exists():
        raise FileNotFoundError(
            f"PDF directory does not exist: {papers_dir}. "
            "默认目录是 paper；也可以通过 --papers-dir 指定目录。"
        )
    if not papers_dir.is_dir():
        raise NotADirectoryError(f"PDF path is not a directory: {papers_dir}")
    return sorted(path for path in papers_dir.glob("*.pdf") if path.is_file())


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def read_pdf_pages(pdf_path: Path) -> tuple[list[PageText], str | None]:
    with fitz.open(pdf_path) as doc:
        metadata_title = (doc.metadata or {}).get("title") or None
        pages = [
            PageText(page_number=index + 1, text=page.get_text("text"))
            for index, page in enumerate(doc)
        ]
    return pages, metadata_title


def is_useful_title(value: str, file_stem: str) -> bool:
    candidate = value.strip()
    lowered = candidate.casefold()
    if len(candidate) < 5:
        return False
    if lowered in {file_stem.casefold(), "untitled", "unknown"}:
        return False
    header_terms = [
        "arxiv",
        "doi:",
        "https://",
        "http://",
        "issn",
        "microsoft word",
        "provided proper attribution",
        "google hereby grants permission",
        "reproduce the tables",
        "scholarly works",
        "published online",
        "received:",
        "accepted:",
        "article citation",
        "文章引用",
        "advances in",
        "应用数学进展",
    ]
    if any(term in lowered for term in header_terms):
        return False
    if re.search(r"\b20\d{2}\b.*\b\d+\(\d+\)", candidate):
        return False
    if "@" in candidate or candidate.lower().startswith("http"):
        return False
    return True


def extract_title(pdf_path: Path, pages: list[PageText], metadata_title: str | None) -> str:
    file_stem = pdf_path.stem
    if metadata_title and is_useful_title(metadata_title, file_stem):
        return metadata_title.strip()

    if not pages:
        return file_stem

    first_page_lines = [
        line.strip()
        for line in pages[0].text.splitlines()
        if line.strip()
    ]
    for line in first_page_lines[:40]:
        if is_useful_title(line, file_stem):
            if len(line.split()) <= 18 and not re.search(r"\b(university|google|department|conference)\b", line, re.I):
                return line
    return file_stem


def find_section_snippet(pages: list[PageText], section: str, max_chars: int = 900) -> SectionSnippet:
    aliases = SECTION_ALIASES.get(section, [section.casefold()])
    for page in pages:
        raw_text = page.text
        lowered = raw_text.casefold()
        for alias in aliases:
            match = re.search(rf"(^|\n|\s)(\d+(\.\d+)?\s*)?{re.escape(alias)}(\s|\n|$)", lowered)
            if match:
                start = max(match.start(), 0)
                snippet = clean_text(raw_text[start : start + max_chars])
                if snippet:
                    return SectionSnippet(section=section, page_number=page.page_number, text=snippet)

    fallback_pages = pages[:2] if section in {"Abstract", "Introduction"} else pages
    for page in fallback_pages:
        snippet = clean_text(page.text[:max_chars])
        if snippet:
            return SectionSnippet(section=section, page_number=page.page_number, text=snippet)

    return SectionSnippet(section=section, page_number=None, text="")


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+", text)
    return [part.strip() for part in parts if len(part.strip()) >= 20]


def build_extract_answer(snippet: SectionSnippet) -> tuple[str, list[str], int | None]:
    if not snippet.text:
        return TODO_ANSWER, TODO_KEYWORDS, None

    sentences = split_sentences(snippet.text)
    answer = " ".join(sentences[:3]).strip() if sentences else snippet.text[:500].strip()
    if len(answer) > 700:
        answer = answer[:700].rsplit(" ", 1)[0].strip()
    if len(answer) < 40:
        return TODO_ANSWER, TODO_KEYWORDS, snippet.page_number

    keywords = extract_keywords(answer)
    if not keywords:
        keywords = TODO_KEYWORDS
    return answer, keywords, snippet.page_number


def extract_keywords(text: str, limit: int = 8) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}|[\u4e00-\u9fff]{2,}", text)
    counts: dict[str, int] = {}
    display: dict[str, str] = {}
    for token in tokens:
        key = token.casefold()
        if key in STOPWORDS or len(key) < 3:
            continue
        counts[key] = counts.get(key, 0) + 1
        display.setdefault(key, token)

    ranked = sorted(counts, key=lambda key: (-counts[key], text.casefold().find(key)))
    return [display[key] for key in ranked[:limit]]


def build_sample(
    paper_id: str,
    paper_title: str,
    question_index: int,
    plan: dict[str, str],
    snippets: dict[str, SectionSnippet],
) -> dict[str, Any]:
    sample_type = plan["type"]
    if sample_type == "unanswerable":
        gold_answer = UNANSWERABLE_ANSWER
        expected_keywords = UNANSWERABLE_KEYWORDS
        expected_page = None
        is_answerable = False
    else:
        snippet = snippets.get(plan["section"], SectionSnippet(plan["section"], None, ""))
        gold_answer, expected_keywords, expected_page = build_extract_answer(snippet)
        is_answerable = True

    return {
        "id": f"{paper_id}_q{question_index:03d}",
        "paper_id": paper_id,
        "paper_title": paper_title,
        "question": plan["question"],
        "gold_answer": gold_answer,
        "expected_keywords": expected_keywords,
        "expected_section": plan["section"],
        "expected_page": expected_page,
        "type": sample_type,
        "difficulty": plan["difficulty"],
        "is_answerable": is_answerable,
        "need_review": True,
    }


def build_samples_for_pdf(pdf_path: Path, paper_index: int) -> list[dict[str, Any]]:
    pages, metadata_title = read_pdf_pages(pdf_path)
    paper_id = f"paper{paper_index:03d}"
    paper_title = extract_title(pdf_path, pages, metadata_title)
    snippets = {
        section: find_section_snippet(pages, section)
        for section in SECTION_ALIASES
    }
    return [
        build_sample(
            paper_id=paper_id,
            paper_title=paper_title,
            question_index=index,
            plan=plan,
            snippets=snippets,
        )
        for index, plan in enumerate(QUESTION_PLAN, start=1)
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a draft RAG evaluation dataset from local PDFs.")
    parser.add_argument("--papers-dir", type=Path, default=DEFAULT_PAPERS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    papers_dir = normalize_path(args.papers_dir)
    output = normalize_path(args.output)

    print(f"Papers dir: {papers_dir}")
    try:
        pdfs = find_pdfs(papers_dir)
    except Exception as exc:
        print(f"build_rag_eval_dataset failed: {exc}", file=sys.stderr)
        return 1

    if not pdfs:
        print(
            f"build_rag_eval_dataset failed: No PDF files found in {papers_dir}. "
            "请确认论文 PDF 已放入该目录，或通过 --papers-dir 指定目录。",
            file=sys.stderr,
        )
        return 1

    all_samples: list[dict[str, Any]] = []
    processed_pdf_count = 0
    skipped_pdf_count = 0
    for paper_index, pdf_path in enumerate(pdfs, start=1):
        try:
            samples = build_samples_for_pdf(pdf_path, paper_index)
        except Exception as exc:
            skipped_pdf_count += 1
            print(f"WARNING: failed to parse {pdf_path.name}: {exc}", file=sys.stderr)
            continue
        processed_pdf_count += 1
        all_samples.extend(samples)
        print(f"{pdf_path.name}: generated {len(samples)} samples")

    if not all_samples:
        print("build_rag_eval_dataset failed: no samples were generated.", file=sys.stderr)
        return 1

    write_jsonl(output, all_samples)
    per_paper_count = len(QUESTION_PLAN)
    print()
    print(f"读取到 PDF: {len(pdfs)} 篇")
    print(f"成功处理 PDF: {processed_pdf_count} 篇")
    if skipped_pdf_count:
        print(f"跳过 PDF: {skipped_pdf_count} 篇")
    print(f"每篇生成问题: {per_paper_count} 条")
    print(f"总样本数: {len(all_samples)} 条")
    print(f"输出文件: {output}")
    print("提醒：所有样本 need_review=true，请人工复核 gold_answer 和 expected_keywords 后再用于正式评测。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
