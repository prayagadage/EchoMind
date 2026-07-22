"""Unit test suite for ExportService and multi-format document generators."""

import pytest
from modules.export.export_service import ExportFormat, ExportService
from modules.meeting_intelligence.models import IntelligenceItemModel, ItemType
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.db import DatabaseEngine
from modules.storage.models import TranscriptModel
from modules.storage.repositories import MeetingRepository, TranscriptRepository
from modules.summary.models import MeetingSummaryModel, SummaryType
from modules.summary.repository import SummaryRepository


@pytest.fixture
def memory_db():
    db = DatabaseEngine(db_url="sqlite:///:memory:")
    db.init_db()
    return db


def test_export_service_gather_and_export_all_formats(memory_db, tmp_path):
    """ExportService exports meeting to Markdown, JSON, PDF, and DOCX files."""
    export_service = ExportService(db_engine=memory_db)

    # Seed test meeting
    with memory_db.session_scope() as session:
        m = MeetingRepository.create(session, "Quarterly Strategy Sync")
        mid = m.id

        t = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="We will launch the new product in October.",
        )
        TranscriptRepository.add(session, t)

        s = MeetingSummaryModel(
            meeting_id=mid,
            summary_type=SummaryType.COMBINED.value,
            executive_summary="Team aligned on Q4 product launch timeline.",
            key_takeaways='["Launch scheduled for October"]',
            is_final=1,
        )
        SummaryRepository.create(session, s)

        item = IntelligenceItemModel(
            meeting_id=mid,
            item_type=ItemType.ACTION_ITEM.value,
            content="Finalize marketing plan",
            content_hash="h1_marketing",
            assignee="Priya",
            due_date="2026-09-01",
        )
        IntelligenceRepository.create(session, item)

    # 1. Export Markdown
    md_file = tmp_path / "meeting.md"
    out_md = export_service.export_meeting(mid, ExportFormat.MARKDOWN, md_file)
    assert out_md.exists()
    md_content = out_md.read_text(encoding="utf-8")
    assert "# Quarterly Strategy Sync" in md_content
    assert "Finalize marketing plan" in md_content

    # 2. Export JSON
    json_file = tmp_path / "meeting.json"
    out_json = export_service.export_meeting(mid, ExportFormat.JSON, json_file)
    assert out_json.exists()
    json_content = out_json.read_text(encoding="utf-8")
    assert "Quarterly Strategy Sync" in json_content

    # 3. Export PDF
    pdf_file = tmp_path / "meeting.pdf"
    out_pdf = export_service.export_meeting(mid, ExportFormat.PDF, pdf_file)
    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 0

    # 4. Export DOCX
    docx_file = tmp_path / "meeting.docx"
    out_docx = export_service.export_meeting(mid, ExportFormat.DOCX, docx_file)
    assert out_docx.exists()
    assert out_docx.stat().st_size > 0
