"""Native macOS notification manager using osascript fallback."""

import subprocess

from loguru import logger


class NativeNotificationManager:
    """Sends native macOS banner notifications."""

    @staticmethod
    def send_notification(title: str, subtitle: str = "", message: str = "") -> bool:
        """Send a native macOS system notification banner.

        Args:
            title: Notification title string.
            subtitle: Optional notification subtitle string.
            message: Notification message text.

        Returns:
            bool: True if notification dispatch succeeded.
        """
        script = f'display notification "{message}" with title "{title}"'
        if subtitle:
            script += f' subtitle "{subtitle}"'

        cmd = ["osascript", "-e", script]
        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.debug(f"macOS native notification sent: '{title}'")
            return True
        except Exception as exc:
            logger.warning(f"Failed to send native macOS notification: {exc}")
            return False
