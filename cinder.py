import portalocker
import time

from core.terminal.startup import startup
from core.terminal.control.style import Style, Fore
from core.arguments import Parser


lazy from app.commands import parsers

# 启动渲染
console = startup()

parser = Parser(help="Cinder命令行")

parser.register(*parsers)

if __name__ == "__main__":
    retry = 0
    while True:
        try:
            lock = portalocker.Lock("cinder.lock", mode='a', timeout=0)

            lock.acquire()
        except portalocker.AlreadyLocked:
            console.println(f"{Fore.red}有其他 Cinder 实例正在运行。已重试 {retry} 次。{Style.reset}")

            retry += 1

            time.sleep(2)

            continue

        except Exception as e:
            console.error(f"{Fore.red} 无法获取锁：{e}{Style.reset}")
            exit(1)

        except KeyboardInterrupt:
            console.error(f"{Fore.red} 用户中断了运行。{Style.reset}")
            exit(0)

        break

    if retry:
        console.println(f"{Fore.blue}得到了锁，继续运行。{Style.reset}")


    try:
        parser.run()

    finally:
        console.stop()

        lock.release()

