from __future__ import annotations

from typing import Any


def format_reference(item: dict[str, Any], style: str) -> str:
    if style == "gb_t_7714":
        return format_gb_t_7714(item)
    if style == "ieee":
        return format_ieee(item)
    if style == "apa":
        return format_apa(item)
    if style == "bibtex":
        return format_bibtex(item)
    raise ValueError(f"Unsupported reference style: {style}")


def format_all_styles(item: dict[str, Any]) -> dict[str, str]:
    return {
        "gb_t_7714": format_gb_t_7714(item),
        "ieee": format_ieee(item),
        "apa": format_apa(item),
        "bibtex": format_bibtex(item),
    }


def format_gb_t_7714(item: dict[str, Any]) -> str:
    authors = _authors_text(item)
    title = item.get("title") or item.get("raw_text", "")
    venue = item.get("venue") or ""
    year = item.get("year") or ""
    doi = item.get("doi") or ""
    suffix = f" DOI:{doi}" if doi else ""
    return f"{authors}. {title}[J]. {venue}, {year}.{suffix}".strip()


def format_ieee(item: dict[str, Any]) -> str:
    authors = _authors_text(item)
    title = item.get("title") or item.get("raw_text", "")
    venue = item.get("venue") or ""
    year = item.get("year") or ""
    doi = item.get("doi") or ""
    suffix = f", doi: {doi}" if doi else ""
    return f"{authors}, \"{title},\" {venue}, {year}{suffix}.".strip()


def format_apa(item: dict[str, Any]) -> str:
    authors = _authors_text(item)
    title = item.get("title") or item.get("raw_text", "")
    venue = item.get("venue") or ""
    year = item.get("year") or "n.d."
    doi = item.get("doi") or ""
    suffix = f" https://doi.org/{doi}" if doi else ""
    return f"{authors} ({year}). {title}. {venue}.{suffix}".strip()


def format_bibtex(item: dict[str, Any]) -> str:
    key = item.get("citation_key") or _citation_key(item)
    authors = " and ".join(author.get("name", "") for author in item.get("authors", []) if author.get("name"))
    fields = {
        "title": item.get("title") or item.get("raw_text", ""),
        "author": authors,
        "year": item.get("year") or "",
        "journal": item.get("venue") or "",
        "doi": item.get("doi") or "",
        "url": item.get("url") or "",
    }
    lines = [f"@article{{{key},"]
    for name, value in fields.items():
        if value:
            lines.append(f"  {name} = {{{value}}},")
    lines.append("}")
    return "\n".join(lines)


def _authors_text(item: dict[str, Any]) -> str:
    authors = [author.get("name", "") for author in item.get("authors", []) if author.get("name")]
    return ", ".join(authors) if authors else "Unknown"


def _citation_key(item: dict[str, Any]) -> str:
    first_author = "ref"
    if item.get("authors"):
        first_author = item["authors"][0].get("name", "ref").split()[-1].lower()
    return f"{first_author}{item.get('year') or ''}"
