from queue import Queue
from typing import TypeVar

from .elements.base import Element, Line, Overwrite, Input, StopEvent, Text

T = TypeVar("T", bound=Element)

class Manager:
    def __init__(self, input: Queue[str], output: Queue[Element]):
        self.q_output = output
        self.q_input = input

    def println(self, text: str):
        '''输出一行文本'''
        self.q_output.put(
            Line(self.q_input, self.q_output, text)
        )

    def print(self, text: str):
        '''输出文本'''
        self.q_output.put(
            Text(self.q_input, self.q_output, text)
        )

    def overwrite(self, text: str):
        '''覆盖输出一行文本（类似\r）'''
        self.q_output.put(
            Overwrite(self.q_input, self.q_output, text)
        )

    def input(self, prompt: str = ''):
        '''获取用户输入'''
        el = Input(self.q_input, self.q_output, prompt)

        self.q_output.put(el)
        
        return el.get_input()

    def stop(self):
        '''停止渲染'''
        self.q_output.put(StopEvent(self.q_input, self.q_output))

    def get_queue(self):
        '''
        获取输入队列和输出队列
        '''
        return self.q_input, self.q_output

    def add(self, el: T) -> T:
        '''
        添加元素到渲染队列
        '''
        self.q_output.put(el)
        return el


