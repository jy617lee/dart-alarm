"""main.run() 동작 테스트."""

import logging
from typing import Any
from unittest.mock import patch

import main


def test_run_first_execution_saves_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """첫 실행(last_rcept_no=None)이면 max(rcept_no)를 저장하고 종료한다."""
    items = [
        {"rcept_no": "20260224000002", "corp_name": "A", "report_nm": "B"},
        {"rcept_no": "20260224000005", "corp_name": "C", "report_nm": "D"},
    ]
    saved: dict[str, Any] = {}

    with (
        patch("dart_api.load_api_key", return_value="test-key"),
        patch("state_store.load_state", return_value={}),
        patch("dart_api.fetch_disclosures", return_value=items),
        patch("state_store.save_state", side_effect=lambda s: saved.update(s)),
    ):
        main.run()

    assert saved.get("last_rcept_no") == "20260224000005"


def test_run_first_execution_empty_disclosures(caplog: Any) -> None:
    """첫 실행(last_rcept_no=None)이고 공시가 없으면 state를 저장하지 않고 종료한다."""
    caplog.set_level(logging.INFO)
    saved: dict[str, Any] = {}

    with (
        patch("dart_api.load_api_key", return_value="test-key"),
        patch("state_store.load_state", return_value={}),
        patch("dart_api.fetch_disclosures", return_value=[]),
        patch("state_store.save_state", side_effect=lambda s: saved.update(s)),
    ):
        main.run()

    assert "공시 없음" in caplog.text
    assert "last_rcept_no" not in saved


def test_run_second_execution_prints_and_updates(caplog: Any) -> None:
    """두 번째 실행이면 신규 공시를 출력하고 state를 업데이트한다."""
    caplog.set_level(logging.INFO)
    items = [
        {"rcept_no": "20260224000010", "corp_name": "삼성", "report_nm": "시설 증설"},
    ]
    saved: dict[str, Any] = {}

    with (
        patch("dart_api.load_api_key", return_value="test-key"),
        patch(
            "state_store.load_state",
            return_value={"last_rcept_no": "20260224000005"},
        ),
        patch("dart_api.fetch_disclosures", return_value=items),
        patch("state_store.save_state", side_effect=lambda s: saved.update(s)),
        patch("keyword_filter.datetime") as mock_dt,
        patch("keyword_filter.result_writer.save_results"),
    ):
        mock_dt.datetime.now.return_value.strftime.return_value = "12:00:00"
        main.run()

    assert "시설 증설" in caplog.text
    assert saved.get("last_rcept_no") == "20260224000010"


def test_run_no_new_disclosures_does_not_update_state() -> None:
    """신규 공시가 없으면 state를 업데이트하지 않는다."""
    saved: list[dict[str, Any]] = []

    with (
        patch("dart_api.load_api_key", return_value="test-key"),
        patch(
            "state_store.load_state",
            return_value={"last_rcept_no": "20260224000005"},
        ),
        patch("dart_api.fetch_disclosures", return_value=[]),
        patch("state_store.save_state", side_effect=lambda s: saved.append(s)),
    ):
        main.run()

    assert saved == []


def test_run_with_exception(caplog: Any) -> None:
    """예기치 않은 오류가 발생하면 에러 로그를 남기고 예외를 다시 던진다."""
    import pytest

    caplog.set_level(logging.ERROR)

    with patch("dart_api.load_api_key", side_effect=RuntimeError("테스트 에러")):
        with pytest.raises(RuntimeError, match="테스트 에러"):
            main.run()

    assert "예기치 않은 오류 발생: 테스트 에러" in caplog.text
