from queue import Queue
import os
from datetime import datetime

from .base import Element
from ..control.style import Fore, Style

DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3


class LogManager:
    '''
    日志管理类
    '''

    def __init__(self, level: int, log_path: str):
        self.level = level

        self.log_path = log_path
        self.log_file = self.get_log_file()
        self.current_file = open(os.path.join(self.log_path, self.log_file), 'a')

    @staticmethod
    def get_log_file():
        return datetime.now().strftime('%Y%m%d') + '.log'

    def log(self, message: str, level: int, levelname: str):

        if self.get_log_file() != self.log_file:
            self.current_file.close()

            self.log_file = self.get_log_file()
            self.current_file = open(os.path.join(self.log_path, self.log_file), 'a')
            
        if level >= self.level:
            print(f'{levelname}{message}')
            self.current_file.write(f'{levelname}{message}\n')

    def close(self):
        self.current_file.close()

    def debug(self, message: str):
        self.log(message, DEBUG, f'{Fore.light_blue}调试：{Style.reset}')

    def info(self, message: str):
        self.log(message, INFO, f'{Fore.light_green}信息：{Style.reset}')

    def warning(self, message: str):
        self.log(message, WARNING, f'{Fore.light_yellow}警告：{Style.reset}')

    def error(self, message: str):
        self.log(message, ERROR, f'{Fore.light_red}错误：{Style.reset}')


class _Log(Element):
    '''
    日志输出元素基类
    '''

    def __init__(self, input: Queue[str], output: Queue['Element'], message: str, level: int):
        super().__init__(input, output)

        self.message = message
        self.level = level

    def log(self, log_manager: LogManager):
        handlers = {
            DEBUG:   log_manager.debug,
            INFO:    log_manager.info,
            WARNING: log_manager.warning,
            ERROR:   log_manager.error,
        }
        if self.level in handlers:
            handlers[self.level](self.message)
        else:
            handlers[INFO](self.message)

            


