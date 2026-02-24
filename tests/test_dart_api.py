"""DART API 연동 테스트."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import dart_api

# ---------------------------------------------------------------------------
# load_api_key
# ---------------------------------------------------------------------------


def test_load_api_key_returns_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """환경변수에 키가 있으면 반환한다."""
    monkeypatch.setenv("DART_API_KEY", "test-key")
    assert dart_api.load_api_key() == "test-key"


def test_load_api_key_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """환경변수가 없으면 RuntimeError를 즉시 발생시킨다."""
    monkeypatch.delenv("DART_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DART_API_KEY"):
        dart_api.load_api_key()


# ---------------------------------------------------------------------------
# fetch_disclosures
# ---------------------------------------------------------------------------


def _make_response(status_code: int, json_data: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


def test_fetch_disclosures_returns_list_on_success() -> None:
    """200 응답이면 공시 목록을 반환한다."""
    payload: dict[str, Any] = {
        "status": "000",
        "list": [
            {"rcept_no": "1", "corp_name": "테스트", "report_nm": "보고서"},
        ],
    }
    with patch("dart_api.requests.get", return_value=_make_response(200, payload)):
        result = dart_api.fetch_disclosures("test-key", "20260224")
    assert result == payload["list"]


def test_fetch_disclosures_retries_on_error() -> None:
    """일반 오류 시 최대 MAX_RETRIES회 재시도 후 빈 리스트를 반환한다."""
    error_payload: dict[str, Any] = {"status": "900", "list": []}
    mock_resp = _make_response(200, error_payload)

    with (
        patch("dart_api.requests.get", return_value=mock_resp) as mock_get,
        patch("dart_api.time.sleep"),
    ):
        result = dart_api.fetch_disclosures("test-key", "20260224")

    assert result == []
    assert mock_get.call_count == dart_api.MAX_RETRIES


def test_fetch_disclosures_exponential_backoff_on_429() -> None:
    """429 응답 시 지수 백오프(1분→2분)를 적용하고 이후 성공하면 목록을 반환한다."""
    too_many = _make_response(429, {})
    success_payload: dict[str, Any] = {
        "status": "000",
        "list": [{"rcept_no": "1", "corp_name": "A", "report_nm": "B"}],
    }
    success = _make_response(200, success_payload)

    sleep_calls: list[float] = []

    with (
        patch("dart_api.requests.get", side_effect=[too_many, too_many, success]),
        patch("dart_api.time.sleep", side_effect=lambda s: sleep_calls.append(s)),
    ):
        result = dart_api.fetch_disclosures("test-key", "20260224")

    assert sleep_calls == [
        dart_api.BACKOFF_BASE_SECONDS,
        dart_api.BACKOFF_BASE_SECONDS * 2,
    ]
    assert result == success_payload["list"]


# ---------------------------------------------------------------------------
# print_disclosures
# ---------------------------------------------------------------------------


def test_print_disclosures_outputs_fields(capsys: pytest.CaptureFixture[str]) -> None:
    """rcept_no, corp_name, report_nm이 출력에 포함되어야 한다."""
    items: list[dict[str, Any]] = [
        {"rcept_no": "20260224001", "corp_name": "삼성전자", "report_nm": "분기보고서"}
    ]
    dart_api.print_disclosures(items)
    captured = capsys.readouterr().out
    assert "20260224001" in captured
    assert "삼성전자" in captured
    assert "분기보고서" in captured


def test_print_disclosures_empty_prints_nothing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """빈 목록이면 아무것도 출력하지 않는다."""
    dart_api.print_disclosures([])
    assert capsys.readouterr().out == ""
