"""Unit test suite for ViewModels and reactive UI state management."""

import pytest
from core.settings_service import SettingsService
from modules.storage.db import DatabaseEngine
from modules.storage.repositories import MeetingRepository
from PyQt6.QtWidgets import QApplication
from ui.desktop.viewmodels.dashboard_viewmodel import DashboardViewModel
from ui.desktop.viewmodels.library_viewmodel import LibraryViewModel
from ui.desktop.viewmodels.settings_viewmodel import SettingsViewModel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def memory_db():
    db = DatabaseEngine(db_url="sqlite:///:memory:")
    db.init_db()
    return db


def test_dashboard_viewmodel(qapp, memory_db):
    """DashboardViewModel loads statistics and recent meetings."""
    with memory_db.session_scope() as session:
        MeetingRepository.create(session, "Demo Sync 1")
        MeetingRepository.create(session, "Demo Sync 2")

    vm = DashboardViewModel(db_engine=memory_db)
    vm.refresh()

    assert len(vm.recent_meetings) == 2
    assert vm.stats["total_meetings"] == 2


def test_library_viewmodel_filter_and_delete(qapp, memory_db):
    """LibraryViewModel loads, filters, and deletes meetings."""
    with memory_db.session_scope() as session:
        m1 = MeetingRepository.create(session, "Architecture Sync")
        MeetingRepository.create(session, "Marketing Huddle")
        m1_id = m1.id

    vm = LibraryViewModel(db_engine=memory_db)
    vm.load_meetings()
    assert len(vm.meetings) == 2

    # Filter
    vm.load_meetings("Architecture")
    assert len(vm.meetings) == 1
    assert vm.meetings[0]["title"] == "Architecture Sync"

    # Delete
    vm.delete_meeting(m1_id)
    vm.load_meetings()
    assert len(vm.meetings) == 1
    assert vm.meetings[0]["title"] == "Marketing Huddle"


def test_settings_viewmodel(qapp, tmp_path):
    """SettingsViewModel updates preferences via SettingsService."""
    config_file = tmp_path / "test_settings_vm.json"
    settings_service = SettingsService(config_path=config_file)
    vm = SettingsViewModel(settings_service=settings_service)

    settings = vm.settings
    settings.appearance.theme = "light"
    vm.save_settings(settings)

    assert settings_service.settings.appearance.theme == "light"
