from datetime import timedelta
import re

def format_size(size: int | float) -> str:
    '''格式化文件大小。'''
    if size < 1024:
        return f"{size} B"
    elif size < 1024**2:
        return f"{size/1024:.2f} KiB"
    elif size < 1024**3:
        return f"{size/1024**2:.2f} MiB"
    else:
        return f"{size/1024**3:.2f} GiB"

def td_to_hms(td: timedelta, *, wrap24: bool = False, round_us: bool = True) -> str:
    """
    将 timedelta 格式化为 'HH:MM:SS'。

    wrap24=True  : 超过 24 小时只显示当天部分（如 1 天 5 小时 -> 05:00:00）
    wrap24=False : 小时数累加（如 1 天 5 小时 -> 29:00:00），推荐
    round_us     : 微秒四舍五入到秒（避免 00:00:00 丢掉接近 1 秒的差值）
    """
    total = td.total_seconds()
    sign = "-" if total < 0 else ""
    total = abs(total)

    secs = round(total) if round_us else int(total)   # 四舍五入到整秒

    hours, rem = divmod(secs, 3600)
    minutes, seconds = divmod(rem, 60)

    if wrap24:
        hours %= 24

    return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"



def substitute(text: str, ctx: dict[str, str]):
    '''格式化${}格式的字符串'''

    return re.sub(r"\$\{(\w+)\}", lambda m: ctx.get(m.group(1), m.group(0)), text)