"""로거 관련 모듈."""

import logging
import sys
from typing import Optional

_logger = logging.getLogger("dart_alarm")


def setup_logger() -> None:
    """로거 설정 (콘솔 및 파일 핸들러 추가)."""
    _logger.setLevel(logging.INFO)

    # 중복 추가 방지
    if _logger.handlers:
        return

    formatter = logging.Formatter(
        fmt="[%(levelname)s] %(asctime)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    _logger.addHandler(console_handler)
    _logger.addHandler(file_handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """공통 설정된 로거 반환."""
    return _logger
