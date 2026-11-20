import os
import webbrowser
from datetime import datetime, timedelta
import time
from typing import Generator
from enum import Enum, auto

lazy import requests
from pydantic import BaseModel, ValidationError, computed_field, PrivateAttr

from app.config.base import use_config

lazy from ..database import use_database
lazy from ..database.model import Accounts
from .base import Task, StepUpdate, StepFinished, TaskError


class DeviceCodeResponse(BaseModel):
    user_code: str
    device_code: str
    verification_uri: str
    expires_in: int

    _created_at: datetime = PrivateAttr(default_factory=datetime.now)

    @computed_field
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self._created_at + timedelta(seconds=self.expires_in) 

class MSTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int

    _created_at: datetime = PrivateAttr(default_factory=datetime.now)
        
    @computed_field
    @property
    def expires_at(self) -> datetime:
        return self._created_at + timedelta(seconds=self.expires_in) 

class XboxTokenResponse(BaseModel):
    Token: str

    class _DisplayClaims(BaseModel):
        class _Xui(BaseModel):
            uhs: str

        xui: list[_Xui]

    DisplayClaims: _DisplayClaims

class XboxErrorResponse(BaseModel):
    XErr: int
    Message: str

class MCTokenResponse(BaseModel):
    username: str
    access_token: str
    expires_in: int

    _created_at: datetime = PrivateAttr(default_factory=datetime.now)
    
    @computed_field
    @property
    def expires_at(self) -> datetime:
        return self._created_at + timedelta(seconds=self.expires_in) 

class MCProfileResponse(BaseModel):
    id: str
    name: str

#region #! 一些常量
APP_ID = "ba0066a5-1eee-4e44-bf56-5687702e170c"

GET_DEVICE_CODE = f"https://login.live.com/oauth20_connect.srf"

GET_MS_TOKEN = f"https://login.live.com/oauth20_token.srf"

GET_XBOX_TOKEN = "https://user.auth.xboxlive.com/user/authenticate"

GET_XSTS_TOKEN = "https://xsts.auth.xboxlive.com/xsts/authorize"

GET_MC_ACCESS_TOKEN = "https://api.minecraftservices.com/authentication/login_with_xbox"

GET_MC_PROFILE = "https://api.minecraftservices.com/minecraft/profile"

REFRESH_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
#endregion


class RefreshAccount(Task):
    
    class State(Enum):
        ACCOUNT_NOT_FOUND = auto()
        OFFLINE_ACCOUNT = auto()

        TOKEN_EXPIRED = auto()

        XBOX_ERROR = auto()

    def __init__(self, account_name: str):
        self.account_name = account_name

        self.app_id = use_config().accounts.override.ms_client_id or APP_ID
        self.database = use_database()

    def refresh_ms(self, old_ms_refresh_token: str):
        response = requests.post(REFRESH_URL, data={
            "client_id": self.app_id,
            "grant_type": "refresh_token",
            "refresh_token": old_ms_refresh_token,
            # "scope": "XboxLive.signin XboxLive.offline_access"
        }, )

        if response.status_code != 200:
            raise TaskError(self.State.TOKEN_EXPIRED)  

        result = MSTokenResponse(**response.json())

        return result.refresh_token, result.access_token, result.expires_at

    def refresh_mc(self, ms_access_token: str):
        
        # 获取xbox令牌
        xbox_res = requests.post(GET_XBOX_TOKEN, json={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": f"d={ms_access_token}"     
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT"
            }, headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            })
        xbox_res.raise_for_status()
        xbox_token = XboxTokenResponse(**xbox_res.json())


        # 获取xsts令牌
        xsts_res = requests.post(GET_XSTS_TOKEN, headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        }, json={
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [ xbox_token.Token ]
            },
            "RelyingParty": "rp://api.minecraftservices.com/",   
            "TokenType": "JWT"
        })

        if xsts_res.status_code != 200:
            error_result = XboxErrorResponse(**xsts_res.json())

            message: str
            match error_result.XErr:
                case 2148916227:
                    message = "Xbox 账户被封禁。"

                case 2148916233:
                    message = "你的 Microsoft 账户没有 Xbox 账户。"

                case 2148916235:
                    message = "你所在的国家或地区不支持 Xbox Live 服务。"

                case 2148916236:
                    message = "在韩国地区，你需要先完成成人验证。"

                case 2148916237:
                    message = "在韩国地区，你需要先完成成人验证。"

                case _:
                    message = f"未知错误。{error_result.Message}"

            raise TaskError(self.State.XBOX_ERROR, {
                "message": message
            })

        xsts_result = XboxTokenResponse(**xsts_res.json())

        # 获取minecraft令牌
        mc_res =  requests.post(GET_MC_ACCESS_TOKEN, json={
                "identityToken": f"XBL3.0 x={xsts_result.DisplayClaims.xui[0].uhs};{xsts_result.Token}" 
            }, headers={"Content-Type": "application/json",
                        "Accept": "application/json"
                        }
            )
        mc_res.raise_for_status()

        mc_result = MCTokenResponse(**mc_res.json())

        return mc_result.access_token, mc_result.expires_at

    def run(self):
        yield None
        
        account = Accounts.get_or_none(Accounts.id == self.account_name)
        
        if account is None:
            raise TaskError(self.State.ACCOUNT_NOT_FOUND)

        if account.kind == "offline":
            raise TaskError(self.State.OFFLINE_ACCOUNT)

        is_refreshed = False

        if account.ms_expires_at < datetime.now():
            try:
                new_ms_refresh_token, new_ms_access_token, new_ms_expires_at = self.refresh_ms(account.ms_refresh_token)
            except TaskError as e:
                if e.message == self.State.TOKEN_EXPIRED:
                    with self.database.atomic():
                        account.delete_instance()

                raise e
            
            with self.database.atomic():
                account.ms_refresh_token = new_ms_refresh_token
                account.ms_access_token = new_ms_access_token
                account.ms_expires_at = new_ms_expires_at
                account.save()  
            
            is_refreshed = True
            
        if account.mc_expires_at < datetime.now():
            new_mc_access_token, new_mc_expires_at = self.refresh_mc(account.ms_access_token)

            with self.database.atomic():
                account.mc_access_token = new_mc_access_token
                account.mc_expires_at = new_mc_expires_at
                account.save()  

            is_refreshed = True

        if is_refreshed:
            return True
        else:
            return False


