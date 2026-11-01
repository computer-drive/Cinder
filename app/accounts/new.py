import secrets
from threading import Event, Thread
from typing import Literal
import webbrowser
lazy from wsgiref.simple_server import make_server, WSGIRequestHandler

lazy from flask import Flask, current_app, request
lazy import requests

from core.terminal.console import Console
from core.terminal.control import Fore, Style

from .schema import *
from .command import accounts

class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默，不输出访问日志

ERROR_SIGNAL = sentinel("ERROR_SIGNAL")
SIGINT_SIGNAL = sentinel("SIGINT_SIGNAL")

def auto_login(console: Console) -> tuple[str, str] | ERROR_SIGNAL | SIGINT_SIGNAL:
    spinner = console.spinner("")
    spinner.loading1("正在准备...")

    # 准备回调用到的flask应用
    app = Flask(__name__)

    # 准备回调用到的事件
    app.is_auth_success = Event() #type: ignore
    app.auth_code = None          #type: ignore


    @app.route("/auth", methods=["GET"])
    def auth_callback():        
        auth_code = request.args.get("code", None)
        state_param = request.args.get("state", None) # 获取state防止CSRF攻击

        if auth_code is None:
            return REDIRECT_PAGE_ERROR, 400
        else:
            if state_param == state: # 验证state
                
                app.auth_code = auth_code #type: ignore
                app.is_auth_success.set() #type: ignore
                return REDIRECT_PAGE, 200
            else:
                return REDIRECT_PAGE_ERROR, 400

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
            app.is_auth_success.wait()    #type: ignore
        except KeyboardInterrupt:
            spinner.error("用户取消了登录。")
            status = SIGINT_SIGNAL
            break

        status = app.auth_code #type: ignore
        spinner.finish("登录成功。")
        break

    server.shutdown()

    

    if isinstance(status, str):

        spinner = console.spinner("正在获取 Microsoft 令牌...")

        result = get_ms_token(console, f"http://localhost:{port}/auth", status)

        if result != ERROR_SIGNAL:
            spinner.finish("获取 Microsoft 令牌成功。")
        else:
            spinner.error("获取 Microsoft 令牌失败。")

        return result
    
    else:
        return status

def get_ms_token(console: Console, redirect_url: str, code: str) -> tuple[str, str] | ERROR_SIGNAL:
    try:
        response = requests.post(f"{MS_BASE_URL}consumers/oauth2/v2.0/token", data={
            "client_id": MS_CLIENT_ID,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_url,
            "scope": "XboxLive.signin XboxLive.offline_access"
        }, headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }, timeout=10)
    except requests.RequestException as e:
        console.error(f"请求 Microsoft 令牌失败（网络错误）：{e}")
        return ERROR_SIGNAL

    if response.status_code != 200:
        console.error(f"请求 Microsoft 令牌失败（状态错误）：{response.status_code}。响应内容：{response.text}")
        return ERROR_SIGNAL
    else:
        access_token = response.json().get("access_token", None)
        refresh_token = response.json().get("refresh_token", None)

        if access_token is None or refresh_token is None:
            console.error("请求 Microsoft 令牌失败（响应格式错误）")
            return ERROR_SIGNAL
        else:
            return access_token, refresh_token
        
    

def manual_login(console) -> str | ERROR_SIGNAL | SIGINT_SIGNAL:
    pass



