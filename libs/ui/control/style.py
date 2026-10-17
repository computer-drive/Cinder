from .base import _ESC

class Fore:
    black = _ESC + '30m'
    red = _ESC + '31m'
    green = _ESC + '32m'
    yellow = _ESC + '33m'
    blue = _ESC + '34m'
    magenta = _ESC + '35m' # 紫色
    cyan = _ESC + '36m' # 青色
    white = _ESC + '37m' # 白色

    # 亮色系
    light_black = _ESC + '90m'
    light_red = _ESC + '91m'
    light_green = _ESC + '92m'
    light_yellow = _ESC + '93m'
    light_blue = _ESC + '94m'
    light_magenta = _ESC + '95m' # 紫色
    light_cyan = _ESC + '96m' # 青色
    light_white = _ESC + '97m' # 白色

    default = _ESC + '39m' # 终端默认色

    @classmethod
    def custom(cls, r: int, g: int, b: int):
        return f'{_ESC}38;2;{r};{g};{b}'

class Back:
    black = _ESC + '40m' # 黑色背景
    red = _ESC + '41m' # 红色背景
    green = _ESC + '42m' # 绿色背景
    yellow = _ESC + '43m' # 黄色背景
    blue = _ESC + '44m' # 蓝色背景
    magenta = _ESC + '45m' # 紫色背景
    cyan = _ESC + '46m' # 青色背景
    white = _ESC + '47m' # 白色背景
    default = _ESC + '49m' # 终端默认背景

    # 亮色系
    light_black = _ESC + '100m'
    light_red = _ESC + '101m'
    light_green = _ESC + '102m'
    light_yellow = _ESC + '103m'
    light_blue = _ESC + '104m'
    light_magenta = _ESC + '105m' # 紫色
    light_cyan = _ESC + '106m' # 青色
    light_white = _ESC + '107m' # 白色

    default = _ESC + '109m' # 终端默认背景

    @classmethod
    def custom(cls, r: int, g: int, b: int):
        return f'{_ESC}48;2;{r};{g};{b}'


class Style:
    reset = _ESC + '0m' # 重置样式
    bold = _ESC + '1m' # 加粗
    italic = _ESC + '3m' # 斜体

    invert = _ESC + '7m' # 反显
    hidden = _ESC + '8m' # 隐藏
    strike = _ESC + '9m' # 删除线

    @classmethod
    def underline(cls, count: int = 1):
        '''添加下划线，count参数可传入1, 2'''
        return f'{_ESC}{4 if count == 1 else 21}m' # 下划线







