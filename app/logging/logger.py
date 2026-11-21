import logging
from logging.handlers import RotatingFileHandler
from queue import Queue


from ..paths import paths

class QueueHandler(logging.Handler):
    def __init__(self, queue: Queue[str]):
        super().__init__()
        self.queue = queue


    def emit(self, record):
        self.queue.put(self.format(record))


def get_logger(name: str, queue: Queue[str] | None = None):


    logger = logging.getLogger(name)

    logger.setLevel(logging.INFO)

    
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = RotatingFileHandler(
        filename=paths.logs / "logs.log",
        maxBytes=1024 * 1024 * 10, # 最大10MB
        backupCount=5, # 最多保留5个备份文件
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if queue is not None:
        queue_handler = QueueHandler(queue)
        queue_handler.setFormatter(formatter)
        logger.addHandler(queue_handler)

    _logger = logger

    return _logger