def get_xbox_live_token(console: Console, access_token: str) -> tuple[str, str] | ERROR_SIGNAL :

    try:
        response = requests.post(XBOX_LIVE_URL, json=get_xobx_live_body(access_token), timeout=10, headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    except requests.RequestException as e:
        console.error(f"请求 Xbox Live 令牌失败（网络错误）：{e}")
        return ERROR_SIGNAL

    if response.status_code != 200:
        console.error(f"请求 Xbox Live 令牌失败（状态错误）：{response.status_code}")
        
        return ERROR_SIGNAL
    else:
        token = response.json().get("Token", None)
        user_hash = response.json().get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs", None)
        if token is None or user_hash is None:
            console.error("请求 Xbox Live 令牌失败（响应格式错误）")
            return ERROR_SIGNAL
        else:
            return token, user_hash


def get_xsts_token(console: Console, xbox_live_token: str) -> str | ERROR_SIGNAL:
    try:
        response = requests.post(XSTS_URL, json={
                    "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [ xbox_live_token ]
            },
            "RelyingParty": "rp://api.minecraftservices.com/",  
            "TokenType": "JWT"
        }, timeout=10, headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    except requests.RequestException as e:
        console.error(f"请求 XSTS 令牌失败（网络错误）：{e}")
        return ERROR_SIGNAL

    if response.status_code != 200:
        if response.status_code == 401:
            error_code = response.json().get("XErr", None)
            match error_code:
                case 2148916227:
                    console.error("你的 Xbox Live 账户被封禁了。")
                case 2148916233:
                    console.error("你的 Microsoft 账户未启用 Xbox Live 服务。")
                    console.println(f"可以先去 {Style.link("Minecraft 官网", "https://www.minecraft.net/")} 登录一次。")
                case 2148916235:
                    console.error("你所在的国家或地区不支持 Xbox Live 服务。")
                case (2148916236, 2148916237):
                    console.error("你的 Xbox Live 账户未通过成人验证（韩国地区）。")
                case None:
                    console.error("请求 XSTS 令牌失败（响应格式错误）")
                case _:
                    console.error(f"请求 XSTS 令牌失败（未知错误）：{error_code}（{response.json().get("Message", "无消息")}）")

    
        return ERROR_SIGNAL
    else:
        token = response.json().get("Token", None)
        if token is None:
            console.error("请求 XSTS 令牌失败（响应格式错误）")
            return ERROR_SIGNAL
        else:
            return token

def get_mc_token(console: Console, user_hash: str, xsts_token: str) -> str | ERROR_SIGNAL:
    try:
        response = requests.post(MC_TOKEN_URL, json={
            "identityToken": f"XBL3.0 x={user_hash};{xsts_token}"
        }, timeout=10, headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    except requests.RequestException as e:
        console.error(f"请求 Minecraft 令牌失败（网络错误）：{e}")
        return ERROR_SIGNAL

    if response.status_code != 200:
        console.error(f"请求 Minecraft 令牌失败（状态错误）：{response.status_code}。响应内容：{response.text}")
        return ERROR_SIGNAL
    else:
        token = response.json().get("access_token", None)
        if token is None:
            console.error("请求 Minecraft 令牌失败（响应格式错误）")
            return ERROR_SIGNAL
        else:
            return token

@accounts.command("new", "添加一个 Minecraft 账户")
def add_account():
    console = Console.get_instance()

    console.title("添加 Minecraft 账户")


    console.println("接下来 Cinder 将会引导你添加一个 Minecraft 账户，请按照提示操作。\n")

    login_type: Literal["auto", "manual"]

    _choices = ["1. 自动模式：开启一个浏览器，在浏览器上登录 Microsoft 账户即可完成。",
        "2. 手动模式：Cinder 将提供一个设备码，在登录 Microsoft 账户时输入该设备码即可完成。"
    ]

    login_type = "auto" if console.choose(
        "你可以选择以下两种方式登录到 Microsoft 账户：",
        choices=_choices
    ) == _choices[0] else "manual"

    console.println("")


    ##########################################
    result = manual_login(console) if login_type == "manual" else auto_login(console)
    
    if result in [ERROR_SIGNAL, SIGINT_SIGNAL]:
        return
    else:
        access_token, refresh_token = result #type: ignore
    
    ##########################################

    spinner = console.spinner("正在获取 Xbox Live 令牌...")
    # 获取Xbox Live令牌
    try:
        result = get_xbox_live_token(console, access_token)
    except KeyboardInterrupt:
        spinner.error("用户取消了登录。")
        return

    if result == ERROR_SIGNAL:
        spinner.error("获取 Xbox Live 令牌失败，稍后再试。")
        return

    xbox_live_token, user_hash = result

    spinner.finish("获取 Xbox Live 令牌成功。")

    ##########################################

    spinner = console.spinner("正在获取 XSTS 令牌...")

    try:
        xsts_token = get_xsts_token(console, xbox_live_token)
    except KeyboardInterrupt:
        spinner.error("用户取消了登录。")
        return

    if xsts_token == ERROR_SIGNAL: 
        spinner.error("获取 XSTS 令牌失败，稍后再试。")
        return
    else:
        spinner.finish("获取 XSTS 令牌成功。")

    ##########################################1

    spinner = console.spinner("正在获取 Minecraft 令牌...")

    try:
        mc_token = get_mc_token(console, user_hash, xsts_token)
    except KeyboardInterrupt:
        spinner.error("用户取消了登录。")
        return

    if mc_token == ERROR_SIGNAL: 
        spinner.error("获取 Minecraft 令牌失败，稍后再试。")
        return
    else:
        spinner.finish("获取 Minecraft 令牌成功。")

    