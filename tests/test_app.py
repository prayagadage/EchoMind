"""Unit tests for application entry point and container lifespan."""

from app.container import ApplicationContainer
from app.main import main
from core.config import Settings


def test_application_container_lifespan(mock_settings: Settings) -> None:
    """Verify container initialization and graceful shutdown."""
    container = ApplicationContainer(settings=mock_settings)
    assert not container.is_initialized

    container.initialize()
    assert container.is_initialized

    container.shutdown()
    assert not container.is_initialized


def test_app_main_success_exit(mock_settings: Settings) -> None:
    """Verify main entry point completes with exit code 0."""
    result = main()
    assert result == 0
