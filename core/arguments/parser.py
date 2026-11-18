from typing import Callable, Annotated, cast
import shutil
import sys
import textwrap
from collections import Counter
from pathlib import Path

from ..terminal.console import Console
from ..terminal.control import Fore, Style
from ..utils.levenshtein import levenshtein
from .argument import Argument


_INDENT = "    "
_MIN_WIDTH = 60
_MAX_WIDTH = 100
_GAP = 4

# * AI 重构了不少

def _terminal_width() -> int:
    try:
        columns = shutil.get_terminal_size((80, 24)).columns
    except OSError:
        columns = 80

    return max(_MIN_WIDTH, min(columns, _MAX_WIDTH))


def _short_description(doc: str | None) -> str:
    """取描述的第一行，用作列表里的短描述。"""
    if not doc:
        return ""

    return doc.strip().splitlines()[0].strip()


def _long_description(doc: str | None) -> str:
    """取描述除第一行外的正文，用作 --help 里的长描述。"""
    if not doc:
        return ""

    lines = doc.strip().splitlines()
    if len(lines) <= 1:
        return ""

    return "\n".join(lines[1:]).strip("\n")


def _wrap(text: str, width: int) -> list[str]:
    if not text:
        return [""]

    return textwrap.wrap(text, width=max(10, width)) or [""]


def _render_entries(entries: list[tuple[str, str]]) -> list[str]:
    """对齐渲染「左列 + 右列」列表，右列超宽时折行并悬挂缩进。"""
    if not entries:
        return []

    name_width = max(len(name) for name, _ in entries)
    lines: list[str] = []

    for name, description in entries:
        head = f"{_INDENT}{name.ljust(name_width)}{' ' * _GAP}"
        wrapped = _wrap(description, _terminal_width() - len(head))

        lines.append(head + wrapped[0])
        lines.extend(" " * len(head) + part for part in wrapped[1:])

    return lines



