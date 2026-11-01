from queue import Queue
from typing import Literal
from shutil import get_terminal_size

from readchar import readkey
from readchar import key as KEY
from wcwidth import wcswidth

from ..control import Cursor, Style, Fore
from .element import Element


class PromptElement(Element):
    def __init__(self, input_queue: Queue[str]):
        self.input_queue = input_queue

    def run(self) -> str:
        raise NotImplementedError

class Confirm(PromptElement):
    def __init__(self, input_queue: Queue[str], prompt: str, default: bool = True):
        super().__init__(input_queue)
        self.prompt = prompt
        self.default = default

    def run(self):
        Cursor.hide()

        current = self.default
        is_selected = False

    
        while True:
            Cursor.overwrite(
                        f"{self.prompt}（{f"{Style.invert}Yes{Style.reset}/N" if current else f"Y/{Style.invert}No{Style.reset}"}）" 
                    )

            if is_selected:
                break

            try:
                key = readkey()
            except KeyboardInterrupt:
                continue

            if key in ["Y", "y"]:
                current = True
                is_selected = True

            elif key in ["N", "n"]:
                current = False
                is_selected = True

            elif key in [KEY.UP, KEY.LEFT]:
                current = True

            elif key in [KEY.DOWN, KEY.RIGHT]:
                current = False

            elif key == KEY.ENTER:
                break
   
        Cursor.show()
        Cursor.println("")
        return "1" if current else "0"
            
UNSELECTED_CHAR = "-"
SELECTED_CHAR = ">"

def truncate_to_width(text: str, max_width: int, ellipsis: str = "…") -> str:
    """按显示宽度截断字符串，超出部分用省略号代替"""
    if wcswidth(text) <= max_width:
        return text

    ell_width = wcswidth(ellipsis)
    limit = max_width - ell_width

    # 逐字符累加宽度，找到能放下的最长前缀
    width = 0
    result = []
    for ch in text:
        w = wcswidth(ch)
        if w < 0:          # 不可打印字符，跳过或按 0 处理
            w = 0
        if width + w > limit:
            break
        result.append(ch)
        width += w

    return "".join(result) + ellipsis


class Choose(PromptElement):
    
    def __init__(self, input_queue: Queue[str],
                prompt: str,
                choices: list[str],
                defualt: int,
                allow_cancel: bool = False):
        
        self.prompt = prompt
        self.choices = choices
        self.default = defualt
        self.allow_cancel = allow_cancel

    def run(self):
        Cursor.hide()

        current = self.default


        Cursor.println(self.prompt)
        for index, choice in enumerate(self.choices):

            if index == current:
                
                text = f"{Style.invert}{SELECTED_CHAR} {choice}"
            else:
                text = f"{UNSELECTED_CHAR} {choice}"

            if wcswidth(text) > get_terminal_size().columns:
                text = truncate_to_width(text, get_terminal_size().columns)

            # if index == current:
            #     text += " " * (get_terminal_size().columns - wcswidth(text))
            
            Cursor.println(f"{text}{Style.reset}")


        # 上移光标
        Cursor.up(len(self.choices) - current)

        current_value = None
        
        while True:
            try:
                key = readkey()
            except KeyboardInterrupt:
                if self.allow_cancel:
                    current_value = "cancel"
                    break
                else:

                    # 上移到prompt行
                    Cursor.up( current + 1)

                    Cursor.print(f"\r{Fore.red}（不允许取消）{Style.reset}{self.prompt}")

                    Cursor.down( current + 1)


            else:

                if key == KEY.ENTER:
                    current_value = self.choices[current]

                    Cursor.down(len(self.choices) - current + 1)
                    Cursor.print("\r")
                    break

                
                elif key == KEY.UP and current > 0:
                    # print(current, "-")
                    Cursor.overwrite(f"{UNSELECTED_CHAR} {self.choices[current]}")
                    current -= 1
                    
                    Cursor.up(1)
                    Cursor.overwrite(f"{Style.invert}{SELECTED_CHAR} {self.choices[current]}{Style.reset}")

                elif key == KEY.DOWN and current < len(self.choices) - 1:

                    Cursor.overwrite(f"{UNSELECTED_CHAR} {self.choices[current]}")
                    current += 1
                
                    Cursor.down(1)
                    Cursor.overwrite(f"{Style.invert}{SELECTED_CHAR} {self.choices[current]}{Style.reset}")
                    

        Cursor.show()

        return current_value


                


                

            
            

        


        
