from queue import Queue
from enum import Enum, auto
import time

from .base import Element
from ..control.control import Cursor

CIRCULAR_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

WAVE_CHARS = ['█▇▆▅▄▃▂▁', '▇█▇▆▅▄▃▂', '▆▇█▇▆▅▄▃', '▅▆▇█▇▆▅▄', '▄▅▆▇█▇▆▅', '▃▄▅▆▇█▇▆', '▂▃▄▅▆▇█▇',  '▁▂▃▄▅▆▇█', '▂▃▄▅▆▇█▇', '▃▄▅▆▇█▇▆', '▄▅▆▇█▇▆▅', '▅▆▇█▇▆▅▄', '▆▇█▇▆▅▄▃', '▇█▇▆▅▄▃▂']

FINISHED_CHAR = "✓"
ERROR_CHAR = "×"


class CircularStatus(Enum):
    RUNNING = auto()
    FINISHED = auto()
    ERROR = auto()
    STOPPED = auto()


class Progress(Element):

    def __init__(self, input: Queue[str], output: Queue[Element], message: str = "", progress_text: list[str] = CIRCULAR_CHARS) -> None:
        super().__init__(input, output)
        self.message = message

        self.status = CircularStatus.RUNNING
        self.progress_text = progress_text

    def finish(self, message: str | None = None):
        self.status = CircularStatus.FINISHED

        if message is not None:
            self.message = message

    def error(self, message: str | None = None):
        self.status = CircularStatus.ERROR

    def update(self, message: str):
        self.message = message

    def stop(self):
        self.status = CircularStatus.STOPPED

    def render(self):
        i = 0
        while True:
            # print(self.status)
            if self.status == CircularStatus.RUNNING:
                Cursor.overwrite(f"{self.progress_text[i]} {self.message}")
                # print(i, len(self.progress_text[i]), )
                i += 1

                if i >= len(self.progress_text):
                    i = 0

            elif self.status == CircularStatus.FINISHED:
                Cursor.overwrite(f"\r{FINISHED_CHAR} {self.message}")
                print()
                break

            elif self.status == CircularStatus.ERROR:
                Cursor.overwrite(f"\r{ERROR_CHAR} {self.message}")
                print()
                break

            elif self.status == CircularStatus.STOPPED:
                print()
                break

            else:
                break

            time.sleep(1/12)
            



