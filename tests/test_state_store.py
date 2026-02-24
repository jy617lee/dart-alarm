"""state_store 모듈 테스트."""

from pathlib import Path

import state_store


def test_load_state_returns_empty_when_no_file(
    tmp_path: Path,
) -> None:
    """state.json이 없으면 빈 dict를 반환한다."""
    original = state_store.STATE_FILE
    state_store.STATE_FILE = tmp_path / "state.json"
    try:
        result = state_store.load_state()
    finally:
        state_store.STATE_FILE = original
    assert result == {}


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """저장 후 로드하면 동일한 데이터가 반환된다."""
    original = state_store.STATE_FILE
    state_store.STATE_FILE = tmp_path / "state.json"
    try:
        data = {"last_rcept_no": "20260224000001"}
        state_store.save_state(data)
        result = state_store.load_state()
    finally:
        state_store.STATE_FILE = original
    assert result == data
