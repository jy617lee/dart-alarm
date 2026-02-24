"""결과 저장소 모듈."""

import datetime
from pathlib import Path
from typing import Any

RESULTS_DIR = Path("results")


def save_results(
    matched: list[tuple[dict[str, Any], list[str]]],
    today: datetime.date,
    now: datetime.datetime,
) -> None:
    """매칭된 공시 결과를 마크다운 파일에 기록한다."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RESULTS_DIR / f"{today.strftime('%Y-%m-%d')}.md"

    is_new = not file_path.exists()
    lines = []

    if is_new:
        lines.append(f"# {today.strftime('%Y-%m-%d')} 공시 알람 결과")

    now_str = now.strftime("%H:%M:%S")

    # 각 폴링 결과 묶음을 띄우기 위해 빈 줄 하나 추가
    lines.append("")

    from keyword_filter import KEYWORDS

    for kw in KEYWORDS:
        lines.append(f"## {kw}")

        # 해당 키워드를 포함하는 매칭 항목만 필터
        items_for_kw = [item for item, kws in matched if kw in kws]

        if items_for_kw:
            for item in items_for_kw:
                corp_name = item.get("corp_name", "")
                report_nm = item.get("report_nm", "")
                rcept_no = item.get("rcept_no", "")

                if "[기재정정]" in report_nm:
                    report_nm = report_nm.replace("[기재정정]", "").strip() + " [정정]"

                url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                lines.append(f"{now_str} | {corp_name} | {report_nm} | {url}")
        else:
            lines.append("(없음)")

        lines.append("")

    # 파일의 끝에 내용 추가 (append 모드)
    with file_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))
