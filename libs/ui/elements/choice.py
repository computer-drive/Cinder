from queue import Queue

import readchar

from .base import Element
from ..control.control import Cursor
from ..control.style import Style, Fore

CANCEL = sentinel("CANCEL")

class Choose(Element):
    '''
    选择元素
    '''

    def __init__(self, input: Queue, output: Queue, prompt: str, choices: list[str], allow_cancel: bool = False):
        super().__init__(input, output)
        self.prompt = prompt
        self.choices = choices
        self.allow_cancel = allow_cancel

        if self.allow_cancel:
            self.choices.append(f"取消（^C）")

    def get_choice(self) -> tuple[bool, str]:
        '''
        获取用户选择
        '''
        result = self.input.get()

        if result == CANCEL or (self.allow_cancel and result == self.choices[len(self.choices) - 1]):
            return False, ""
        else:
            return True, result

    def render(self):
        current_choice = 0

        print(self.prompt)


        for i, choice in enumerate(self.choices):
            if i == current_choice:
                print(f"{Style.invert}> {choice}{Style.reset}")
            else:
                print(f"- {choice}")

        Cursor.up(len(self.choices))
        Cursor.hide()

        while True:
            is_exit = False
            try:
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
                    is_exit = True
                    break

                elif key == readchar.key.CTRL_C:
                    raise KeyboardInterrupt

                else:
                    # 回到第一行：
                    Cursor.up(current_choice + 1)
                    

                    # 输出错误信息
                    Cursor.overwrite(f"{Fore.blue}（按↑↓键切换，Enter键选择）{Style.reset}{self.prompt}")

                    # 回到当前选项
                    print("\r", end="")
                    Cursor.down(current_choice + 1)


            except KeyboardInterrupt:
                if self.allow_cancel:
                    self.input.put(CANCEL) #type: ignore
                    is_exit = True
                    break
                else:
                    # 回到第一行：
                    Cursor.up(current_choice + 1)
                    

                    # 输出错误信息
                    Cursor.overwrite(f"{Fore.red}（不允许取消）{Style.reset}{self.prompt}")

                    # 回到当前选项
                    print("\r", end="")
                    Cursor.down(current_choice + 1)
                    continue

            finally:
                if is_exit:
                    print("\n" * (len(self.choices) - current_choice ), end="")
                    Cursor.show()

                

            

        
