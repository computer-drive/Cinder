import time

from libs.ui.startup import start_worker
from libs.ui.manager import Manager
from libs.ui.elements.progress import Progress, WAVE_CHARS


def main(manager: Manager):
    import random
    manager.println("测试文本：hello world")


    while True:
        i = 0
        total = random.randint(50, 500)
        p = manager.add(Progress(*manager.get_queue(), f"正在下载（0 / {total} MB）", ))
        while True:
        
            i += random.randint(1, 10)

            p.update(f"正在下载（{i} / {total} MB）")

            time.sleep(0.1)

            if i >= total:
                break

        p.finish(f"下载完成（{total} MB）")

    manager.stop()

if __name__ == "__main__":
    start_worker(main)
