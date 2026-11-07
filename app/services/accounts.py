import os
import webbrowser
from datetime import datetime, timedelta
import time
from typing import Generator

lazy import requests
from pydantic import BaseModel, ValidationError, computed_field, PrivateAttr

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
#endregion

class _New(Task):

    def __init__(self):
        self.ms_access_token: str
        self.ms_refresh_token: str
        self.ms_expires_at: datetime #指的是access_token的过期时间

        self.mc_access_token :str
        self.mc_expires_at: datetime

        self.cinder_name: str = "" # 此名称指的是Cinder内部保存账户的名称


    def run(self) -> Generator[StepUpdate | StepFinished, None, dict | None]:

        # 从环境变量取被覆写的值
        APP_ID_ =  os.environ.get("cinder_override_app_id", None)

        if APP_ID_ is not None:
            yield StepUpdate("preparing", {
                "message": "注意，您正在使用被被覆写的AppID进行登录。"
            })
        else:
            APP_ID_ = APP_ID

        # 发送请求获取登录代码
        res_ = requests.post(GET_DEVICE_CODE, data={
            "response_type": "device_code",
            "client_id": APP_ID_,
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
                    "client_id": APP_ID_,
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


        yield StepFinished("getting_xbox")

        # 拿Xbox令牌
        try:
            res_ =  requests.post(GET_XBOX_TOKEN, json={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": f"d={self.ms_access_token}"     
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT"
            }, headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }).json()

            result =XboxTokenResponse(**res_)

        except ValidationError as e:
            raise TaskError(f"登录信息获取失败。{e}")


        yield StepFinished("getting_xsts")

        # 拿XSTS令牌
        res_ = requests.post(GET_XSTS_TOKEN, headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        }, json={
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [ result.Token ]
            },
            "RelyingParty": "rp://api.minecraftservices.com/",   
            "TokenType": "JWT"
        })

        try:
            if res_.status_code != 200:
                result = XboxErrorResponse(**res_.json())

                message: str = ""
                match result.XErr:
                    case 2148916227:
                        message = "无法登录，Xbox 账户被封禁。"

                    case 2148916233:
                        message = "无法登录，你的 Microsoft 账户没有 Xbox 账户。"

                    case 2148916235:
                        message = "无法登录，你所在的国家或地区不支持 Xbox Live 服务。"

                    case 2148916236:
                        message = "无法登录，在韩国地区，你需要先完成成人验证。"

                    case 2148916237:
                        message = "无法登录，在韩国地区，你需要先完成成人验证。"

                    case _:
                        message = "未知错误。"

                raise TaskError(message, {
                    "code": result.XErr,
                    "message": result.Message
                })

            else:
                result = XboxTokenResponse(**res_.json())

        except ValidationError as e:
            raise TaskError(f"登录信息获取失败。{e}")

        yield StepFinished("getting_mc_token")

        # 获取Minecraft令牌
        try:
            res_ = requests.post(GET_MC_ACCESS_TOKEN, json={
                "identityToken": f"XBL3.0 x={result.DisplayClaims.xui[0].uhs};{result.Token}" 
            }, headers={"Content-Type": "application/json",
                        "Accept": "application/json"
                        }
            ).json()

            result = MCTokenResponse(**res_)

        except ValidationError as e:
            raise TaskError(f"登录信息获取失败。{e}", {
                "data": res_
            })

        else:
            self.mc_expires_at = result.expires_at
            self.mc_access_token = result.access_token

        yield StepFinished("getting_profile")

        
        # 获取Minecraft玩家数据
        try:
            res_ = requests.get(GET_MC_PROFILE, headers={
                "Authorization": f"Bearer {self.mc_access_token}"
            })

            if res_.status_code != 200:
                # 当玩家数据不存在时，返回未购买游戏错误
                yield StepFinished("unbought_game", is_error=True)
                return

            result = MCProfileResponse(**res_.json())

        except ValidationError as e:
            raise TaskError(f"登录信息获取失败。{e}")
        else:


            yield StepUpdate("username", {
                "message": f"玩家名：{result.name}"
            })

            database = use_database(Accounts)

            while True:
                yield StepFinished("input_account_name")

                self.cinder_name = self.cinder_name.strip()
                
                if self.cinder_name != "":
                    if Accounts.select().where(Accounts.id == self.cinder_name).exists():
                        yield StepUpdate("account_name", {
                            "message": "账号名已存在。"
                        })
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

        



class AccountsSerivce:

    def __init__(self):
        self.new = _New




    