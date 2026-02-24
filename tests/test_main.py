"""main.run() 동작 테스트."""

from unittest.mock import patch

import main


def test_run_does_not_raise() -> None:
    """run()이 API 키와 응답을 mock했을 때 예외 없이 실행되어야 한다."""
    with (
        patch("dart_api.load_api_key", return_value="test-key"),
        patch("dart_api.fetch_disclosures", return_value=[]),
    ):
        main.run()
