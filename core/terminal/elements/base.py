'''
这是控制台渲染部分的基础组件部分
'''
from enum import Enum, auto
from shutil import get_terminal_size
import wcwidth

from ..control import Cursor, Style
from .element import Element

class BaseElement(Element):

    def draw(self):
        '''将组件绘制到屏幕上'''
        raise NotImplementedError

    def get_text(self):
        '''返回要将组件绘制到屏幕上的文本'''
        raise NotImplementedError

class TextType(Enum):
    TEXT = auto() # 普通文本print
    LINE = auto() # 换行文本println
    OVERWRITE = auto() # 覆写文本overwrite


class TextElement(BaseElement):

    def __init__(self, text: str, text_type: TextType = TextType.TEXT):
        self.text = text
        self.text_type = text_type

    def draw(self):
        if self.text_type == TextType.LINE:
            Cursor.println(self.text)
        elif self.text_type == TextType.OVERWRITE:
            Cursor.overwrite(self.text)
        else:
            Cursor.print(self.text)

    def get_text(self):
        return self.text

class TitleElement(BaseElement):

    def __init__(self, text: str):
        self.text = text

    def draw(self):
        space_length = (get_terminal_size().columns - wcwidth.wcswidth(self.text))

        left_length, right_length = 0, 0
        # 判断能否整除于2
        if space_length % 2 == 0:
            left_length = right_length = space_length // 2
        else:
            left_length = (space_length - 1) // 2
            right_length = left_length + 1

        Cursor.print("=" * left_length + f"{Style.invert}{self.text}{Style.reset}" + "=" * right_length)


    
