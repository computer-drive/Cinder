import portalocker
import time
import sys

from app.excepthook import excepthook
from app.logging import get_queue, get_logger
from core.terminal.startup import startup
from core.terminal.control.style import Style, Fore
from core.arguments import Parser
from core.utils.memory import tune_malloc

from app.paths import Paths
from app.config.base import use_config

lazy from app.commands import parsers

# 设置异常钩子
sys.excepthook = excepthook

# 调整 malloc 行为
tune_malloc()

# 启动渲染
console = startup()

# 初始化配置
use_config()

## 初始化解析
parser = Parser(help="Cinder命令行")
parser.register(*parsers)

# 初始化Paths
paths = Paths.get_paths()

def main():
    logger = get_logger()

    retry = 0
    while True:
        try:
            lock = portalocker.Lock(paths.lock, mode='a', timeout=0)

            lock.acquire()
        except portalocker.AlreadyLocked:
            logger.error("没有获取到锁，等待重试...")
            console.println(f"{Fore.red}有其他 Cinder 实例正在运行。已重试 {retry} 次。{Style.reset}")

            retry += 1

            time.sleep(2)

            continue

        except Exception as e:
            console.error(f"无法获取锁：{e}")
            return 

        except KeyboardInterrupt:
            console.error(f"用户中断了运行。")
            return 

        break

    logger.info(f"命令行：{' '.join(sys.argv)}")



    if retry:
        console.println(f"{Fore.blue}得到了锁，继续运行。{Style.reset}")

    try:
        parser.run()
    finally:
        lock.release()



if __name__ == "__main__":

    try:
       main()

    finally:
        console.stop()
        
        get_queue().put(None)

        

        

