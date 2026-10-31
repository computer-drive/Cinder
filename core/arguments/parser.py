from typing import Callable, Annotated, cast
import sys
from collections import Counter

from ..terminal.console import Console
from ..terminal.control import Fore, Style
from ..utils.levenshtein import levenshtein
from .argument import Argument


class Parser:
    '''命令行参数解析器'''

    def __init__(self, name: str | None = None, help: str | None = None):
        self.name = name
        self.help = help

        # 名称：(帮助，函数)
        self.commands: dict[str, tuple[str | None, Callable]] = {}

        self.sub_commands: dict[str, Parser] = {}

        self.console = Console.get_instance()

    def command(self, name: str, help: str | None = None):
        '''定义命令'''
        def wrapper(func):
            self.commands[name] = (help, func)
            return func

        return wrapper

    def register(self, *parser: Parser):
        '''注册子命令'''
        for p in parser:
            if p.name is None:
                raise ValueError('子命令解析器必须有名称')
            
            self.sub_commands[p.name] =  p

    def show_help(self, command: str | None = None, prefix: str = ""):
        if command is None:
            # 根据sys.argv获取运行的程序的名称
            program_name = sys.argv[0].split("/")[-1]

            self.console.println(
                f"""{self.help}
                
{Style.bold}用法{Style.reset}：{program_name} {prefix} <命令>

{Style.bold}命令{Style.reset}：

"""

            )
        elif command in self.sub_commands:
            self.sub_commands[command].show_help()

    def run_command(self, command_name: str, args_origin: list[str]):
        '''运行命令'''
        # print(args_origin)

        # 通过类型注解获取这个命令的所有参数
        args_spec: dict[str, Annotated[type, Argument]] = dict(self.commands[command_name][1].__annotations__) # 拷贝一下对象
        args_spec.pop("return", None)# 由于是Callable，去除可能出现的return键

        args: list[str | tuple[str, str]] = []

        used = set()


        # 初步解析参数
        has_name_args = False
        for arg in args_origin[1:]:
            if "=" in arg:
                a_ = arg.split("=", 1)
                args.append((a_[0], a_[1]))

                has_name_args = True
            else:
                if has_name_args:
                    self.console.error(f"位置参数不能出现在名称参数的后面，请检查参数“{arg}”。")
                    return
                
                args.append(arg)

        # print(args)

        # 先初始化最初的finally_args
        args_finally = {}

        # 解析参数
        for i in range(len(args_spec)):
            lst_args_spec = list(args_spec.keys())

            arg_name = lst_args_spec[i]
            all = args_spec[arg_name]

            arg_type: type = all.__origin__
            arg_spec: Argument = all.__metadata__[0]
            arg_spec_name: tuple[str, ...] = arg_spec.names


            # 先使用位置参数读取
            try:
                arg = args[i]

                if not isinstance(arg, str):
                    # print(arg, "这个参数不是位置参数")
                    raise ValueError("这个参数不是位置参数")

                used.add(arg)
    
            except IndexError, ValueError:
                # 读取失败，再尝试用具名参数

                is_error = False

                if len(arg_spec_name) == 0:
                    # 没有可用的名字，报错
                    is_error = True

                else:
                    possible_args = [arg for arg in args if isinstance(arg, tuple) and arg[0] in arg_spec_name]

                    if len(possible_args) == 0:
                        is_error = True
                    elif len(possible_args) > 1:
                        self.console.error(f"提供了两个相同名称的参数“{possible_args[0][0]}”。")
                        return
                    else:
                        arg = possible_args[0][1]

                        used.add(arg)
                        
                        
                if is_error:
                    # 判断是否有默认值
                    if arg_spec.optional[0]:
                        # 有默认值
                        args_finally[arg_name] =  arg_spec.optional[1]
                        continue

                    else:
                        if arg_spec.is_positional():
                            self.console.error(f"没有提供第 {i + 1} 个位置参数。")
                        else:
                            self.console.error(f"没有提供参数 {",".join(arg_spec_name)}。")
                        return

            try:
                args_finally[arg_name] = arg_type(arg) # pyright: ignore[reportPossiblyUnboundVariable] #
            except ValueError:
                self.console.error(f"参数“{arg_name}”需要是 {arg_type.__name__} 类型，无法转换值“{arg}”。") # pyright: ignore[reportPossiblyUnboundVariable]
                return





        # 判断used
        all = ([arg if isinstance(arg, str) else arg[1] for arg in args])
        used = list(used)
        # print(all, used)
        if len(used) != len(all):
            self.console.warning(f"参数 {", ".join(Counter(all) - Counter(used))} 未被定义（或使用）。")

        # 解析完，运行函数
        self.commands[command_name][1](**args_finally)



    def run(self, args: list[str] = sys.argv):
        '''运行解析器'''

        if len(self.commands) + len(self.sub_commands) == 0:
            raise ValueError("你还没有注册任何命令！")

        console = self.console

        if len(args) == 1:
            console.error("没有提供参数。")
            return

        args = args[1:] # 去除第一个元素

        if args[0] in self.commands:
            self.run_command(args[0], args[0:])

        elif args[0] in self.sub_commands:

            self.sub_commands[args[0]].run(args[0:])
        else:
            all_commands_name = [*self.commands, *self.sub_commands]

            # 计算args[1]与所有all_commands_name的编辑距离，然后找到最相近的
            edit_distances = {i: levenshtein(args[0], i) for i in all_commands_name}

            
            min_name = min(edit_distances, key=lambda key: edit_distances[key])
            min_distance = edit_distances[min_name]

            if min_distance < len(min_name):
                console.error(f"找不到命令“{args[0]}”，你指的是不是“{min_name}”？")
            else:
                console.error(f"找不到命令“{args[0]}”。")


        

        

 

        