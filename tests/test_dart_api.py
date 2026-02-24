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
    # load_dotenv가 실제 .env를 읽어서 다시 키를 채우지 않도록 모킹
    with (
        patch("dart_api.load_dotenv"),
        pytest.raises(RuntimeError, match="DART_API_KEY"),
    ):
        dart_api.load_api_key()


# ---------------------------------------------------------------------------
# _fetch_page
# ---------------------------------------------------------------------------


def _make_response(status_code: int, json_data: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


def test_fetch_page_returns_list_on_success() -> None:
    """200 응답이면 공시 목록을 반환한다."""
    payload: dict[str, Any] = {
        "status": "000",
        "list": [
            {
                "rcept_no": "20260224000001",
                "corp_name": "테스트",
                "report_nm": "보고서",
            },
        ],
    }
    with patch("dart_api.requests.get", return_value=_make_response(200, payload)):
        result = dart_api._fetch_page("test-key", "20260224", 1)
    assert result == payload["list"]


def test_fetch_page_retries_on_error() -> None:
    """일반 오류 시 최대 MAX_RETRIES회 재시도 후 RuntimeError를 c1c생한다."""
    import pytest

    error_payload: dict[str, Any] = {"status": "900", "list": []}
    mock_resp = _make_response(200, error_payload)

    with (
        patch("dart_api.requests.get", return_value=mock_resp) as mock_get,
        patch("dart_api.time.sleep"),
        pytest.raises(RuntimeError, match="DART API 최종 실패"),
    ):
        dart_api._fetch_page("test-key", "20260224", 1)

    assert mock_get.call_count == dart_api.MAX_RETRIES


def test_fetch_page_exponential_backoff_on_429() -> None:
    """429 응답 시 지수 백오프(1분→2분)를 적용하고 이후 성공하면 목록을 반환한다."""
    too_many = _make_response(429, {})
    success_payload: dict[str, Any] = {
        "status": "000",
        "list": [{"rcept_no": "20260224000001", "corp_name": "A", "report_nm": "B"}],
    }
    success = _make_response(200, success_payload)

    sleep_calls: list[float] = []

    with (
        patch("dart_api.requests.get", side_effect=[too_many, too_many, success]),
        patch("dart_api.time.sleep", side_effect=lambda s: sleep_calls.append(s)),
    ):
        result = dart_api._fetch_page("test-key", "20260224", 1)

    assert sleep_calls == [
        dart_api.BACKOFF_BASE_SECONDS,
        dart_api.BACKOFF_BASE_SECONDS * 2,
    ]
    assert result == success_payload["list"]


# ---------------------------------------------------------------------------
# fetch_disclosures (페이지네이션 + 필터링)
# ---------------------------------------------------------------------------


def _make_items(rcept_nos: list[str]) -> list[dict[str, Any]]:
    return [{"rcept_no": r, "corp_name": "A", "report_nm": "B"} for r in rcept_nos]


def test_fetch_disclosures_first_run_returns_all() -> None:
    """last_rcept_no=None(첫 실행)이면 전체 공시를 반환한다."""
    items = _make_items(["20260224000001", "20260224000002"])
    with patch("dart_api._fetch_page", return_value=items):
        result = dart_api.fetch_disclosures("key", "20260224", last_rcept_no=None)
    assert result == items


def test_fetch_disclosures_filters_by_last_rcept_no() -> None:
    """last_rcept_no보다 큰 것만 반환한다."""
    page1 = _make_items(["20260224000003", "20260224000004"])
    # page1에 신규가 있으므로 다음 페이지 요청, page2는 PAGE_SIZE 미만 → 종료
    page2: list[dict[str, Any]] = []

    with patch("dart_api._fetch_page", side_effect=[page1, page2]):
        result = dart_api.fetch_disclosures(
            "key", "20260224", last_rcept_no="20260224000002"
        )

    assert [i["rcept_no"] for i in result] == ["20260224000003", "20260224000004"]


def test_fetch_disclosures_early_exit_when_no_new() -> None:
    """응답 중 신규가 하나도 없으면 조기 종료한다."""
    old_items = _make_items(["20260224000001", "20260224000002"])

    with patch("dart_api._fetch_page", return_value=old_items) as mock_page:
        result = dart_api.fetch_disclosures(
            "key", "20260224", last_rcept_no="20260224000005"
        )

    assert result == []
    assert mock_page.call_count == 1  # 첫 페이지에서 조기 종료


def test_fetch_disclosures_stops_at_last_page() -> None:
    """응답이 PAGE_SIZE 미만이면 마지막 페이지로 판단하고 종료한다."""
    page1 = _make_items(["20260224000003"])  # PAGE_SIZE(100) 미만 → 마지막 페이지

    with patch("dart_api._fetch_page", return_value=page1) as mock_page:
        result = dart_api.fetch_disclosures(
            "key", "20260224", last_rcept_no="20260224000002"
        )

    assert [i["rcept_no"] for i in result] == ["20260224000003"]
    assert mock_page.call_count == 1


def test_fetch_disclosures_fetches_multiple_pages() -> None:
    """PAGE_SIZE만큼 응답이 오면 다음 페이지를 계속 요청한다."""
    page1 = _make_items([str(i) for i in range(1, dart_api.PAGE_SIZE + 1)])  # 100건
    page2 = _make_items(["101"])  # 1건

    with patch("dart_api._fetch_page", side_effect=[page1, page2]) as mock_page:
        result = dart_api.fetch_disclosures("key", "20260224", last_rcept_no=None)

    assert len(result) == dart_api.PAGE_SIZE + 1
    assert mock_page.call_count == 2
