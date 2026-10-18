from queue import Queue
from enum import Enum, auto
import shutil
import time

from .base import Element
from ..control.control import Cursor

CIRCULAR_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

WAVE_CHARS = ['█▇▆▅▄▃▂▁', '▇█▇▆▅▄▃▂', '▆▇█▇▆▅▄▃', '▅▆▇█▇▆▅▄', '▄▅▆▇█▇▆▅', '▃▄▅▆▇█▇▆', '▂▃▄▅▆▇█▇',  '▁▂▃▄▅▆▇█', '▂▃▄▅▆▇█▇', '▃▄▅▆▇█▇▆', '▄▅▆▇█▇▆▅', '▅▆▇█▇▆▅▄', '▆▇█▇▆▅▄▃', '▇█▇▆▅▄▃▂']

FINISHED_CHAR = "✓"
ERROR_CHAR = "×"

BLOCK_CHAR = "█"
EMPTY_CHAR = "░"


class CircularStatus(Enum):
    RUNNING = auto()
    FINISHED = auto()
    ERROR = auto()
    STOPPED = auto()


class Spinner(Element):
    '''
    转动条元素
    '''
    def __init__(self, input: Queue[str], output: Queue[Element], message: str = "", progress_text: list[str] = CIRCULAR_CHARS) -> None:
        super().__init__(input, output)
        self.message = message

        self.status = CircularStatus.RUNNING
        self.progress_text = progress_text

    def finish(self, message: str | None = None):
        self.status = CircularStatus.FINISHED

        if message is not None:
            self.message = message

    def error(self, message: str | None = None):
        self.status = CircularStatus.ERROR

    def update(self, message: str):
        self.message = message

    def stop(self):
        self.status = CircularStatus.STOPPED

    def render(self):
        i = 0
        while True:
            # print(self.status)
            if self.status == CircularStatus.RUNNING:
                Cursor.overwrite(f"{self.progress_text[i]} {self.message}")
                # print(i, len(self.progress_text[i]), )
                i += 1

                if i >= len(self.progress_text):
                    i = 0

            elif self.status == CircularStatus.FINISHED:
                Cursor.overwrite(f"\r{FINISHED_CHAR} {self.message}")
                print()
                break

            elif self.status == CircularStatus.ERROR:
                Cursor.overwrite(f"\r{ERROR_CHAR} {self.message}")
                print()
                break

            elif self.status == CircularStatus.STOPPED:
                print()
                break

            else:
                break

            time.sleep(1/12)

class ProgressBar(Element):
    '''
    进度条元素
    '''
    def __init__(self,
                input:           Queue[str],
                output:          Queue[Element],
                message:         str = "",
                current:         int = 0,
                total:           int = 100,
                block_char:      str = BLOCK_CHAR,
                empty_char:      str = EMPTY_CHAR,
                format:          str = "{message} [{progress}]",
                progress_length: int = 20,
                ) -> None:
        '''
        初始化进度条元素。
        :param current: 当前进度，当current = -1 时，表示为不确定状态。
        :param progress_length: 进度条长度，当progress_length为零或负数时，将按照当前终端行宽度减少该值计算宽度
        '''
        super().__init__(input, output)
        self.message = message
        self.current = current
        self.total = total
        self.block_char = block_char
        self.empty_char = empty_char
        self.format = format
        self.progress_length = progress_length

    def update(self, current: int, message: str | None = None, total: int | None = None):
        '''
        更新进度条进度
        '''
        self.current = current
        if total is not None:
            self.total = total

        if message is not None:
            self.message = message

    def render(self):
        # 这是当进度条处于不确定状态时使用的变量
        block_position = 0
        block_length = 10


        while True:
            # 计算进度条长度
            if self.progress_length <= 0:
                # 获取终端行宽度
                progress_length = shutil.get_terminal_size().columns + self.progress_length
            else:
                progress_length = self.progress_length

            if self.current == -1:
                progress_text = ""

                if (self.progress_length - block_position) >= block_length:
                    progress_text += self.empty_char * block_position

                    progress_text += block_length * self.block_char

                    progress_text += (progress_length - block_position - block_length) * self.empty_char
        
                else:
                    # 进度条超出范围，在前面显示
                    font_length = block_length - (self.progress_length - block_position)

                    progress_text += self.block_char * font_length

                    # 补充空格到进度条长度
                    progress_text += (block_position - font_length) * self.empty_char

                    # 补充空格到进度条长度
                    progress_text += (block_length - font_length) * self.block_char

                block_position += 1
                if block_position >= progress_length:
                    block_position = 0

            else:
                current_count = int((self.current / self.total) * progress_length)
                progress_text = self.block_char * current_count + self.empty_char * (progress_length - current_count)

            

            progress = self.format.format(message=self.message, progress=progress_text)

            Cursor.overwrite(progress)

            time.sleep(1 / 24)




        
            



