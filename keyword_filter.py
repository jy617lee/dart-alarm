"""공시 키워드 필터링 및 출력 모듈."""

import datetime
from typing import Any

import logger
import result_writer
import telegram_sender

KEYWORDS = ["증설", "수주", "공개매수", "자사주매입", "흑자전환", "임상"]


def filter_and_print_disclosures(
    items: list[dict[str, Any]], last_rcept_no: str
) -> None:
    """신규 공시에서 키워드를 매칭하고 포맷에 맞게 콘솔에 출력한다."""
    matched = []

    for item in items:
        report_nm = item.get("report_nm", "")
        # 키워드 매칭 (부분 일치)
        matched_kws = [kw for kw in KEYWORDS if kw in report_nm]
        if matched_kws:
            matched.append((item, matched_kws))

    now = datetime.datetime.now()
    today = now.date()
    total_count = len(items)

    log = logger.get_logger()

    if not matched:
        log.info(f"폴링 완료 - 신규 {total_count}건 중 매칭 없음")
        return

    log.info(f"신규 {total_count}건 중 키워드 매칭 {len(matched)}건")

    for i, (item, kws) in enumerate(matched, 1):
        corp_name = item.get("corp_name", "")
        report_nm = item.get("report_nm", "")
        rcept_no = item.get("rcept_no", "")

        # [기재정정] 태그 변환
        if "[기재정정]" in report_nm:
            report_nm = report_nm.replace("[기재정정]", "").strip() + " [정정]"

        kw_str = ", ".join(kws)
        url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

        log.info(f"{i}. {corp_name} | {report_nm} | 매칭키워드: {kw_str} | {url}")

    # 마크다운 파일에 매칭 결과 추가 저장
    result_writer.save_results(matched, today, now, last_rcept_no)

    # 텔레그램 알람 전송
    telegram_sender.send_alert(matched)
