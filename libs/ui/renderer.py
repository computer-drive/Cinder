import sys
from queue import Queue

from .elements.base import StopEvent, Element, Overwrite, Line
from .elements.log import LogManager, INFO, _Log

class Renderer:

    def __init__(self, input: Queue[str], output: Queue[Element]):
        self.current_line_width = 0

        self.input = input
        self.output = output

        self.log_manager = LogManager(INFO, "logs")

        self.at_line_start = True

    def run(self):

        while True:
            element: Element  = self.output.get()

            # print(element)

            if isinstance(element, StopEvent):
                # 判断是否为停止事件
                break

            elif isinstance(element, _Log):
                element.log(self.log_manager)

                

            else:
                if type(element) is Line and not self.at_line_start:
                    print() # 换行
                    self.at_line_start = True

                element.render()

                if isinstance(element, Overwrite):
                    self.at_line_start = False

                


    