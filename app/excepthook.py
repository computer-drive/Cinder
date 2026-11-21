import types

from .logging import get_logger

def excepthook(type: type, value: Exception, tb: types.TracebackType):

    logger = get_logger("Exception")

    logger.error(f"未捕获的异常：{type.__name__} {value}")

    logger.exception(value, exc_info=(type, value, tb))
