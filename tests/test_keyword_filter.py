"""키워드 필터 모듈 테스트."""

from typing import Any
from unittest.mock import patch

import keyword_filter


def test_filter_no_match(capsys) -> None:  # type: ignore[no-untyped-def]
    """매칭되는 키워드가 없으면 매칭 없음 메시지를 출력한다."""
    items: list[dict[str, Any]] = [
        {"rcept_no": "1", "corp_name": "삼성전자", "report_nm": "사업보고서"},
        {"rcept_no": "2", "corp_name": "카카오", "report_nm": "분기보고서"},
    ]
    with patch("keyword_filter.datetime") as mock_dt:
        mock_dt.datetime.now.return_value.strftime.return_value = "12:00:00"
        keyword_filter.filter_and_print_disclosures(items)

    captured = capsys.readouterr().out
    assert "[12:00:00] 폴링 완료 - 신규 2건 중 매칭 없음" in captured


def test_filter_with_match(capsys) -> None:  # type: ignore[no-untyped-def]
    """매칭되는 키워드가 있으면 포맷에 맞춰 출력한다."""
    items: list[dict[str, Any]] = [
        {"rcept_no": "1", "corp_name": "삼성전자", "report_nm": "신규 시설 증설"},
        {"rcept_no": "2", "corp_name": "카카오", "report_nm": "분기보고서"},
    ]
    with patch("keyword_filter.datetime") as mock_dt:
        mock_dt.datetime.now.return_value.strftime.return_value = "12:00:00"
        keyword_filter.filter_and_print_disclosures(items)

    captured = capsys.readouterr().out
    assert "[12:00:00] 신규 2건 중 키워드 매칭 1건" in captured
    assert (
        "1. 삼성전자 | 신규 시설 증설 | 매칭키워드: 증설 | "
        "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=1"
    ) in captured


def test_filter_with_correct_tag(capsys) -> None:  # type: ignore[no-untyped-def]
    """제목에 [기재정정]이 있으면 [정정] 태그를 붙인다."""
    items: list[dict[str, Any]] = [
        {
            "rcept_no": "3",
            "corp_name": "네이버",
            "report_nm": "[기재정정] 대규모 수주 계획",
        },
    ]
    with patch("keyword_filter.datetime") as mock_dt:
        mock_dt.datetime.now.return_value.strftime.return_value = "12:00:00"
        keyword_filter.filter_and_print_disclosures(items)

    captured = capsys.readouterr().out
    assert "1. 네이버 | 대규모 수주 계획 [정정] | 매칭키워드: 수주 |" in captured
