import portalocker
import time

from core.terminal.startup import startup
from core.terminal.control.style import Style, Fore
from core.arguments import Parser

from app.paths import Paths
from app.commands import parsers

# 启动渲染
console = startup()

# 初始化解析
parser = Parser(help="Cinder命令行")
parser.register(*parsers)

# 初始化Paths
paths = Paths.get_paths()

def main():
    retry = 0
    while True:
        try:
            lock = portalocker.Lock(paths.lock, mode='a', timeout=0)

            lock.acquire()
        except portalocker.AlreadyLocked:
            console.println(f"{Fore.red}有其他 Cinder 实例正在运行。已重试 {retry} 次。{Style.reset}")

            retry += 1

            time.sleep(2)

            continue

        except Exception as e:
            console.error(f"{Fore.red} 无法获取锁：{e}{Style.reset}")
            return 

        except KeyboardInterrupt:
            console.error(f"{Fore.red} 用户中断了运行。{Style.reset}")
            return 

        break

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

        

        

