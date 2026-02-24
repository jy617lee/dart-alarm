"""로거 모듈 테스트."""

import logging

from logger import get_logger, setup_logger


def test_logger_setup() -> None:
    """로거가 올바르게 설정되는지 확인한다."""
    setup_logger()
    logger = get_logger()
    assert logger.level == logging.INFO
    assert len(logger.handlers) >= 2  # 콘솔 + 파일
    # 핸들러 타입 확인
    types = [type(h) for h in logger.handlers]
    assert logging.StreamHandler in types
    assert logging.FileHandler in types
