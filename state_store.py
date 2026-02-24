"""state.json 로드 / 저장 모듈."""

import json
from pathlib import Path
from typing import Any

STATE_FILE: Path = Path("state.json")


def load_state() -> dict[str, Any]:
    """state.json을 읽어 반환한다. 파일이 없으면 빈 dict를 반환한다."""
    if not STATE_FILE.exists():
        return {}
    with STATE_FILE.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def save_state(state: dict[str, Any]) -> None:
    """state를 state.json에 저장한다."""
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)
