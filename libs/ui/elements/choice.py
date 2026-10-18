from queue import Queue

import readchar

from .base import Element
from ..control.control import Cursor
from ..control.style import Style

class Choose(Element):
    '''
    选择元素
    '''

    def __init__(self, input: Queue, output: Queue, prompt: str, choices: list[str]):
        super().__init__(input, output)
        self.prompt = prompt
        self.choices = choices

    def get_choice(self):
        '''
        获取用户选择
        '''
        return self.input.get()

    def render(self):
        current_choice = 0

        print(self.prompt)


        for i, choice in enumerate(self.choices):
            if i == current_choice:
                print(f"{Style.invert}> {choice}{Style.reset}")
            else:
                print(f"- {choice}")

        Cursor.up(len(self.choices))
        # Cursor.hide()

        while True:
            key = readchar.readkey()

            if key == readchar.key.UP:
                if current_choice > 0:
                    
                    Cursor.overwrite(f"- {self.choices[current_choice]}")

                    current_choice -= 1
                    Cursor.up()
                    Cursor.overwrite(f"{Style.invert}> {self.choices[current_choice]}{Style.reset}")

            elif key == readchar.key.DOWN:
                if current_choice < len(self.choices) - 1:
                    Cursor.overwrite(f"- {self.choices[current_choice]}")
                    current_choice += 1
                    Cursor.down()
                    Cursor.overwrite(f"{Style.invert}> {self.choices[current_choice]}{Style.reset}")

            elif key == readchar.key.ENTER:
                self.input.put(self.choices[current_choice])

                print("\n" * (len(self.choices) - current_choice ), end="")
                Cursor.show()
                break

            

        
