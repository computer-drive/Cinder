from .render import start_console_render
from .console import Console

def startup():
    '''启动Cinder渲染线程'''

    input_queue, output_queue, stop_event = start_console_render()

    return Console(input_queue, output_queue, stop_event)
    