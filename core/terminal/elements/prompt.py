from queue import Queue
from typing import Literal


from readchar import readkey
from readchar import key as KEY

from ..control import Cursor, Style
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
            
UNSELECTED_CHAR = "○"
SELECTED_CHAR = "●"


        

class Choose(PromptElement):
    
    def __init__(self, input_queue: Queue[str],
                prompt: str,
                choices: list[str],
                allow_cancel: bool = False,
                style: Literal["vertical", "horizontal"] = "vertical"):
        
        self.prompt = prompt
        self.choices = choices
        self.allow_cancle = allow_cancel
        self.style = style
        


        
