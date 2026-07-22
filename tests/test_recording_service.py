"""Unit test suite for RecordingService."""

from app.container import ApplicationContainer
from modules.recording.service import RecordingService
from modules.storage.db import DatabaseEngine


def test_recording_service_lifecycle():
    """RecordingService handles start and stop recording lifecycle."""
    container = ApplicationContainer()
    container._db_engine = DatabaseEngine(db_url="sqlite:///:memory:")
    container.initialize()

    rec_service = RecordingService(container=container)
    assert rec_service.is_recording is False
    assert rec_service.active_meeting_id is None

    mid = rec_service.start_recording("Unit Test Recording")
    assert rec_service.is_recording is True
    assert rec_service.active_meeting_id == mid

    stopped_id = rec_service.stop_recording()
    assert stopped_id == mid
    assert rec_service.is_recording is False

    container.shutdown()
