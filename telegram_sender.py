"""텔레그램 알람 전송 모듈."""

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

import logger

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2


def load_config() -> tuple[str, str]:
    """환경변수에서 텔레그램 봇 토큰과 채팅방 ID를 로드한다."""
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 환경변수가 설정되지 않았습니다."
        )

    return token, chat_id


def build_message(matched: list[tuple[dict[str, Any], list[str]]]) -> str:
    """텔레그램 전송용 HTML 메시지를 구성한다.

    키워드별로 공시를 그룹핑하며, 공시 명칭에 DART URL 하이퍼링크를 삽입한다.
    """
    from keyword_filter import KEYWORDS

    # 요약 정보 (키워드별 건수)
    summary_parts = []
    for kw in KEYWORDS:
        count = sum(1 for _, kws in matched if kw in kws)
        summary_parts.append(f"{kw} {count}건")

    lines: list[str] = ["<b>📢 DART 공시 알람</b>"]
    lines.append(f"요약: {', '.join(summary_parts)}")
    lines.append("")

    for kw in KEYWORDS:
        lines.append(f"<b>▶ {kw}</b>")
        items_for_kw = [item for item, kws in matched if kw in kws]

        if items_for_kw:
            for item in items_for_kw:
                corp_name = item.get("corp_name", "")
                report_nm = item.get("report_nm", "")
                rcept_no = item.get("rcept_no", "")

                if "[기재정정]" in report_nm:
                    report_nm = report_nm.replace("[기재정정]", "").strip() + " [정정]"

                url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                lines.append(f'{corp_name} | <a href="{url}">{report_nm}</a>')
        else:
            lines.append("(없음)")

        lines.append("")

    return "\n".join(lines).strip()


def send_message(token: str, chat_id: str, text: str) -> None:
    """텔레그램 API를 호출하여 메시지를 전송한다.

    실패 시 지수 백오프 기반으로 최대 MAX_RETRIES 회 재시도한다.
    """
    url = TELEGRAM_API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    log = logger.get_logger()
    backoff_exponent = 0

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                log.info("텔레그램 메시지 전송 성공")
                return

            log.warning(
                f"텔레그램 전송 실패 (시도 {attempt}/{MAX_RETRIES},"
                f" status: {response.status_code}): {response.text}"
            )
        except Exception as e:
            log.warning(
                f"텔레그램 전송 중 예외 발생 (시도 {attempt}/{MAX_RETRIES}): {e}"
            )

        if attempt < MAX_RETRIES:
            wait = BACKOFF_BASE_SECONDS * (2**backoff_exponent)
            log.info(f"{wait}초 후 재시도...")
            time.sleep(wait)
            backoff_exponent += 1

    log.error("텔레그램 메시지 전송 최종 실패")


def send_alert(matched: list[tuple[dict[str, Any], list[str]]]) -> None:
    """매칭된 공시 목록을 텔레그램으로 전송한다.

    환경 변수가 누락된 경우 에러 로그를 남기고 조용히 종료한다 (앱을 중단시키지 않음).
    """
    log = logger.get_logger()
    try:
        token, chat_id = load_config()
    except RuntimeError as e:
        log.error(f"텔레그램 설정 오류 - 알람 전송 생략: {e}")
        return

    text = build_message(matched)
    send_message(token, chat_id, text)
