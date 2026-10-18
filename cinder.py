import time

from libs.ui.startup import start_worker
from libs.ui.manager import Manager
from libs.ui.elements.progress import Spinner, WAVE_CHARS, ProgressBar
from libs.ui.elements.choice import Choose


def main(manager: Manager):
    import random
    manager.println("测试文本：hello world")

    # p = manager.add(ProgressBar(*manager.get_queue(), message="测试进度", current=-1, total=100, progress_length=50))
    # i = 0
    # while True:
    
    #     i += random.randint(1, 10)

    #     p.update(i, f"{i}")

    #     time.sleep(0.1)

    #     # if i >= p.total:
    #     #     break

    # p.stop()

    choice = manager.add(Choose(*manager.get_queue(), "请选择：", ["选项1", "选项2", "选项3"], True))
    manager.println(str(choice.get_choice()))

    manager.stop()

if __name__ == "__main__":
    start_worker(main)
