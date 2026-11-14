'''
这是控制台渲染部分动态组件的部分
'''

from queue import Queue, Empty
from enum import Enum, auto
from threading import Event

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
    def __init__(self, output_queue: Queue[Element | None], text: str, state: SpinnerState = SpinnerState.LOADING):
        super().__init__(output_queue)

        self.state: SpinnerState = state
        self.index = 0

        self.text = text

        self.update_state_event: Event | None = None

    def set_text(self, text: str):
        self.text = text

    def finish(self, text: str):
        self.state = SpinnerState.FINISH
        self.text = text

        self.update_state_event = Event()
        return self.update_state_event

    def error(self, text: str):
        self.state = SpinnerState.ERROR
        self.text = text

    def loading1(self, text: str | None = None):
        self.state = SpinnerState.LOADING1
        if text is not None:
            self.text = text

    def loading2(self, text: str | None):
        self.state = SpinnerState.LOADING2
        if text is not None:
            self.text = text

    def loading0(self, text: str | None):
        self.state = SpinnerState.LOADING
        if text is not None:
            self.text = text


    def update(self) -> None | STOP_SIGNAL:
        Cursor.hide()


        while True:
            try:
                el = self.output_queue.get_nowait()
            except Empty:
                break

            else:
                # 有组件时
                if el is not None and isinstance(el, BaseElement):
                    Cursor.overwrite(el.get_text() + "\n")
                else:
                    if el is None:
                        self.output_queue.put(None)

                        Cursor.show()
                        return STOP_SIGNAL
                    
                    self.output_queue.put(el)

                    Cursor.show()
                    return STOP_SIGNAL
        
        if self.state == SpinnerState.FINISH:
            Cursor.overwrite(f"{FINISH_CHAR} {self.text}")
            Cursor.println("")

            Cursor.show()

            if self.update_state_event is not None:
                self.update_state_event.set()

            return STOP_SIGNAL
        
        elif self.state == SpinnerState.ERROR:
            Cursor.overwrite(f"{ERROR_CHAR} {self.text}\n")
            Cursor.println("")

            if self.update_state_event is not None:
                self.update_state_event.set()

            Cursor.show()
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

        
        

