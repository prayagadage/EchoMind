"""macOS desktop Notification and sound alert service."""

import os
import platform
import subprocess
import threading

from loguru import logger


class NotificationService:
    """Service rendering native macOS system notifications and audio alert chimes."""

    def __init__(self, play_sound_enabled: bool = True) -> None:
        """Initialize NotificationService instance.

        Args:
            play_sound_enabled: True to play sound chimes for high severity.
        """
        self._play_sound_enabled = play_sound_enabled
        self._is_macos = platform.system() == "Darwin"
        logger.debug(
            f"NotificationService initialized: macos={self._is_macos}, "
            f"sound={play_sound_enabled}"
        )

    def notify(
        self,
        title: str,
        message: str,
        subtitle: str | None = None,
        sound_name: str = "Glass",
    ) -> None:
        """Trigger non-blocking macOS system notification banner and alert sound.

        Args:
            title: Main notification banner title.
            message: Body message text.
            subtitle: Optional subtitle line.
            sound_name: System sound name in /System/Library/Sounds.
        """
        # Execute notification in background thread to avoid blocking main event loops
        thread = threading.Thread(
            target=self._notify_background,
            args=(title, message, subtitle, sound_name),
            daemon=True,
        )
        thread.start()

    def _notify_background(
        self,
        title: str,
        message: str,
        subtitle: str | None = None,
        sound_name: str = "Glass",
    ) -> None:
        """Background execution worker for osascript and sound playback."""
        logger.info(f"NOTIFICATION BANNER >> [{title}] {message}")

        if not self._is_macos:
            return

        # 1. Play macOS system alert sound if enabled
        if self._play_sound_enabled:
            sound_file = f"/System/Library/Sounds/{sound_name}.aiff"
            if os.path.exists(sound_file):
                try:
                    subprocess.run(
                        ["afplay", sound_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2.0,
                    )
                except Exception as exc:
                    logger.debug(f"afplay sound playback error: {exc}")

        # 2. Display macOS desktop notification banner via osascript
        try:
            sub_part = f' subtitle "{subtitle}"' if subtitle else ""
            applescript = (
                f'display notification "{message}" with title "{title}"{sub_part}'
            )
            subprocess.run(
                ["osascript", "-e", applescript],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3.0,
            )
        except Exception as exc:
            logger.debug(f"osascript notification display error: {exc}")