class Parser:
    '''命令行参数解析器'''

    def __init__(self, name: str | None = None, help: str | None = None):
        self.name = name
        self.help = help

        # 名称：(帮助，函数)
        self.commands: dict[str, tuple[str | None, Callable]] = {}

        self.sub_commands: dict[str, Parser] = {}

        self.parent: Parser | None = None

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

            p.parent = self
            self.sub_commands[p.name] = p

    # ------------------------------------------------------------------
    # 帮助
    # ------------------------------------------------------------------

    @property
    def _prefix(self) -> str:
        """把父级名称串起来，得到 `cinder instances install` 这样的前缀。"""
        names: list[str] = []
        node: Parser | None = self

        while node is not None:
            if node.name:
                names.append(node.name)
            node = node.parent

        names.reverse()

        program = Path(sys.argv[0]).stem or "cinder"

        return " ".join([program, *names])

    @staticmethod
    def _parameters(func: Callable) -> list[tuple[str, type, Argument]]:
        """按函数签名顺序取出 (参数名, 类型, 元数据)。"""
        annotations = dict(getattr(func, "__annotations__", {}))
        annotations.pop("return", None)

        parameters: list[tuple[str, type, Argument]] = []
        for name, annotation in annotations.items():
            origin = getattr(annotation, "__origin__", annotation)
            metadata = getattr(annotation, "__metadata__", ())
            spec = metadata[0] if metadata else Argument()

            parameters.append((name, origin, spec))

        return parameters

    @staticmethod
    def _parameter_entries(params: list[tuple[str, type, Argument]]) -> list[tuple[str, str]]:
        entries: list[tuple[str, str]] = []

        for name, annotation, spec in params:
            optional, default = spec.optional

            if spec.is_positional():
                left = f"[{name}]" if optional else f"<{name}>"
            elif annotation is bool:
                left = f"{', '.join(spec.names)} <bool>"
            else:
                left = f"{', '.join(spec.names)} <{name}>"

            description = spec.help or ""
            if optional and default is not None:
                description = f"{description}（默认：{default}）" if description else f"默认：{default}"

            entries.append((left, description))

        return entries

    @staticmethod
    def _usage_tokens(func: Callable) -> list[str]:
        tokens: list[str] = []

        for name, annotation, spec in Parser._parameters(func):
            optional = spec.optional[0]

            if spec.is_positional():
                token = f"[{name}]" if optional else f"<{name}>"
            else:
                flag = spec.names[0] if spec.names else name
                token = f"{flag}=<bool>" if annotation is bool else f"{flag} <{name}>"

            tokens.append(f"[{token}]" if optional else token)

        return tokens

    def _print_overview(self):
        lines: list[str] = []

        short = _short_description(self.help)
        body = _long_description(self.help)

        if short:
            lines.append(f"{Style.bold}{short}{Style.reset}")

        if body:
            lines.append("")
            lines.extend(_INDENT + line if line.strip() else "" for line in body.splitlines())

        lines.append("")
        lines.append(f"{Style.bold}用法{Style.reset}：")
        lines.append(f"{_INDENT}{self._prefix} [--help] <命令> [参数...]")

        entries: list[tuple[str, str]] = []
        entries.extend(
            (name, _short_description(help_text))
            for name, (help_text, _) in self.commands.items()
        )
        entries.extend(
            (name, _short_description(parser.help))
            for name, parser in self.sub_commands.items()
        )

        if entries:
            lines.append("")
            lines.append(f"{Style.bold}命令{Style.reset}：")
            lines.extend(_render_entries(sorted(entries)))



        self.console.println("\n".join(lines))

    def _print_command_help(self, name: str):
        help_text, func = self.commands[name]
        doc = getattr(func, "__doc__", None) or help_text

        short = _short_description(doc)
        body = _long_description(doc)
        params = self._parameters(func)

        lines: list[str] = []

        if short:
            lines.append(f"{Style.bold}{short}{Style.reset}")

        if body:
            lines.append("")
            lines.extend(_INDENT + line if line.strip() else "" for line in body.splitlines())

        lines.append("")
        lines.append(f"{Style.bold}用法{Style.reset}：")
        tokens = self._usage_tokens(func)
        lines.append(f"{_INDENT}{' '.join([self._prefix, name, *tokens])}")

        if params:
            lines.append("")
            lines.append(f"{Style.bold}参数{Style.reset}：")
            lines.extend(_render_entries(self._parameter_entries(params)))

        self.console.println("\n".join(lines))

    def show_help(self, path: list[str] | None = None):
        """显示帮助。path 为空显示本层，否则逐级下钻到命令。"""
        topics = list(path or [])
        node: Parser = self

        for index, topic in enumerate(topics):
            if topic in node.sub_commands:
                node = node.sub_commands[topic]
                continue

            if topic in node.commands:
                if index != len(topics) - 1:
                    node.console.error(f"命令“{topic}”没有子主题。")
                    return

                node._print_command_help(topic)
                return

            node.console.error(f"没有与“{topic}”匹配的帮助主题。")
            return

        node._print_overview()

    # ------------------------------------------------------------------
    # 运行
    # ------------------------------------------------------------------

    def run_command(self, command_name: str, args_origin: list[str]):
        '''运行命令'''
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
                        args_finally[arg_name] = arg_spec.optional[1]
                        continue

                    else:
                        if arg_spec.is_positional():
                            self.console.error(f"没有提供第 {i + 1} 个位置参数。")
                        else:
                            self.console.error(f"没有提供参数 {','.join(arg_spec_name)}。")
                        return

            try:
                args_finally[arg_name] = arg_type(arg)
            except ValueError:
                self.console.error(f"参数“{arg_name}”需要是 {arg_type.__name__} 类型，无法转换值“{arg}”。") # pyright: ignore[reportPossiblyUnboundVariable]
                return

        # 判断used
        all = ([arg if isinstance(arg, str) else arg[1] for arg in args])
        used = list(used)

        if len(used) != len(all):
            self.console.warning(f"参数 {', '.join(Counter(all) - Counter(used))} 未被定义（或使用）。")

        # 解析完，运行函数
        self.commands[command_name][1](**args_finally)

    def run(self, args: list[str] | None = None):
        '''运行解析器'''

        if len(self.commands) + len(self.sub_commands) == 0:
            raise ValueError("你还没有注册任何命令！")

        console = self.console

        argv = list(sys.argv if args is None else args)[1:]

        if not argv:
            self.show_help()
            return

        head, rest = argv[0], argv[1:]

        # 帮助入口：help / -h / --help，可以跟一串主题逐级下钻
        if head in ("help", "-h", "--help"):
            self.show_help(rest)
            return

        if head in self.commands:
            if any(arg in ("-h", "--help") for arg in rest):
                self._print_command_help(head)
                return

            self.run_command(head, argv)
            return

        if head in self.sub_commands:
            sub = self.sub_commands[head]

            if rest and rest[0] in ("help", "-h", "--help"):
                sub.show_help(rest[1:])
                return

            sub.run(argv)
            return

        all_commands_name = [*self.commands, *self.sub_commands]

        # 计算与所有命令的编辑距离，然后找到最相近的
        edit_distances = {i: levenshtein(head, i) for i in all_commands_name}

        min_name = min(edit_distances, key=lambda key: edit_distances[key])
        min_distance = edit_distances[min_name]

        if min_distance < len(min_name):
            console.error(f"找不到命令“{head}”，你指的是不是“{min_name}”？")
        else:
            console.error(f"找不到命令“{head}”。")
