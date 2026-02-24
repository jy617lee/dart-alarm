"""DART OpenAPI 폴링 스크립트 - 키워드 매칭 공시를 결과 파일에 저장한다."""

import datetime

import dart_api


def run() -> None:
    """단일 실행 진입점. 인프라단에서 반복 호출된다."""
    api_key = dart_api.load_api_key()
    bgn_date = datetime.date.today().strftime("%Y%m%d")
    items = dart_api.fetch_disclosures(api_key, bgn_date)
    dart_api.print_disclosures(items)


if __name__ == "__main__":  # pragma: no cover
    run()