class New(Task):

    def __init__(self):
        self.ms_access_token: str
        self.ms_refresh_token: str
        self.ms_expires_at: datetime #指的是access_token的过期时间

        self.mc_access_token :str
        self.mc_expires_at: datetime

        self.cinder_name: str = "" # 此名称指的是Cinder内部保存账户的名称


    def run(self) -> Generator[StepUpdate | StepFinished, None, dict | None]:

        config = use_config()

        ms_app_id = config.accounts.override.ms_client_id or APP_ID

        # 发送请求获取登录代码
        res_ = requests.post(GET_DEVICE_CODE, data={
            "response_type": "device_code",
            "client_id": ms_app_id,
            "scope": "XboxLive.signin offline_access"
        }, headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }).json()

    
        try:
            result = DeviceCodeResponse(**res_)
        except ValidationError as e:
            raise TaskError(f"登录信息获取失败。{e}")

        # 打开浏览器让用户登录
        webbrowser.open(result.verification_uri)

        yield StepFinished("wait_login", {
            "user_code": result.user_code,
            "verification_uri": result.verification_uri
        })

        while True:
            if not result.is_expired:
                # 轮询查询登录状态
                res_ = requests.post(GET_MS_TOKEN, data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": ms_app_id,
                    "device_code": result.device_code,
                }, headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if res_.status_code == 200:
                    break

            else:
                raise TaskError("登录已超时，请重试。")

            time.sleep(1)

        try:
            result = MSTokenResponse(**res_.json())
        except ValidationError as e:
            raise TaskError(f"登录信息获取失败。{e}")

        self.ms_access_token = result.access_token
        self.ms_refresh_token = result.refresh_token

        self.ms_expires_at = result.expires_at


        yield StepFinished("getting_mc_token")

        self.mc_access_token, self.mc_expires_at = RefreshAccount("no").refresh_mc(self.ms_access_token)

        yield StepFinished("getting_profile")

        # 获取Minecraft玩家数据

        res_ = requests.get(GET_MC_PROFILE, headers={
            "Authorization": f"Bearer {self.mc_access_token}"
        })

        if res_.status_code != 200:
            # 当玩家数据不存在时，返回未购买游戏错误
            yield StepFinished("unbought_game", is_error=True)
            return

        result = MCProfileResponse(**res_.json())


        yield StepUpdate("username", {
            "username": f"{result.name}"
        })

        database = use_database(Accounts)

        yield StepFinished("login_success")

        while True:
            yield StepFinished("input_account_name")

            self.cinder_name = self.cinder_name.strip()
            
            if self.cinder_name != "":
                if Accounts.select().where(Accounts.id == self.cinder_name).exists():
                    yield StepUpdate("account_name_error")
                    continue
                else:
                    break


        with database.atomic():
            account = Accounts.create(
                kind="microsoft",
                id=self.cinder_name,
                name=result.name,
                uuid=result.id,
                ms_refresh_token=self.ms_refresh_token,
                ms_access_token=self.ms_access_token,
                ms_expires_at=self.ms_expires_at,
                mc_access_token=self.mc_access_token,
                mc_expires_at=self.mc_expires_at,
            )
        
        database.close()
            
        return {
            "account_name": self.cinder_name,
            "username": result.name
        }



class NewOffline(Task):

    def __init__(self):
        self.username: str = ""
        self.cinder_name : str = ""

    def run(self):
        database = use_database()
        
        yield StepFinished("input_username")

        while True:
            yield StepFinished("input_cinder_name")

            if self.cinder_name != "" and Accounts.get_or_none(Accounts.id == self.cinder_name) is None:
                break
            else:
                yield StepUpdate("account_name_error")
                self.cinder_name = ""

        
        with database.atomic():

            account = Accounts.create(
                kind="offline",
                id=self.cinder_name,
                name=self.username,
                uuid="",
                ms_refresh_token="",
                ms_access_token="",
                ms_expires_at=0,
                mc_access_token="",
                mc_expires_at=0,
            )

        




class AccountsSerivce:

    def __init__(self):
        self.new = New

        self.refresh = RefreshAccount
        self.new_offline = NewOffline   




    