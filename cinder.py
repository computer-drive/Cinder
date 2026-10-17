import time

from libs.ui.startup import start_worker
from libs.ui.manager import Manager


def main(manager: Manager):
    manager.println("测试文本：hello world")


    i = 0
    while i < 10:
        manager.overwrite(f"测试文本：{i}")
        i += 1
        time.sleep(1)

    manager.stop()

if __name__ == "__main__":
    start_worker(main)
