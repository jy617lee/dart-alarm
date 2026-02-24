"""DART OpenAPI 공시 목록 조회 모듈."""

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

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
# 공시 목록 조회
# ---------------------------------------------------------------------------


def fetch_disclosures(api_key: str, bgn_date: str) -> list[dict[str, Any]]:
    """DART 공시 목록 API를 호출하고 결과를 반환한다.

    - 일반 오류(status != 000): 최대 MAX_RETRIES회 재시도, 간격 RETRY_INTERVAL_SECONDS초
    - 429 Too Many Requests: Exponential Backoff (BACKOFF_BASE_SECONDS * 2^n 초 대기)
    """
    params: dict[str, Any] = {
        "crtfc_key": api_key,
        "bgn_de": bgn_date,
        "page_count": PAGE_SIZE,
    }
    backoff_exponent = 0

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.get(DART_API_URL, params=params, timeout=10)

        if response.status_code == HTTP_TOO_MANY_REQUESTS:
            wait = BACKOFF_BASE_SECONDS * (2**backoff_exponent)
            time.sleep(wait)
            backoff_exponent += 1
            continue

        data: dict[str, Any] = response.json()
        if data.get("status") == STATUS_OK:
            result: list[dict[str, Any]] = data.get("list", [])
            return result

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_INTERVAL_SECONDS)

    return []


# ---------------------------------------------------------------------------
# 출력
# ---------------------------------------------------------------------------


def print_disclosures(items: list[dict[str, Any]]) -> None:
    """공시 목록을 콘솔에 출력한다."""
    for item in items:
        print(f"[{item['rcept_no']}] {item['corp_name']} - {item['report_nm']}")
