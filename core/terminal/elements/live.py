'''
这是控制台渲染部分动态组件的部分
'''

from queue import Queue, Empty
from enum import Enum, auto
import sys

from .base import BaseElement
from .element import Element
from ..control import Cursor

STOP_SIGNAL = sentinel("STOP_SIGNAL")


class LiveElement(Element):

    def __init__(self, output_queue: Queue[Element | None]):
        self.output_queue = output_queue

    def update(self) -> None | STOP_SIGNAL:
        raise NotImplementedError

######## 以上是基础内容

SPINNER_CHAR = ['⠈', '⠐', '⠠', '⢀', '⡀', '⠄', '⠂', '⠁']
SPINNER_CHAR1 = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
SPINNER_CHAR2 = ['⣷', '⣯', '⣟', '⡿', '⢿', '⣻', '⣽', '⣾']

FINISH_CHAR = '✔'
ERROR_CHAR = '×'

class SpinnerState(Enum):
    LOADING = auto()
    LOADING1 = auto()
    LOADING2 = auto()
    FINISH = auto()
    ERROR = auto()


class Spinner(LiveElement):
    def __init__(self, output_queue: Queue[Element | None], text: str):
        super().__init__(output_queue)

        self.state: SpinnerState = SpinnerState.LOADING
        self.index = 0

        self.text = text

    def set_text(self, text: str):
        self.text = text

    def finish(self, text: str):
        self.state = SpinnerState.FINISH
        self.text = text

    def error(self, text: str):
        self.state = SpinnerState.ERROR
        self.text = text

    def loading1(self, text: str):
        self.state = SpinnerState.LOADING1
        self.text = text

    def loading2(self, text: str):
        self.state = SpinnerState.LOADING2
        self.text = text

    def update(self) -> None | STOP_SIGNAL:
        try:
            el = self.output_queue.get_nowait()
        except Empty:
            pass
        else:
            # 有组件时
            if el is not None and isinstance(el, BaseElement):
                Cursor.overwrite(el.get_text() + "\n")
        
        if self.state == SpinnerState.FINISH:
            Cursor.println(f"\r{FINISH_CHAR} {self.text}")
            return STOP_SIGNAL
        elif self.state == SpinnerState.ERROR:
            Cursor.println(f"\r{ERROR_CHAR} {self.text}")
            return STOP_SIGNAL
        else:
            chars = {
                SpinnerState.LOADING: SPINNER_CHAR,
                SpinnerState.LOADING1: SPINNER_CHAR1,
                SpinnerState.LOADING2: SPINNER_CHAR2,
            }[self.state]

            if self.index > len(chars) - 1:
                self.index = 0

            Cursor.overwrite(f"{chars[self.index]} {self.text}")
            self.index += 1
        
        

