from queue import Queue
from threading import Event, Thread
from time import perf_counter, sleep
import sys

from .elements import * 


def renderer_worker(input_queue: Queue[str],
                    output_queue: Queue[Element | None],
                    stop_event: Event,
                    fps: int = 24,
                    ):

    # 强制关闭光标的应用模式，修复方向键输入问题
    sys.stdout.write("\x1b[?1l")

    period = 1.0 / fps

    while not stop_event.is_set():
        element = output_queue.get()

        if element is None:
            break

        if isinstance(element, BaseElement):
            # 调用draw函数绘制
            element.draw()

        elif isinstance(element, LiveElement):
            # 以 24 fps的帧率更新，直到STOP_SIGNAL
            next_deadline = perf_counter()

            while not stop_event.is_set():
                if element.update() == STOP_SIGNAL:
                    break

                next_deadline += period
                now = perf_counter()
                delay = next_deadline - now

                if delay > 0:
                    sleep(delay)
                else:
                    next_deadline = now
        elif isinstance(element, PromptElement):
            input_queue.put(element.run())


def start_console_render(fps: int = 24):
    '''
    启动控制台渲染线程
    '''

    input_queue = Queue[str]()
    output_queue = Queue[Element | None]()

    stop_event = Event()

    thread = Thread(target=renderer_worker, args=(input_queue, output_queue, stop_event, fps))
    thread.start()

    return input_queue, output_queue, stop_event


        

                    

                    


    

