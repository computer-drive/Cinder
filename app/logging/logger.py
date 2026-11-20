import logging
from logging.handlers import RotatingFileHandler
from queue import Queue
import threading

lazy import requests

from ..config import use_config
from ..paths import paths

class SocketHandler(logging.Handler):
    def __init__(self, queue: Queue[str | None]):
        super().__init__()

        self.queue = queue

        self.start_server()


    def start_server(self):
        server_thread = threading.Thread(target=self.server, args=(self.queue,), daemon=False)
        server_thread.start()

    def server(self, queue: Queue[str | None]):
            is_stop = False
            while True:

                logs = []
                while True:
                    log = queue.get()

                    if log is None:
                        is_stop = True
                        break
                    
                    logs.append(log)

                    if queue.empty():
                        break

                try:
                    requests.post("http://localhost:9000/logs",
                        timeout=2,
                        json={"logs": logs}
                        )
                except:
                    pass

                if is_stop:
                    break



    def emit(self, record: logging.LogRecord):
        self.queue.put(self.format(record))


    def close(self):
        self.queue.put(None)


_queue: Queue[str | None] = Queue[str | None]()
_logger : logging.Logger | None = None


def get_logger():
    global _logger, _queue

    if _logger is None:
 

        logger = logging.getLogger("cinder")

        logger.setLevel(logging.INFO)

        

        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

        if use_config().system.debug:
            socket_handler = SocketHandler(_queue)
            socket_handler.setFormatter(formatter)
            logger.addHandler(socket_handler)

        
        file_handler = RotatingFileHandler(
            filename=paths.logs / "logs.log",
            maxBytes=1024 * 1024 * 10, # 最大10MB
            backupCount=5, # 最多保留5个备份文件
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        _logger = logger

    return _logger


def get_queue():
    return _queue
