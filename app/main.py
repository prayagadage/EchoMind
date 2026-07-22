"""Application entry point for EchoMind.

Bootstraps the application container, executes initial health routines,
and verifies system readiness.
"""

import sys

from core.exceptions import EchoMindBaseException
from loguru import logger

from app.container import ApplicationContainer


def main() -> int:
    """Main execution function.

    Returns:
        int: Process exit code (0 for success, 1 for error).
    """
    container = ApplicationContainer()
    try:
        # Bootstrap infrastructure and logging
        container.initialize()

        # Log successful initialization message required by Phase 0 specification
        logger.info("EchoMind initialized successfully.")

        # Graceful container cleanup
        container.shutdown()
        return 0

    except EchoMindBaseException as exc:
        logger.error(f"EchoMind application failed with domain error: {exc}")
        return 1
    except Exception as exc:
        logger.critical(f"Unhandled system error encountered: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
