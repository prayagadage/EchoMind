"""Executable demonstration script for Phase 11 Desktop User Experience.

Demonstrates ApplicationContainer, seeding meeting data, ViewModels,
Desktop UI Views, document export (Markdown/JSON/PDF/DOCX),
and macOS System Tray integration.
"""

import sys
from pathlib import Path

from app.container import ApplicationContainer
from loguru import logger
from modules.export.export_service import ExportFormat
from modules.meeting_intelligence.models import IntelligenceItemModel, ItemType
from modules.meeting_intelligence.repository import IntelligenceRepository
from modules.storage.models import SpeakerModel, TranscriptModel
from modules.storage.repositories import (
    MeetingRepository,
    SpeakerRepository,
    TranscriptRepository,
)
from modules.summary.models import MeetingSummaryModel, SummaryType
from modules.summary.repository import SummaryRepository


def run_demo() -> None:
    """Execute Desktop UI demonstration runner."""
    logger.info("=" * 60)
    logger.info("EchoMind Phase 11: Desktop UI & macOS Integration Demo")
    logger.info("=" * 60)

    # 1. Initialize Container with in-memory database for demo
    from modules.storage.db import DatabaseEngine

    container = ApplicationContainer()
    container._db_engine = DatabaseEngine(db_url="sqlite:///:memory:")
    container.initialize()

    # 2. Seed Mock Meeting Data
    logger.info("\n1. Seeding Mock Meeting Data...")
    with container.db_engine.session_scope() as session:
        m = MeetingRepository.create(session, "EchoMind Phase 11 UI Launch Sync")
        mid = m.id

        spk = SpeakerModel(
            meeting_id=mid,
            temporary_name="Speaker A",
            display_name="Prayag",
            color="#4F46E5",
        )
        SpeakerRepository.create(session, spk)

        t1 = TranscriptModel(
            meeting_id=mid,
            sequence_number=1,
            timestamp=0.0,
            language="en",
            original_text="Completed MVVM Desktop UI architecture for macOS.",
            speaker_id=spk.id,
        )
        TranscriptRepository.add(session, t1)

        summary = MeetingSummaryModel(
            meeting_id=mid,
            summary_type=SummaryType.COMBINED.value,
            executive_summary="Team launched EchoMind desktop UI shell.",
            key_takeaways='["MVVM keeps UI decoupled from database & AI"]',
            is_final=1,
        )
        SummaryRepository.create(session, summary)

        item = IntelligenceItemModel(
            meeting_id=mid,
            item_type=ItemType.ACTION_ITEM.value,
            content="Run full desktop UI test suite",
            content_hash="h_ui_test",
            assignee="Prayag",
            due_date="2026-07-25",
        )
        IntelligenceRepository.create(session, item)

    logger.info(f"   Seeded Meeting ID: {mid[:8]} ('EchoMind Phase 11 UI Launch Sync')")

    # 3. Test Multi-Format Document Export
    logger.info("\n2. Testing Multi-Format Document Export Service:")
    export_dir = Path.home() / ".gemini" / "antigravity-ide" / "exports_demo"
    export_dir.mkdir(parents=True, exist_ok=True)

    formats = [
        ExportFormat.MARKDOWN,
        ExportFormat.JSON,
        ExportFormat.PDF,
        ExportFormat.DOCX,
    ]
    for fmt in formats:
        ext = fmt.value if fmt != ExportFormat.MARKDOWN else "md"
        out_file = export_dir / f"demo_meeting.{ext}"
        out_path = container.export_service.export_meeting(
            meeting_id=mid, export_format=fmt, output_path=out_file
        )
        logger.info(f"   • Exported [{fmt.value.upper()}] -> {out_path}")

    # 4. Test Settings Persistence
    logger.info("\n3. Testing SettingsService Persistence:")
    settings = container.settings_service.settings
    logger.info(f"   Current Theme: {settings.appearance.theme}")
    logger.info(f"   Audio VAD Threshold: {settings.audio.vad_energy_threshold}")
    settings.appearance.theme = "dark"
    container.settings_service.update_settings(settings)
    logger.info("   Persisted Settings Updated successfully.")

    # 5. Initialize Desktop Qt Application Shell (offscreen test check)
    logger.info("\n4. Initializing Desktop Qt Application & ViewModels:")
    from PyQt6.QtWidgets import QApplication
    from ui.desktop.main_window import MainWindow

    _app = QApplication.instance() or QApplication(sys.argv)
    _window = MainWindow(container)
    logger.info("   MainWindow, ViewModels, and macOS MenuBarTrayApp initialized!")

    container.shutdown()

    logger.info("=" * 60)
    logger.info("Phase 11 Demo completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_demo()
