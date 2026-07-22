"""Export ViewModel handling document export operations."""

from pathlib import Path

from modules.export.export_service import ExportFormat, ExportService
from PyQt6.QtCore import pyqtSignal
from ui.desktop.viewmodels.base_viewmodel import BaseViewModel


class ExportViewModel(BaseViewModel):
    """ViewModel driving multi-format document exports."""

    export_completed = pyqtSignal(str)

    def __init__(self, export_service: ExportService) -> None:
        """Initialize ExportViewModel.

        Args:
            export_service: ExportService instance.
        """
        super().__init__()
        self._export_service = export_service

    def export(self, meeting_id: str, fmt: str, destination_path: str) -> None:
        """Export meeting data to disk.

        Args:
            meeting_id: Target meeting UUID.
            fmt: Format string ('markdown', 'json', 'pdf', 'docx').
            destination_path: Destination file path.
        """
        self.set_loading(True)
        try:
            target_format = ExportFormat(fmt.lower())
            output = self._export_service.export_meeting(
                meeting_id=meeting_id,
                export_format=target_format,
                output_path=Path(destination_path),
            )
            self.export_completed.emit(str(output))
        except Exception as exc:
            self.error_occurred.emit(f"Export failed: {exc}")
        finally:
            self.set_loading(False)
