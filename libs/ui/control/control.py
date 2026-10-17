from .base import _ESC
import sys

class Cursor:
    '''
    光标控制类
    '''
    _HIDE_CURSOR = f'{_ESC}?25l'
    _SHOW_CURSOR = f'{_ESC}?25h'
    _CLEAR_SCREEN = f'{_ESC}2J'

    @classmethod
    def hide(cls):
        '''隐藏光标'''
        sys.stdout.write(cls._HIDE_CURSOR)
        sys.stdout.flush()

    @classmethod
    def show(cls):
        '''显示光标'''
        sys.stdout.write(cls._SHOW_CURSOR)
        sys.stdout.flush()

    @classmethod
    def up(cls, count: int = 1):
        '''上移光标'''
        sys.stdout.write(f'{_ESC}{count}A')
        sys.stdout.flush()

    @classmethod
    def down(cls, count: int = 1):
        '''下移光标'''
        sys.stdout.write(f'{_ESC}{count}B')
        sys.stdout.flush()

    @classmethod
    def left(cls, count: int = 1):
        '''左移光标'''
        sys.stdout.write(f'{_ESC}{count}D')
        sys.stdout.flush()

    @classmethod
    def right(cls, count: int = 1):
        '''右移光标'''
        sys.stdout.write(f'{_ESC}{count}C')
        sys.stdout.flush()

    @classmethod
    def move(cls, x: int, y: int):
        '''移动光标到指定位置'''
        sys.stdout.write(f'{_ESC}{y};{x}H')
        sys.stdout.flush()

    @classmethod
    def clear(cls):
        '''清除屏幕'''
        sys.stdout.write(cls._CLEAR_SCREEN)
        sys.stdout.flush()



class Scroll:
    '''
    滚动区域控制类
    '''
    @classmethod
    def set(cls, top: int, bottom: int):
        '''设置滚动区域'''
        sys.stdout.write(f'{_ESC}10{top};{bottom}t')
        sys.stdout.flush()

    @classmethod
    def recover(cls):
        '''恢复滚动区域'''
        sys.stdout.write(f'{_ESC}100t')
        sys.stdout.flush()

    


    
