'''
这是控制台渲染部分动态组件的部分
'''

from queue import Queue

from .base import BaseElement
from .element import Element

STOP_SIGNAL = sentinel("STOP_SIGNAL")

class LiveElement(Element):

    def __init__(self, output_queue: Queue[BaseElement]):
        self.output_queue = output_queue

    def update(self) -> None | STOP_SIGNAL:
        raise NotImplementedError

