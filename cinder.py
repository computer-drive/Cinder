from multiprocessing.connection import Listener, Client
import sys
import webbrowser
import subprocess
import os
from queue import Queue, Empty
from threading import Thread

import portalocker
lazy from waitress.server import create_server

from core.utils.memory import tune_malloc
from app.excepthook import excepthook
from app.logging import get_logger
from app.paths import Paths
from app.config.base import use_config
lazy from app.server.server import app

#region init
# 设置异常钩子
sys.excepthook = excepthook

# 调整 malloc 行为
tune_malloc()

# 初始化配置
try:
    use_config()
except Exception as e:
    sys.exit(1)

# 初始化Paths
paths = Paths.get_paths()
#endregion


def run_server(as_service:bool = False):
    queue = Queue[str]()
    logger = get_logger("Server", queue)
    
    try:
        lock = portalocker.Lock(paths.lock, mode="a", timeout=0)

        lock.acquire()

    except portalocker.AlreadyLocked:
        if as_service:
            print("-XError", flush=True) 
        logger.error("有其他进程获取到了锁，无法启动服务器。")
        return

    except Exception as e:
        if as_service:
            print("-XError", flush=True)

        logger.error("未能获取到锁。")
        logger.exception(e)
        return

    try:
        

        port = use_config().system.server_port

        logger.info(f"将在 {port} 端口运行服务器。")

        if as_service:
            print("-XStarted", flush=True)
        else:
            if use_config().system.auto_start_web_browser:
                webbrowser.open(f"http://localhost:{port}")

        
        server = create_server(app, host="0.0.0.0", port=port)
        
        monitor_thread = Thread(target=service_monitor, args=(queue, server), daemon=True)
        monitor_thread.start()
        
        server.run()

    except KeyboardInterrupt:
        pass

    finally:
        lock.release()

    

def service_monitor(queue: Queue[str], server):
    address: str
    family: str

    if sys.platform == "win32":
        address = r"\\.\pipe\Pipe"
        family = "AF_PIPE"

    else:
        address = str(paths.data / "sock.sock")
        family = "AF_UNIX"

    with Listener(address, family) as listener:
        with listener.accept() as conn:
            while True:
                try:
                    msg = queue.get_nowait()
                    conn.send(msg)
                except Empty:
                    pass

                if conn.poll(0.1):
                    msg = conn.recv()
                    logger = get_logger("Server")
                    logger.info(f"收到消息: {msg}")
                    if msg == "stop":
                        # 发SIGINT
                        server.close()

                        break
                    
                
def attach_server():
    address: str
    family: str

    if sys.platform == "win32":
        address = r"\\.\pipe\Pipe"
        family = "AF_PIPE"

    else:
        address = str(paths.data / "sock.sock")
        family = "AF_UNIX"
    
    
    with Client(address, family) as conn:
        while True:
            try:
                data: str = conn.recv()

                print(data)
            except KeyboardInterrupt:
                conn.send("stop")
                break
                
            except Exception as e:
                print(e)
                break

        
def run_as_service():

    kwargs = {}
    # ! 让子进程脱离父进程的控制台/进程组，父进程退出后它仍存活
    if sys.platform == "win32":
        
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        
        kwargs["start_new_session"] = True
    
    process = subprocess.Popen(
        [sys.executable, os.path.abspath(sys.argv[0]), "run", "--as-service"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        text=True,
        **kwargs
    )


    for text in process.stdout:
        
        sys.stdout.write(text)

        if ("-XStarted" in text):
            print("启动成功", flush=True)
            break
        
        if  ("-XError" in text):
            print("启动失败", flush=True)
            break

        
    
            
if __name__ == "__main__":
    try:
        arg = sys.argv[1]
    except IndexError:
        arg = "run"

    match arg:
        case "run":
            run_server(sys.argv[2] == '--as-service' if len(sys.argv) > 2 else False)
        case "run-as-service":
            run_as_service()
        case "attach":
            attach_server()
        
        case _:
            print(f"未知的参数 {arg}")

        

        

