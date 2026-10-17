import threading
import queue
from typing import Callable

from .renderer import Renderer
from .manager import Manager

def start_worker(worker: Callable):
    '''启动渲染'''
    output = queue.Queue()
    input_ = queue.Queue()

    renderer = Renderer(input_, output)
    

    manager = Manager(input_, output)

    thread = threading.Thread(target=worker, args=(manager,))
    thread.start()

    renderer.run()

    thread.join()


