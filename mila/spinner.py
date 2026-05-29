import sys
import threading
import time

from mila.style import C, step_pass, step_fail, step_warn


class Spinner:
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    FRAME_INTERVAL = 0.08
    MIN_DURATION = 0.18

    def __init__(self, text: str) -> None:
        self.text = text
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time = 0.0
        self._done = False

    def start(self) -> "Spinner":
        self._start_time = time.monotonic()
        sys.stdout.write(C.HIDE_CURSOR)
        sys.stdout.flush()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __enter__(self) -> "Spinner":
        return self.start()

    def __exit__(self, exc_type, exc_val, tb) -> None:
        if not self._done:
            self._finish()

    def _loop(self) -> None:
        i = 0
        while not self._stop.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(f"\r{C.CLEAR_LINE}   {C.MAG}{frame}{C.R} {self.text}")
            sys.stdout.flush()
            time.sleep(self.FRAME_INTERVAL)
            i += 1

    def _finish(self) -> None:
        if self._done:
            return
        self._done = True
        elapsed = time.monotonic() - self._start_time
        if elapsed < self.MIN_DURATION:
            time.sleep(self.MIN_DURATION - elapsed)
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r" + C.CLEAR_LINE + C.SHOW_CURSOR)
        sys.stdout.flush()

    def succeed(self, text: str | None = None) -> None:
        self._finish()
        step_pass(text or self.text)

    def fail(self, text: str | None = None) -> None:
        self._finish()
        step_fail(text or self.text)

    def warn(self, text: str | None = None) -> None:
        self._finish()
        step_warn(text or self.text)

    def stop(self) -> None:
        self._finish()


class LazySpinner:
    def __init__(self) -> None:
        self._sp: Spinner | None = None

    def __enter__(self) -> "LazySpinner":
        return self

    def __exit__(self, exc_type, exc_val, tb) -> None:
        if self._sp is not None:
            self._sp.stop()

    def update(self, text: str) -> None:
        if self._sp is None:
            self._sp = Spinner(text).start()
        else:
            self._sp.text = text

    def succeed(self, text: str) -> None:
        if self._sp is None:
            step_pass(text)
        else:
            self._sp.succeed(text)

    def fail(self, text: str) -> None:
        if self._sp is None:
            step_fail(text)
        else:
            self._sp.fail(text)
