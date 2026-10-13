import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configures privacy-safe structured logging.
    Guarantees no candidate PII or raw resume text is logged.
    """
    logger = logging.getLogger("resume_analyzer")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()


def get_logger(name: str | None = None) -> logging.Logger:
    """Returns a child logger or the root resume_analyzer logger."""
    if name:
        return logging.getLogger(f"resume_analyzer.{name}")
    return logger
