"""Logging utilities"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "100 MB",
    retention: str = "30 days",
    format_string: Optional[str] = None
):
    """Setup logging system

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file path, if None only output to console
        rotation: Log rotation size
        retention: Log retention time
        format_string: Custom log format
    """
    # Remove default handler
    logger.remove()

    # Default format
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Add console handler
    logger.add(
        sys.stderr,
        format=format_string,
        level=log_level,
        colorize=True
    )

    # Add file handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format=format_string,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8"
        )

    logger.info(f"Logger initialized with level: {log_level}")


def get_logger(name: str):
    """Get logger with specified name

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logger.bind(name=name)


# Export logger for use in other modules
__all__ = ["logger", "setup_logger", "get_logger"]
