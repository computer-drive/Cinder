import time

from libs.ui.startup import start_worker
from libs.ui.manager import Manager
from libs.ui.elements.progress import Spinner, WAVE_CHARS, ProgressBar


def main(manager: Manager):
    import random
    manager.println("测试文本：hello world")

    p = manager.add(ProgressBar(*manager.get_queue(), message="测试进度", current=-1, total=100, progress_length=50))
    i = 0
    while True:
    
        i += random.randint(1, 1)

        p.update(i, f"{i}")

        time.sleep(0.1)

        if i >= p.total:
            break

    # p.finish(f"下载完成（{i}）")

    manager.stop()

if __name__ == "__main__":
    start_worker(main)
