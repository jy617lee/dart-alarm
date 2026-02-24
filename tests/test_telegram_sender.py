"""텔레그램 전송 모듈 테스트."""

import logging
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
    """환경변수가 누락되었을 때 RuntimeError가 발생하는지 확인한다."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with patch("telegram_sender.load_dotenv"):
        with pytest.raises(RuntimeError, match="설정되지 않았습니다"):
            telegram_sender.load_config()


def test_build_message_format() -> None:
    """키워드별 그룹핑, 요약, 하이퍼링크가 올바른 HTML 포맷인지 확인한다."""
    matched: list[tuple[dict[str, Any], list[str]]] = [
        ({"corp_name": "A사", "report_nm": "증설 안내", "rcept_no": "1"}, ["증설"]),
        (
            {
                "corp_name": "B사",
                "report_nm": "[기재정정] 수주 공시",
                "rcept_no": "2",
            },
            ["수주"],
        ),
    ]

    import keyword_filter

    original_kws = keyword_filter.KEYWORDS
    keyword_filter.KEYWORDS = ["증설", "수주", "공개매수"]

    try:
        text = telegram_sender.build_message(matched)

        # 요약
        assert "증설 1건, 수주 1건, 공개매수 0건" in text
        # 키워드 헤더
        assert "<b>▶ 증설</b>" in text
        assert "<b>▶ 수주</b>" in text
        assert "<b>▶ 공개매수</b>" in text
        # 하이퍼링크
        dart_url_1 = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=1"
        assert f'<a href="{dart_url_1}">증설 안내</a>' in text
        # [기재정정] -> [정정] 변환
        dart_url_2 = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=2"
        assert f'<a href="{dart_url_2}">수주 공시 [정정]</a>' in text
        # 없는 키워드는 (없음)
        assert "(없음)" in text
    finally:
        keyword_filter.KEYWORDS = original_kws


@patch("telegram_sender.requests.post")
def test_send_message_success(mock_post: MagicMock) -> None:
    """200 응답을 받으면 재시도 없이 성공 처리되는지 확인한다."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    telegram_sender.send_message("token", "chat", "text")

    assert mock_post.call_count == 1


@patch("telegram_sender.time.sleep")
@patch("telegram_sender.requests.post")
def test_send_message_retries_on_failure(
    mock_post: MagicMock,
    mock_sleep: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """HTTP 오류 발생 시 최대 재시도 후 에러 로그를 남기는지 확인한다."""
    caplog.set_level(logging.ERROR)

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_post.return_value = mock_resp

    telegram_sender.send_message("token", "chat", "text")

    assert mock_post.call_count == telegram_sender.MAX_RETRIES
    assert "텔레그램 메시지 전송 최종 실패" in caplog.text


@patch("telegram_sender.time.sleep")
@patch("telegram_sender.requests.post")
def test_send_message_retries_on_exception(
    mock_post: MagicMock,
    mock_sleep: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """예외 발생 시에도 재시도하고 최종 에러 로그를 남기는지 확인한다."""
    caplog.set_level(logging.ERROR)

    mock_post.side_effect = requests.RequestException("Connection error")

    telegram_sender.send_message("token", "chat", "text")

    assert mock_post.call_count == telegram_sender.MAX_RETRIES
    assert "텔레그램 메시지 전송 최종 실패" in caplog.text


@patch("telegram_sender.send_message")
@patch("telegram_sender.load_config", return_value=("tok", "cid"))
def test_send_alert_calls_send_message(
    mock_cfg: MagicMock, mock_send: MagicMock
) -> None:
    """send_alert가 send_message를 정상적으로 호출하는지 확인한다."""
    matched: list[tuple[dict[str, Any], list[str]]] = []
    telegram_sender.send_alert(matched)
    mock_send.assert_called_once()


def test_send_alert_missing_env(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """환경변수 누락 시 에러 로그만 남기고 예외 없이 종료되는지 확인한다."""
    caplog.set_level(logging.ERROR)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with patch("telegram_sender.load_dotenv"):
        telegram_sender.send_alert([])  # 예외 없이 종료되어야 함

    assert "텔레그램 설정 오류" in caplog.text
