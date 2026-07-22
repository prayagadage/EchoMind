"""Application container and service locator for EchoMind.

Manages application initialization, settings wiring, logger setup, database lifespan,
and component lifecycle hooks without relying on global state.
"""

from core.config import Settings, get_settings
from core.event_bus import EventBus
from core.exceptions import InitializationError
from core.logger import setup_logger
from loguru import logger
from modules.storage.db import DatabaseEngine
from modules.storage.service import TranscriptService


class ApplicationContainer:
    """Manages application-wide service wiring, state, and lifespan management."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize container instance.

        Args:
            settings: Optional explicit Settings instance (useful for test overrides).
        """
        self._settings: Settings | None = settings
        self._event_bus: EventBus | None = None
        self._db_engine: DatabaseEngine | None = None
        self._transcript_service: TranscriptService | None = None
        self._initialized: bool = False

    @property
    def settings(self) -> Settings:
        """Access validated configuration settings instance."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def event_bus(self) -> EventBus:
        """Access global EventBus instance."""
        if self._event_bus is None:
            self._event_bus = EventBus()
        return self._event_bus

    @property
    def db_engine(self) -> DatabaseEngine:
        """Access DatabaseEngine instance."""
        if self._db_engine is None:
            self._db_engine = DatabaseEngine()
        return self._db_engine

    @property
    def transcript_service(self) -> TranscriptService:
        """Access TranscriptService instance."""
        if self._transcript_service is None:
            self._transcript_service = TranscriptService(
                db_engine=self.db_engine,
                event_bus=self.event_bus,
            )
        return self._transcript_service

    @property
    def is_initialized(self) -> bool:
        """Check if application lifespan container is initialized."""
        return self._initialized

    def initialize(self) -> None:
        """Bootstrap system infrastructure, logging, database, and health diagnostics.

        Raises:
            InitializationError: If setup fails.
        """
        if self._initialized:
            logger.warning(
                "ApplicationContainer initialization requested but already active."
            )
            return

        try:
            # 1. Setup structured logging
            setup_logger(self.settings)

            # 2. Log initialization lifecycle event
            logger.info(
                f"Initializing {self.settings.app_name} v{self.settings.app_version} "
                f"[{self.settings.app_env.upper()} mode]"
            )

            # 3. Perform hardware & runtime platform health checks
            self._verify_platform_environment()

            # 4. Initialize Database & TranscriptService
            self.transcript_service.db_engine.init_db()

            self._initialized = True
            logger.info("ApplicationContainer initialization complete.")
        except Exception as exc:
            raise InitializationError(
                message=f"Failed to initialize ApplicationContainer: {exc}",
                details={"error": str(exc)},
            ) from exc

    def _verify_platform_environment(self) -> None:
        """Verify operating system and platform capabilities."""
        import platform

        os_name = platform.system()
        arch = platform.machine()

        logger.debug(f"Detected Platform: OS={os_name}, Architecture={arch}")

        # Non-fatal warning if running off Apple Silicon
        if os_name != "Darwin" or arch != "arm64":
            logger.warning(
                f"Host platform ({os_name} {arch}) differs from "
                "primary target (macOS arm64). "
                "Performance optimizations for Apple Silicon Metal/MLX may be disabled."
            )

    def shutdown(self) -> None:
        """Gracefully shutdown services and release resources."""
        if not self._initialized:
            return

        logger.info("Shutting down ApplicationContainer services...")

        if self._event_bus is not None:
            self._event_bus.shutdown()

        if self._db_engine is not None:
            self._db_engine.close()

        self._initialized = False
        logger.info("ApplicationContainer shutdown complete.")
