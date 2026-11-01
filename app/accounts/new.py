import secrets
from threading import Event, Thread
import webbrowser
import sys
from typing import Literal
lazy from wsgiref.simple_server import make_server, WSGIRequestHandler

lazy from flask import Flask, current_app, request

from core.terminal.console import Console
from core.terminal.control import Fore, Style

from .schema import *
from .command import accounts

class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默，不输出访问日志

ERROR_SIGNAL = sentinel("ERROR_SIGNAL")
SIGINT_SIGNAL = sentinel("SIGINT_SIGNAL")

def auto_login(console: Console) -> str | ERROR_SIGNAL | SIGINT_SIGNAL:
    spinner = console.spinner("")
    spinner.loading1("正在准备...")

    # 准备回调用到的flask应用
    app = Flask(__name__)

    # 准备回调用到的事件
    app.is_auth_success = Event() #type: ignore
    app.auth_code = None          #type: ignore


    @app.route("/auth", methods=["GET"])
    def auth_callback():        
        auth_code = request.args.get("code")

        if auth_code is None:
            return REDIRECT_PAGE_ERROR, 400
        else:
            app.auth_code = auth_code #type: ignore
            app.is_auth_success.set() #type: ignore
            return REDIRECT_PAGE, 200

    server = make_server("0.0.0.0", 0, app, handler_class=QuietHandler)

    

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # 生成url
    state = secrets.token_urlsafe(16)
    port = server.server_port
    login_url = f'''{MS_BASE_URL}consumers/oauth2/v2.0/authorize
    ?client_id={MS_CLIENT_ID}
    &response_type=code
    &redirect_uri=http://localhost:{port}/auth
    &scope=XboxLive.signin%20XboxLive.offline_access
    &state={state}'''
    

    webbrowser.open(login_url)

    console.println("Cinder 打开了一个浏览器网页，请在浏览器上登录 Microsoft 账户。")
    console.println(f"没有看到窗口？手动访问 {Style.link("登录 Microsoft 账户", login_url)}")
    
    spinner.loading0("正在等待登录...")

    status : str| ERROR_SIGNAL | SIGINT_SIGNAL
    while True:
        # 等待用户登录
        try:
            app.is_auth_success.wait()    
        except KeyboardInterrupt:
            spinner.error("用户取消了登录。")
            status = SIGINT_SIGNAL
            break

        status = app.auth_code #type: ignore
        spinner.finish("登录成功。")
        break

    server.shutdown()
    return status
        
    

def manual_login(console) -> str | ERROR_SIGNAL | SIGINT_SIGNAL:
    pass


@accounts.command("new", "添加一个 Minecraft 账户")
def add_account():
    console = Console.get_instance()

    console.title("添加 Minecraft 账户")


    console.println("接下来 Cinder 将会引导你添加一个 Minecraft 账户，请按照提示操作。\n")

    login_type: Literal["auto", "manual"]

    if sys.platform == "darwin":
        # macOS 上对于普通的脚本不能注册 URL Scheme
        # 所以只能使用手动模式
        login_type = "manual"

        console.println("你将使用手动模式登录到 Microsoft 账户。")
    else:
        _choices = ["1. 自动模式：开启一个浏览器，在浏览器上登录 Microsoft 账户即可完成。",
            "2. 手动模式：Cinder 将提供一个设备码，在登录 Microsoft 账户时输入该设备码即可完成。"
        ]

        login_type = "auto" if console.choose(
            "你可以选择以下两种方式登录到 Microsoft 账户：",
            choices=_choices
        ) == _choices[0] else "manual"

    console.println("")

    code = manual_login(console) if login_type == "manual" else auto_login(console)

    # print(code)``