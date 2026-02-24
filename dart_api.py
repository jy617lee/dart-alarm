"""DART OpenAPI 공시 목록 조회 모듈."""

import os
import time
from typing import Any, Optional

import requests
from dotenv import load_dotenv

import logger

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
PAGE_SIZE: int = 100
DART_API_URL: str = "https://opendart.fss.or.kr/api/list.json"
MAX_RETRIES: int = 3
RETRY_INTERVAL_SECONDS: int = 5
BACKOFF_BASE_SECONDS: int = 60  # 429 시 기본 대기: 60초 → 120초 → 240초
HTTP_TOO_MANY_REQUESTS: int = 429
STATUS_OK: str = "000"


# ---------------------------------------------------------------------------
# API 키 로드
# ---------------------------------------------------------------------------


def load_api_key() -> str:
    """환경변수에서 DART_API_KEY를 로드한다.

    .env 파일이 있으면 자동으로 읽어온다.
    키가 없으면 RuntimeError를 즉시 발생시킨다.
    """
    load_dotenv()
    key = os.environ.get("DART_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DART_API_KEY 환경변수가 설정되지 않았습니다.")
    return key


# ---------------------------------------------------------------------------
# 단일 페이지 호출
# ---------------------------------------------------------------------------


def _fetch_page(api_key: str, bgn_date: str, page_no: int) -> list[dict[str, Any]]:
    """DART API에서 단일 페이지를 조회하여 반환한다.

    - 일반 오류(status != 000): 최대 MAX_RETRIES회 재시도, 간격 RETRY_INTERVAL_SECONDS초
    - 429 Too Many Requests: Exponential Backoff (BACKOFF_BASE_SECONDS * 2^n 초 대기)
    """
    params: dict[str, Any] = {
        "crtfc_key": api_key,
        "bgn_de": bgn_date,
        "page_count": PAGE_SIZE,
        "page_no": page_no,
    }
    backoff_exponent = 0

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.get(DART_API_URL, params=params, timeout=10)

        if response.status_code == HTTP_TOO_MANY_REQUESTS:
            wait = BACKOFF_BASE_SECONDS * (2**backoff_exponent)
            logger.get_logger().warning(
                f"429 Too Many Requests (page {page_no}). {wait}초 후 재시도..."
            )
            time.sleep(wait)
            backoff_exponent += 1
            continue

        data: dict[str, Any] = response.json()
        if data.get("status") == STATUS_OK:
            result: list[dict[str, Any]] = data.get("list", [])
            return result

        if attempt < MAX_RETRIES:
            logger.get_logger().warning(
                f"API 오류, {RETRY_INTERVAL_SECONDS}초 후 재시도 "
                f"({attempt}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_INTERVAL_SECONDS)
        else:
            error_msg = (
                f"status={data.get('status')}, message={data.get('message', '')}"
            )
            logger.get_logger().error(
                f"API 요청 최종 실패 (page {page_no}): {error_msg}"
            )
            raise RuntimeError(f"DART API 최종 실패 (page {page_no}): {error_msg}")

    # 루프를 정상 통과하면 도달 수 없는 코드이지만 타입 체커를 위해 유지
    return []  # pragma: no cover


# ---------------------------------------------------------------------------
# 페이지네이션 + 신규 공시 필터링
# ---------------------------------------------------------------------------


def fetch_disclosures(
    api_key: str, bgn_date: str, last_rcept_no: Optional[str] = None
) -> list[dict[str, Any]]:
    """전체 공시를 페이지네이션으로 가져오고, last_rcept_no보다 큰 신규 공시만 반환한다.

    조기 종료 조건:
    1. 응답 공시 중 last_rcept_no보다 큰 것이 하나도 없는 경우
    2. 응답 건수가 PAGE_SIZE 미만인 경우 (마지막 페이지)
    """
    all_items: list[dict[str, Any]] = []
    page_no = 1

    while True:
        items = _fetch_page(api_key, bgn_date, page_no)
        logger.get_logger().info(f"API 호출: page={page_no}, 응답={len(items)}건")

        if last_rcept_no is not None:
            new_items = [i for i in items if i["rcept_no"] > last_rcept_no]
            all_items.extend(new_items)

            # 이 페이지에 신규 공시가 하나도 없으면 조기 종료
            if not new_items:
                break
        else:
            all_items.extend(items)

        # 마지막 페이지 판단
        if len(items) < PAGE_SIZE:
            break

        page_no += 1

    return all_items
