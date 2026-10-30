from .base import _ESC
import sys

class Cursor:
    '''
    光标控制类
    '''
    _HIDE_CURSOR = f'{_ESC}?25l'
    _SHOW_CURSOR = f'{_ESC}?25h'
    _CLEAR_SCREEN = f'{_ESC}2J'
    _CLEAR_TO_EOL = f'{_ESC}K'

    @classmethod
    def hide(cls):
        '''隐藏光标'''
        sys.stdout.write(cls._HIDE_CURSOR)


    @classmethod
    def show(cls):
        '''显示光标'''
        sys.stdout.write(cls._SHOW_CURSOR)


    @classmethod
    def up(cls, count: int = 1):
        '''上移光标'''
        sys.stdout.write(f'{_ESC}{count}A')


    @classmethod
    def down(cls, count: int = 1):
        '''下移光标'''
        sys.stdout.write(f'{_ESC}{count}B')


    @classmethod
    def left(cls, count: int = 1):
        '''左移光标'''
        sys.stdout.write(f'{_ESC}{count}D')


    @classmethod
    def right(cls, count: int = 1):
        '''右移光标'''
        sys.stdout.write(f'{_ESC}{count}C')


    @classmethod
    def move(cls, x: int, y: int):
        '''移动光标到指定位置'''
        sys.stdout.write(f'{_ESC}{y};{x}H')


    @classmethod
    def clear(cls):
        '''清除屏幕，并将光标移动到屏幕顶部'''
        sys.stdout.write(cls._CLEAR_SCREEN)
        sys.stdout.write(f'{_ESC}1;1H')

    @classmethod
    def clear_to_eol(cls):
        '''清除文本到行尾'''
        sys.stdout.write(cls._CLEAR_TO_EOL)

    @classmethod
    def overwrite(cls, text: str):
        '''覆盖当前行文本（类似\r）'''
        
        sys.stdout.write("\r" + text)
        cls.clear_to_eol()

        sys.stdout.flush()

    @classmethod
    def print(cls, text: str):
        sys.stdout.write(text)

    @classmethod
    def println(cls, text: str):
        cls.print(text + '\n')


class Scroll:
    '''
    滚动区域控制类
    '''
    @classmethod
    def set(cls, top: int, bottom: int):
        '''设置滚动区域'''
        sys.stdout.write(f'{_ESC}10{top};{bottom}t')


    @classmethod
    def recover(cls):
        '''恢复滚动区域'''
        sys.stdout.write(f'{_ESC}100t')
