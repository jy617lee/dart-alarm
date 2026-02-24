"""결과 저장소 테스트."""

import datetime
from pathlib import Path

import result_writer


def test_save_results(tmp_path: Path) -> None:
    """결과가 포맷에 맞게 마크다운으로 저장되는지 확인한다."""
    original_dir = result_writer.RESULTS_DIR
    result_writer.RESULTS_DIR = tmp_path
    today = datetime.date(2026, 2, 24)
    now = datetime.datetime(2026, 2, 24, 15, 23, 0)

    matched = [
        (
            {"corp_name": "A", "report_nm": "증설 계획", "rcept_no": "1"},
            ["증설"],
        ),
        (
            {"corp_name": "B", "report_nm": "[기재정정] 수주 공시", "rcept_no": "2"},
            ["수주"],
        ),
        (
            {"corp_name": "C", "report_nm": "다른 증설", "rcept_no": "3"},
            ["증설"],
        ),
    ]

    try:
        result_writer.save_results(matched, today, now, "20260224000000")
        file_path = tmp_path / "20260224_1523.md"
        assert file_path.exists()

        content = file_path.read_text("utf-8")
        assert "# 2026-02-24 15:23 공시 알람 결과" in content
        assert "> **기준 접수 번호:** `20260224000000`" in content
        assert "## 증설" in content
        assert "A | 증설 계획 | https://" in content
        assert "C | 다른 증설 | https://" in content
        assert "## 수주" in content
        assert "B | 수주 공시 [정정] | https://" in content
        assert "## 공개매수" in content
        assert "(없음)" in content
        assert content.count("# 2026-02-24 15:23") == 1  # 헤더가 한 번만 있어야 함
    finally:
        result_writer.RESULTS_DIR = original_dir
