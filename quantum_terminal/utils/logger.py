"""Logger configuration with loguru for Quantum Investment Terminal.

Provides structured logging with:
- Colored console output
- Automatic log rotation
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Dual output: console + file logs/quantum.log
- Environment-based configuration (DEV/PROD)
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger as _logger

from quantum_terminal.config import settings


# Remove default handler
_logger.remove()

# Determine environment
ENVIRONMENT: str = "PROD" if not settings.debug else "DEV"
LOG_LEVEL: str = settings.log_level.upper()

# Ensure logs directory exists
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Console format with colors
CONSOLE_FORMAT = (
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# File format (no colors)
FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "{message}"
)

# Add console handler with colors
_logger.add(
    sink=sys.stdout,
    format=CONSOLE_FORMAT,
    level=LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=ENVIRONMENT == "DEV",
)

# Add file handler with rotation
_logger.add(
    sink=logs_dir / "quantum.log",
    format=FILE_FORMAT,
    level=LOG_LEVEL,
    rotation="00:00",  # Rotate daily at midnight
    retention="7 days",  # Keep 7 days of logs
    compression="zip",  # Compress rotated logs
    backtrace=True,
    diagnose=ENVIRONMENT == "DEV",
)

# Add error file handler for error-level logs only
_logger.add(
    sink=logs_dir / "quantum_errors.log",
    format=FILE_FORMAT,
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)


def get_logger(name: Optional[str] = None):
    """Get a logger instance with optional name binding.

    Args:
        name: Optional logger name (typically __name__ from calling module).

    Returns:
        Configured loguru logger instance.

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    if name:
        return _logger.bind(module=name)
    return _logger


# Export main logger instance
logger = get_logger()


def configure_logging(
    level: str = "INFO",
    debug_mode: bool = False,
    log_file: Optional[Path] = None,
) -> None:
    """Reconfigure logging at runtime.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        debug_mode: Enable detailed diagnostics.
        log_file: Custom log file path.

    Raises:
        ValueError: If log level is invalid.
    """
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if level.upper() not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")

    # Update global logger level
    _logger.remove()
    _logger.add(
        sink=sys.stdout,
        format=CONSOLE_FORMAT,
        level=level.upper(),
        colorize=True,
        backtrace=True,
        diagnose=debug_mode,
    )

    # Use custom log file or default
    log_path = log_file or (logs_dir / "quantum.log")
    _logger.add(
        sink=log_path,
        format=FILE_FORMAT,
        level=level.upper(),
        rotation="00:00",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=debug_mode,
    )

    logger.info(f"Logging configured: level={level}, debug={debug_mode}, file={log_path}")


# Initial log
logger.info(f"Quantum Terminal logger initialized | Environment: {ENVIRONMENT} | Level: {LOG_LEVEL}")
