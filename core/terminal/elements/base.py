'''
这是控制台渲染部分的基础组件部分
'''
from enum import Enum, auto

from ..control.control import Cursor
from .element import Element

class BaseElement(Element):

    def draw(self):
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

    
