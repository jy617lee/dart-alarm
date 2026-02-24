"""main.run() 동작 테스트."""

import main


def test_run_does_not_raise() -> None:
    """run()이 예외 없이 실행되어야 한다."""
    main.run()
