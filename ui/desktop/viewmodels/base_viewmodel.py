"""Base ViewModel class providing Qt signal dispatching and loading state management."""

from collections.abc import Callable
from typing import Any

from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal


class BaseViewModel(QObject):
    """Base Qt ViewModel handling properties, loading state, and error signals."""

    error_occurred = pyqtSignal(str)
    loading_changed = pyqtSignal(bool)
    data_updated = pyqtSignal()

    def __init__(self) -> None:
        """Initialize BaseViewModel."""
        super().__init__()
        self._is_loading: bool = False

    @property
    def is_loading(self) -> bool:
        """Get current loading status flag."""
        return self._is_loading

    def set_loading(self, value: bool) -> None:
        """Set loading flag and emit signal.

        Args:
            value: True if loading operation is active.
        """
        if self._is_loading != value:
            self._is_loading = value
            self.loading_changed.emit(value)

    def execute_async_action(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """Run a synchronous action safely and emit error signal if exception occurs.

        Args:
            func: Target callable.
            args: Positional arguments.
            kwargs: Keyword arguments.
        """
        self.set_loading(True)
        try:
            func(*args, **kwargs)
            self.data_updated.emit()
        except Exception as exc:
            logger.error(f"ViewModel action error in {self.__class__.__name__}: {exc}")
            self.error_occurred.emit(str(exc))
        finally:
            self.set_loading(False)
