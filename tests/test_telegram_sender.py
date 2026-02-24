"""텔레그램 전송 모듈 테스트."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

import telegram_sender


def test_load_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """환경변수가 정상적으로 로드되는지 확인한다."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    with patch("telegram_sender.load_dotenv"):
        token, chat_id = telegram_sender.load_config()

    assert token == "test-token"
    assert chat_id == "12345"


def test_load_config_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """환경변수가 누락되었을 때 예외가 발생하는지 확인한다."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with patch("telegram_sender.load_dotenv"):
        with pytest.raises(RuntimeError, match="설정되지 않았습니다"):
            telegram_sender.load_config()


def test_build_message() -> None:
    """텔레그램용 HTML 메시지가 올바른 포맷으로 구성되는지 확인한다."""
    matched = [
        ({"corp_name": "A", "report_nm": "증설 안내", "rcept_no": "1"}, ["증설"]),
        (
            {"corp_name": "B", "report_nm": "[기재정정] 수주 공시", "rcept_no": "2"},
            ["수주"],
        ),
    ]

    import keyword_filter

    original_kws = keyword_filter.KEYWORDS
    keyword_filter.KEYWORDS = ["증설", "수주", "공개매수"]

    try:
        text = telegram_sender.build_message(matched)
        assert "<b>요약: 증설 1건, 수주 1건, 공개매수 0건</b>" in text
        assert "<b>## 증설</b>" in text
        assert (
            'A | <a href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=1">'
            "증설 안내</a>" in text
        )
        assert "<b>## 수주</b>" in text
        assert (
            'B | <a href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=2">'
            "수주 공시 [정정]</a>" in text
        )
        assert "<b>## 공개매수</b>" in text
        assert "(없음)" in text
    finally:
        keyword_filter.KEYWORDS = original_kws


@patch("telegram_sender.requests.post")
def test_send_message_success(mock_post: MagicMock) -> None:
    """성공 시 재시도 없이 바로 종료되는지 확인한다."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    telegram_sender.send_message("token", "chat", "text")
    assert mock_post.call_count == 1


@patch("telegram_sender.time.sleep")
@patch("telegram_sender.requests.post")
def test_send_message_retries_and_fails(
    mock_post: MagicMock, mock_sleep: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """실패 시 최대 재시도 후 에러 로그를 남기는지 확인한다."""
    import logging

    caplog.set_level(logging.ERROR)

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_post.return_value = mock_resp

    telegram_sender.send_message("token", "chat", "text")
    assert mock_post.call_count == telegram_sender.MAX_RETRIES
    assert "텔레그램 메시지 전송 최종 실패" in caplog.text


@patch("telegram_sender.time.sleep")
@patch("telegram_sender.requests.post")
def test_send_message_retries_on_exception(
    mock_post: MagicMock, mock_sleep: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """예외 발생 시에도 재시도하는지 확인한다."""
    import logging

    caplog.set_level(logging.ERROR)

    mock_post.side_effect = requests.RequestException("Connection error")

    telegram_sender.send_message("token", "chat", "text")
    assert mock_post.call_count == telegram_sender.MAX_RETRIES
    assert "텔레그램 메시지 전송 최종 실패" in caplog.text


@patch("telegram_sender.send_message")
@patch("telegram_sender.load_config", return_value=("t", "c"))
def test_send_alert(mock_load: MagicMock, mock_send: MagicMock) -> None:
    """send_alert가 올바르게 호출되는지 확인한다."""
    matched: list[tuple[dict[str, Any], list[str]]] = []
    telegram_sender.send_alert(matched)
    mock_send.assert_called_once()
