import os
import webbrowser
from datetime import datetime, timedelta


lazy import requests
from pydantic import BaseModel, ValidationError, computed_field, PrivateAttr

lazy from ..database import use_database
lazy from ..database.model import Accounts
from .base import Task, StepUpdate, StepFinished



GET_DEVICE_CODE = f"https://login.live.com/oauth20_connect.srf"

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

APP_ID = "ba0066a5-1eee-4e44-bf56-5687702e170c"
    

GET_MS_TOKEN = f"https://login.live.com/oauth20_token.srf"

GET_XBOX_TOKEN = "https://user.auth.xboxlive.com/user/authenticate"

GET_XSTS_TOKEN = "https://xsts.auth.xboxlive.com/xsts/authorize"

GET_MC_ACCESS_TOKEN = "https://api.minecraftservices.com/authentication/login_with_xbox"

GET_MC_PROFILE = "https://api.minecraftservices.com/minecraft/profile"

class _New(Task):

    def __init__(self):
        self.ms_access_token: str
        self.ms_refresh_token: str
        self.ms_expires_at: datetime #指的是access_token的过期时间

        self.mc_access_token :str
        self.mc_expires_at: datetime

        self.account_name: str = ""


    def run(self):

        APP_ID_ =  os.environ.get("cinder_override_app_id", None)

        if APP_ID_ is not None:
            yield StepUpdate("preparing", {
                "message": "注意，您正在使用被被覆写的AppID进行登录。"
            })
        else:
            APP_ID_ = APP_ID

        
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

            yield StepFinished("error", {
                "message": f"登录信息获取失败。{e}",
                "data": res_
            }, True)
            return
            
        webbrowser.open(result.verification_uri)

        yield StepFinished("wait_login", {
            "user_code": result.user_code,
            "verification_uri": result.verification_uri
        })

        while True:
            if not result.is_expired:

                res_ = requests.post(GET_MS_TOKEN, data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": APP_ID_,
                    "device_code": result.device_code,
                }, headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if res_.status_code == 200:
                    break

            else:
                yield StepFinished("error", {
                    "message": "登录已超时，请重试。",
                    "data": ""
                }, True)
                return 

        try:
            result = MSTokenResponse(**res_.json())
        except ValidationError:
            yield StepFinished("error", {
                "message": f"登录信息获取失败。",
                "data": res_.json()
            }, True)
            return

        self.ms_access_token = result.access_token
        self.ms_refresh_token = result.refresh_token

        self.ms_expires_at = result.expires_at


        yield StepFinished("getting_xbox")

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
            yield StepFinished("error", {
                "message": f"登录信息获取失败。{e}",
                "data": res_
            }, True)
            return

    
        yield StepFinished("getting_xsts")

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

                yield StepFinished("error", {
                    "message": message,
                    "data": f"错误代码：{result.XErr}，{result.Message}"
                })

                return

            else:
                result = XboxTokenResponse(**res_.json())

        except ValidationError as e:
            yield StepFinished("error", {
                "message": f"登录信息获取失败。{e}",
                "data": res_
            }, True)
            return

        yield StepFinished("getting_mc_token")

        try:
            res_ = requests.post(GET_MC_ACCESS_TOKEN, json={
                "identityToken": f"XBL3.0 x={result.DisplayClaims.xui[0].uhs};{result.Token}" 
            }, headers={"Content-Type": "application/json",
                        "Accept": "application/json"
                        }
            ).json()

            result = MCTokenResponse(**res_)

        except ValidationError as e:
            yield StepFinished("error", {
                "message": f"登录信息获取失败。{e}",
                "data": res_
            }, True)

        else:
            self.mc_expires_at = result.expires_at
            self.mc_access_token = result.access_token

        yield StepFinished("getting_profile")

        
        try:
            res_ = requests.get(GET_MC_PROFILE, headers={
                "Authorization": f"Bearer {self.mc_access_token}"
            })

            if res_.status_code != 200:
                yield StepFinished("unbought_game", is_error=True)
                return

            result = MCProfileResponse(**res_.json())

        except ValidationError as e:
            yield StepFinished("error", {
                "message": f"登录信息获取失败。{e}",
                "data": res_
            }, True)
        else:

            self.username = result.id

            yield StepUpdate("username", {
                "message": f"玩家名：{result.name}"
            })

        
            yield StepFinished("input_account_name")

            database = use_database(Accounts)

            with database.atomic():
                account = Accounts.create(
                    kind="microsoft",
                    id=self.account_name,
                    name=result.name,
                    uuid=result.id,
                    ms_refresh_token=self.ms_refresh_token,
                    ms_access_token=self.ms_access_token,
                    ms_expires_at=self.ms_expires_at,
                    mc_access_token=self.mc_access_token,
                    mc_expires_at=self.ms_expires_at,
                )
                

            return {
                "account_name": self.account_name,
                "username": result.name
            }

        



class AccountsSerivce:

    def __init__(self):
        self.new = _New




    