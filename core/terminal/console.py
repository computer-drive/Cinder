from queue import Queue
from threading import Event
from typing import Callable

from .elements import Element
from .elements.base import TextElement, TextType, TitleElement
from .elements.live import Spinner
from .elements.prompt import Confirm, Choose, Input
from .control import Fore, Style


class Console:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is not None:
            return cls._instance
        else:
            raise ValueError("Console还未被创建过")

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
        '''输出一些文本并覆盖当前行'''
        self.put(TextElement(text, TextType.OVERWRITE))

    def title(self, text: str):
        '''输出一个标题'''
        self.put(TitleElement(text))

    def stop(self):
        '''停止渲染器的运行'''
        self.output_queue.put(None)
        # self.stop_event.set() # ! stop_event有问题，先不用它！

    def warning(self, text: str, prefix: bool = True):
        '''输出警告信息'''
        self.println(f"{Fore.yellow}{"警告：" if prefix else ""}{text}{Style.reset}")

    def error(self, text: str, prefix: bool = True):
        self.println(f"{Fore.red}{"错误：" if prefix else ""}{text}{Style.reset}")

    def success(self, text: str, prefix: bool = True):
        self.println(f"{Fore.green}{"成功：" if prefix else ""}{text}{Style.reset}")

    def spinner(self, text: str):
        '''输出一个旋转的加载图标'''
        spinner = Spinner(self.output_queue, text)
        self.put(spinner)

        return spinner

    def confirm(self, prompt: str, default: bool = True) -> bool:
        el = Confirm(self.input_queue, prompt, default)

        self.put(el)

        return self.input_queue.get() == "1"

    def choose(self, prompt: str, choices: list[str], default: int = 0, allow_cancel: bool = False) -> str:
        el = Choose(self.input_queue, prompt, choices, default, allow_cancel)
        self.put(el)

        return self.input_queue.get()

    def input(self, prompt: str, validation: Callable[[str], bool] | None = None) -> str:

        el = Input(prompt, validation)
        self.put(el)

        return self.input_queue.get()