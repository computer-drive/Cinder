from queue import Queue

from ..control.control import Cursor

class Element:
    '''
    元素基类
    '''
    def __init__(self, input: Queue[str], output: Queue['Element']):
        self.input = input
        self.output = output

    def render(self):
        raise NotImplementedError


class StopEvent(Element):
    '''
    停止事件
    '''
    pass

class Line(Element):
    '''
    输出一行文本
    '''
    def __init__(self, input: Queue[str], output: Queue['Element'], text: str):
        super().__init__(input, output)

        self.text = text

    def render(self):
        print(self.text)

class Text(Element):
    '''
    输出文本
    '''

    def __init__(self, input: Queue[str], output: Queue['Element'], text: str):
        super().__init__(input, output)

        self.text = text

    def render(self):
        print(self.text, end="")

class Overwrite(Line):
    r'''
    覆盖输出一行文本（类似\r）
    '''
    def render(self):
        print("\r"+self.text, end="")
        Cursor.clear_to_eol()

class Input(Element):
    '''
    输入元素
    '''

    def __init__(self, input: Queue[str], output: Queue['Element'], prompt: str = ''):
        super().__init__(input, output)

        self.prompt = prompt

    def render(self):
        self.input.put(input(self.prompt))

    def get_input(self):
        '''
        获取用户输入
        '''
        return self.input.get()


        
