"""main.run() 동작 테스트."""

from unittest.mock import patch

import main


def test_run_first_execution_saves_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """첫 실행(last_rcept_no=None)이면 max(rcept_no)를 저장하고 종료한다."""
    items = [
        {"rcept_no": "20260224000002", "corp_name": "A", "report_nm": "B"},
        {"rcept_no": "20260224000005", "corp_name": "C", "report_nm": "D"},
    ]
    saved: dict = {}

    with (
        patch("dart_api.load_api_key", return_value="test-key"),
        patch("state_store.load_state", return_value={}),
        patch("dart_api.fetch_disclosures", return_value=items),
        patch("state_store.save_state", side_effect=lambda s: saved.update(s)),
    ):
        main.run()

    assert saved.get("last_rcept_no") == "20260224000005"


def test_run_first_execution_empty_disclosures(capsys) -> None:  # type: ignore[no-untyped-def]
    """첫 실행(last_rcept_no=None)이고 공시가 없으면 state를 저장하지 않고 종료한다."""
    saved: dict = {}

    with (
        patch("dart_api.load_api_key", return_value="test-key"),
        patch("state_store.load_state", return_value={}),
        patch("dart_api.fetch_disclosures", return_value=[]),
        patch("state_store.save_state", side_effect=lambda s: saved.update(s)),
    ):
        main.run()

    captured = capsys.readouterr().out
    assert "공시 없음" in captured
    assert "last_rcept_no" not in saved


def test_run_second_execution_prints_and_updates(capsys) -> None:  # type: ignore[no-untyped-def]
    """두 번째 실행이면 신규 공시를 출력하고 state를 업데이트한다."""
    items = [
        {"rcept_no": "20260224000010", "corp_name": "삼성", "report_nm": "분기보고서"},
    ]
    saved: dict = {}

    with (
        patch("dart_api.load_api_key", return_value="test-key"),
        patch("state_store.load_state", return_value={"last_rcept_no": "20260224000005"}),
        patch("dart_api.fetch_disclosures", return_value=items),
        patch("state_store.save_state", side_effect=lambda s: saved.update(s)),
    ):
        main.run()

    captured = capsys.readouterr().out
    assert "삼성" in captured
    assert saved.get("last_rcept_no") == "20260224000010"


def test_run_no_new_disclosures_does_not_update_state() -> None:
    """신규 공시가 없으면 state를 업데이트하지 않는다."""
    saved: list = []

    with (
        patch("dart_api.load_api_key", return_value="test-key"),
        patch("state_store.load_state", return_value={"last_rcept_no": "20260224000005"}),
        patch("dart_api.fetch_disclosures", return_value=[]),
        patch("state_store.save_state", side_effect=lambda s: saved.append(s)),
    ):
        main.run()

    assert saved == []
