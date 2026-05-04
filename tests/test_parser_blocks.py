from pathlib import Path

from app.rag import parser


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self, mode: str) -> str:
        assert mode == "text"
        return self._text


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self._pages = pages

    def __enter__(self):
        return self._pages

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_pdf_parser_detects_conclusion_and_references(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    fake_pdf = _FakePdf(
        [
            _FakePage(
                "\n".join(
                    [
                        "1 引言",
                        "本文介绍研究背景。",
                        "",
                        "5 结论",
                        "本文总结主要发现。",
                        "",
                        "参考文献",
                        "[1] Some reference.",
                    ]
                )
            )
        ]
    )

    monkeypatch.setattr(parser.fitz, "open", lambda path: fake_pdf)

    blocks = parser.parse_pdf(pdf_path)

    conclusion_blocks = [block for block in blocks if block.get("section_title") == "结论"]
    reference_blocks = [block for block in blocks if block.get("section_title") == "参考文献"]
    assert conclusion_blocks
    assert conclusion_blocks[0]["block_type"] == "text"
    assert conclusion_blocks[0]["section_path"] == ["结论"]
    assert reference_blocks
    assert all(block["is_reference_section"] is True for block in reference_blocks)


def test_markdown_parser_tracks_heading_levels_and_section_path(tmp_path: Path):
    md_path = tmp_path / "paper.md"
    md_path.write_text(
        "# Introduction\nIntro text.\n## Method\nMethod text.\n### Details\nDetail text.\n",
        encoding="utf-8",
    )

    blocks = parser.parse_markdown(md_path)

    assert blocks[0]["section_title"] == "Introduction"
    assert blocks[0]["heading_level"] == 1
    assert blocks[0]["section_path"] == ["Introduction"]
    assert blocks[1]["section_title"] == "Method"
    assert blocks[1]["heading_level"] == 2
    assert blocks[1]["section_path"] == ["Introduction", "Method"]
    assert blocks[2]["section_title"] == "Details"
    assert blocks[2]["heading_level"] == 3
    assert blocks[2]["section_path"] == ["Introduction", "Method", "Details"]


def test_txt_parser_adds_block_type_and_paragraph_index(tmp_path: Path):
    txt_path = tmp_path / "paper.txt"
    txt_path.write_text("第一段。\n\n第二段。", encoding="utf-8")

    blocks = parser.parse_txt(txt_path)

    assert blocks == [
        {
            "page_number": 1,
            "section_title": "",
            "section_path": [],
            "block_type": "text",
            "heading_level": None,
            "paragraph_index": 0,
            "char_start": 0,
            "char_end": 10,
            "is_reference_section": False,
            "text": "第一段。\n\n第二段。",
        }
    ]
