from collections.abc import Callable


class SignalReporter:
    def __init__(self, emit: Callable[[str], None]) -> None:
        self._emit = emit

    def __enter__(self) -> "SignalReporter":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def update(self, text: str) -> None:
        self._emit(text)

    def succeed(self, text: str) -> None:
        self._emit(text)

    def fail(self, text: str) -> None:
        self._emit(text)
