from queue import Queue
from threading import Event

from .elements import Element
from .elements.base import TextElement, TextType


class Console:
    def __init__(self, input_queue: Queue[str], output_queue: Queue[Element | None], stop_event: Event):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.stop_event = stop_event

    def put(self, element: Element):
        '''将一个组件放入输出渲染队列'''
        self.output_queue.put(element)

    def print(self, text: str):
        '''输出一些文本'''
        self.put(TextElement(text))

    def println(self, text: str):
        '''输出一些文本并换行'''
        self.put(TextElement(text, TextType.LINE))

    def overwrite(self, text: str):
        self.put(TextElement(text, TextType.OVERWRITE))

    def stop(self):
        self.output_queue.put(None)
        self.stop_event.set()
        