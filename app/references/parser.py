from __future__ import annotations

import re
from typing import Any


DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s\]\)]+", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def parse_references(reference_text: str) -> list[dict[str, Any]]:
    entries = split_reference_entries(reference_text)
    return [parse_reference_entry(entry) for entry in entries if entry.strip()]


def split_reference_entries(reference_text: str) -> list[str]:
    text = reference_text.strip()
    if not text:
        return []

    if "@article" in text.lower() or "@inproceedings" in text.lower():
        return re.findall(r"@\w+\s*\{[^@]+", text, flags=re.IGNORECASE | re.DOTALL)

    pattern = re.compile(r"(?m)^\s*(?:\[\d+\]|\d+[\.\)]|[（(]?\d+[）)])\s+")
    matches = list(pattern.finditer(text))
    if len(matches) >= 2:
        entries = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            entries.append(text[start:end].strip())
        return entries

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(paragraphs) > 1:
        return paragraphs
    return [line.strip() for line in text.splitlines() if len(line.strip()) > 20]


def parse_reference_entry(raw_text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^\s*(?:\[\d+\]|\d+[\.\)]|[（(]?\d+[）)])\s*", "", raw_text.strip())
    doi = _first_match(DOI_RE, cleaned)
    url = _first_match(URL_RE, cleaned)
    year = _parse_year(cleaned)
    title = _guess_title(cleaned)
    authors = _guess_authors(cleaned, title)
    venue = _guess_venue(cleaned, title, year)
    confidence = 0.2
    if title:
        confidence += 0.35
    if year:
        confidence += 0.15
    if doi:
        confidence += 0.2
    if authors:
        confidence += 0.1

    return {
        "raw_text": raw_text.strip(),
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "doi": doi.lower(),
        "url": url,
        "confidence_score": min(confidence, 1.0),
    }


def _first_match(pattern: re.Pattern, text: str) -> str:
    match = pattern.search(text)
    return match.group(0).rstrip(".,;") if match else ""


def _parse_year(text: str) -> int | None:
    matches = YEAR_RE.findall(text)
    year_match = re.search(YEAR_RE, text)
    return int(year_match.group(0)) if year_match else None


def _guess_title(text: str) -> str:
    if text.lstrip().startswith("@"):
        title_match = re.search(r"title\s*=\s*[\{\"]([^}\"]+)", text, re.IGNORECASE)
        return " ".join(title_match.group(1).split()) if title_match else ""

    quoted = re.search(r"[“\"]([^”\"]{8,200})[”\"]", text)
    if quoted:
        return " ".join(quoted.group(1).split())

    parts = [part.strip() for part in re.split(r"\.\s+", text) if part.strip()]
    for part in parts[1:4]:
        if 8 <= len(part) <= 220 and not DOI_RE.search(part) and not URL_RE.search(part):
            return " ".join(part.split())
    return ""


def _guess_authors(text: str, title: str) -> list[dict[str, str]]:
    if text.lstrip().startswith("@"):
        author_match = re.search(r"author\s*=\s*[\{\"]([^}\"]+)", text, re.IGNORECASE)
        if author_match:
            return [{"name": name.strip()} for name in author_match.group(1).split(" and ") if name.strip()]

    prefix = text.split(title, 1)[0] if title and title in text else text[:160]
    prefix = re.sub(r"\b(19|20)\d{2}\b.*", "", prefix)
    candidates = re.split(r",|;|\band\b|和|，", prefix)
    authors = []
    for candidate in candidates[:8]:
        name = candidate.strip(" .")
        if 2 <= len(name) <= 80:
            authors.append({"name": name})
    return authors


def _guess_venue(text: str, title: str, year: int | None) -> str:
    if not title or title not in text:
        return ""
    tail = text.split(title, 1)[-1]
    if year and str(year) in tail:
        tail = tail.split(str(year), 1)[0]
    tail = DOI_RE.sub("", tail)
    tail = URL_RE.sub("", tail)
    tail = tail.strip(" .,:;")
    return " ".join(tail.split())[:255]
