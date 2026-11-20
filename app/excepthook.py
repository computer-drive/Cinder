import traceback

from core.terminal.control import Style, Fore
from .logging import get_logger, get_queue

def excepthook(type, value, tb):

    print(f"{Fore.red}未捕获的异常：{type.__name__} {value}") 

    print("".join(traceback.format_exception(type, value, tb)) + Style.reset)

    logger = get_logger()
    logger.error(f"未捕获的异常：{type.__name__} {value}")

    logger.error(traceback.format_exception(type, value, tb))

    get_queue().put(None)