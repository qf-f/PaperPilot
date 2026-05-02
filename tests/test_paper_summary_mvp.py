from pathlib import Path

from app.db.models.generated_output import GeneratedOutput
from app.exporters.markdown_exporter import export_markdown
from app.exporters.word_exporter import export_word_from_markdown
from app.paper.section_detector import group_chunks_by_section
from app.schemas.paper_summary_schema import PaperSummaryRequest


def test_section_detector_recognizes_common_sections():
    groups = group_chunks_by_section(
        [
            {"section_title": "Abstract", "content": "This paper proposes...", "chunk_index": 0},
            {"section_title": "方法", "content": "本文方法包括...", "chunk_index": 1},
            {"section_title": "Experiments", "content": "We evaluate...", "chunk_index": 2},
        ]
    )

    names = [group["section_name"] for group in groups]
    assert "Abstract" in names
    assert "Method" in names
    assert "Experiment" in names


def test_generated_output_model_can_represent_paper_summary():
    output = GeneratedOutput(
        output_type="paper_summary",
        title="论文总结",
        content_markdown="# 论文总结",
        content_json={"problem": "原文中未找到明确依据"},
        citations=[],
        status="finished",
    )

    assert output.output_type == "paper_summary"
    assert output.status == "finished"


def test_paper_summary_request_validation_accepts_standard():
    request = PaperSummaryRequest(
        project_id="00000000-0000-0000-0000-000000000001",
        document_id="00000000-0000-0000-0000-000000000002",
        user_id="demo-user",
        summary_type="standard",
    )

    assert request.summary_type == "standard"


def test_markdown_export(tmp_path: Path):
    file_path = tmp_path / "summary.md"
    result = export_markdown("# 论文总结\n\n内容", str(file_path))

    assert Path(result).exists()
    assert Path(result).read_text(encoding="utf-8").startswith("# 论文总结")


def test_word_export_file_generation(tmp_path: Path):
    file_path = tmp_path / "summary.docx"
    result = export_word_from_markdown(
        markdown_content="# 论文总结\n\n## 核心方法\n\n- 方法要点",
        file_path=str(file_path),
        title="测试导出",
    )

    assert Path(result).exists()
    assert Path(result).suffix == ".docx"


def test_document_without_chunks_expected_error_message():
    expected = "Document has no chunks"
    assert expected in "Document has no chunks. Please re-parse this document."
