"""main.py 모듈 임포트 및 기본 구조 테스트."""

import importlib
import json
import os


def test_main_module_importable() -> None:
    """main 모듈이 임포트 가능해야 한다."""
    mod = importlib.import_module("main")
    assert mod is not None


def test_main_has_run_function() -> None:
    """main 모듈에 run 함수가 존재해야 한다."""
    import main

    assert callable(main.run)


def test_state_json_is_valid_json(tmp_path: object) -> None:
    """state.json 파일이 유효한 JSON이어야 한다."""
    state_file = os.path.join(os.path.dirname(__file__), "..", "state.json")
    with open(state_file, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_results_directory_exists() -> None:
    """results/ 디렉토리가 존재해야 한다."""
    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    assert os.path.isdir(results_dir)
