"""DART OpenAPI 폴링 스크립트 - 신규 공시를 필터링하여 콘솔에 출력한다."""

import datetime
from typing import Optional

import dart_api
import keyword_filter
import logger
import result_writer
import state_store


def run() -> None:
    """단일 실행 진입점. 인프라단에서 반복 호출된다."""
    logger.setup_logger()
    log = logger.get_logger()
    log.info("폴링 시작")

    try:
        api_key = dart_api.load_api_key()
        state = state_store.load_state()
        last_rcept_no: Optional[str] = state.get("last_rcept_no")

        # last_rcept_no 유효성 검증: 14자리 YYYYMMDDNNNNNN 형식
        if last_rcept_no is not None and (
            len(last_rcept_no) != 14 or not last_rcept_no.isdigit()
        ):
            log.warning(
                f"last_rcept_no 형식 이상 ({last_rcept_no!r}) → None으로 초기화"
            )
            last_rcept_no = None

        # bgn_date: last_rcept_no 앞 8자리(YYYYMMDD), 없으면 오늘
        if last_rcept_no:
            bgn_date = last_rcept_no[:8]
        else:
            bgn_date = datetime.date.today().strftime("%Y%m%d")

        now = datetime.datetime.now()

        try:
            items = dart_api.fetch_disclosures(api_key, bgn_date, last_rcept_no)
        except RuntimeError as api_err:
            log.error(f"API 호출 실패: {api_err}")
            result_writer.save_error_result(now, str(api_err))
            return

        if last_rcept_no is None:
            # 첫 실행: max(rcept_no)를 저장하고 종료 (알람 없음)
            if items:
                new_last = max(i["rcept_no"] for i in items)
                state_store.save_state({"last_rcept_no": new_last})
                log.info(f"첫 실행 완료. last_rcept_no={new_last} 저장.")
            else:
                log.info("첫 실행 완료. 공시 없음.")
            return

        # 두 번째 실행부터: 신규 공시 출력 후 state 업데이트
        keyword_filter.filter_and_print_disclosures(items, last_rcept_no)

        if items:
            new_last = max(i["rcept_no"] for i in items)
            state_store.save_state({"last_rcept_no": new_last})
            log.info(f"last_rcept_no={new_last} 업데이트 완료.")
        else:
            log.info("신규 공시 없음.")
    except Exception as e:
        log.error(f"예기치 않은 오류 발생: {e}", exc_info=True)
        raise


if __name__ == "__main__":  # pragma: no cover
    run()
