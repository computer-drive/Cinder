
from enum import Enum, auto
from datetime import datetime, timedelta
import requests
from typing import Any, Literal

from pydantic import BaseModel, computed_field, PrivateAttr

from ...database import use_database
from ...database.model import Accounts

from ...logging import get_logger
from ...config import use_config

#region Pydantic Models
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
#endregion

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


class RefreshResult(Enum):
    SUCCESS = auto()
    ACCOUNT_NOT_FOUND = auto()
    TOKEN_EXPIRED = auto()
    OFFLINE_ACCOUNT = auto()

    XBOX_ERROR = auto()

    UNREFRESHED = auto()

class AccountService:
    RefreshResult = RefreshResult

    def __init__(self):
        self.db = use_database()

        self.app_id = use_config().accounts.override.ms_client_id or APP_ID


    def get_all_accounts(self):
        return list(Accounts.select())

    def delete_account(self, account_id: str):
        with self.db.atomic():
            rows_deleted = Accounts.delete().where(Accounts.id == account_id).execute()

        if rows_deleted == 0:
            return False
        else:
            get_logger("Accounts").info(f"删除了账户 {account_id}")

            return True

    
    def __refresh_ms(self, old_ms_refresh_token: str) -> tuple[Literal[False], None] | tuple[Literal[True], tuple[str, str, datetime]]:
        response = requests.post(REFRESH_URL, data={
            "client_id": self.app_id,
            "grant_type": "refresh_token",
            "refresh_token": old_ms_refresh_token,
            # "scope": "XboxLive.signin XboxLive.offline_access"
        }, )

        if response.status_code != 200:
            return False, None

        result = MSTokenResponse(**response.json())

        return True, (result.refresh_token, result.access_token, result.expires_at)

    def __refresh_mc(self, ms_access_token: str) -> tuple[Literal[False], str] | tuple[Literal[True], tuple[str, datetime]]:
            
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
    
                return False, message
    
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
    
            return True, (mc_result.access_token, mc_result.expires_at)
    


    def refresh_account(self, account_id: str):
        logger = get_logger("Accounts")
        logger.info(f"正在刷新账户 {account_id} 的令牌...")

        account = Accounts.get_or_none(Accounts.id == account_id)

        if account is None:
            logger.error(f"账户 {account_id} 不存在，结束。")
            return RefreshResult.ACCOUNT_NOT_FOUND, None

        if account.kind == "offline":
            logger.error(f"账户 {account_id} 是离线账户，结束。")
            return RefreshResult.OFFLINE_ACCOUNT, None


        is_refreshed = False
        new_ms_refresh_token = ""
        new_ms_access_token = ""
        new_ms_expires_at = ""
        new_mc_access_token = ""
        new_mc_expires_at = ""

        if account.ms_expires_at < datetime.now():
            result, data = self.__refresh_ms(account.ms_refresh_token)
            
            if result is False or data is None:
                with self.db.atomic():
                    account.delete_instance()
                    account.save()

                logger.error(f"账户 {account_id} 的 Microsoft 令牌过期了，账户已被删除。结束。")
                return RefreshResult.TOKEN_EXPIRED, None
            
            new_ms_refresh_token, new_ms_access_token, new_ms_expires_at = data

            with self.db.atomic():
                account.ms_refresh_token = new_ms_refresh_token
                account.ms_access_token = new_ms_access_token
                account.ms_expires_at = new_ms_expires_at
                account.save()  

            logger.info(f"账户 {account_id} 的 Microsoft 令牌刷新成功。")
            
            is_refreshed = True
            
        if account.mc_expires_at < datetime.now():
            result, data = self.__refresh_mc(account.ms_access_token)

            if result is False:
                logger.error(f"账户 {account_id} 的 Minecraft 令牌刷新失败，结束。{data}")
                return RefreshResult.XBOX_ERROR, data
            
            assert not isinstance(data, str)

            new_mc_access_token, new_mc_expires_at = data

            with self.db.atomic():
                account.mc_access_token = new_mc_access_token
                account.mc_expires_at = new_mc_expires_at
                account.save()  

            logger.info(f"账户 {account_id} 的 Minecraft 令牌刷新成功。")

            is_refreshed = True

        if is_refreshed:
            return RefreshResult.SUCCESS, account
        else:
            logger.info(f"账户 {account_id} 的令牌没有过期，结束。")

            # 这里的意思是没刷新任何东西
            return RefreshResult.UNREFRESHED, account

        



           

        
        
