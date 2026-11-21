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






class RefreshAccount(Task[tuple[bool, Accounts]]):
    
    class State(Enum):
        ACCOUNT_NOT_FOUND = auto()
        OFFLINE_ACCOUNT = auto()

        TOKEN_EXPIRED = auto()

        XBOX_ERROR = auto()

    def __init__(self, account_name: str):
        self.account_name = account_name

        self.app_id = use_config().accounts.override.ms_client_id or APP_ID
        self.database = use_database()

    

    
    def run(self) -> Generator[StepUpdate, None, tuple[bool, Accounts]]:
        yield StepUpdate("FUCK!")
        
        account = Accounts.get_or_none(Accounts.id == self.account_name)
        
        if account is None:
            raise TaskError(self.State.ACCOUNT_NOT_FOUND)

        if account.kind == "offline":
            raise TaskError(self.State.OFFLINE_ACCOUNT)

        is_refreshed = False

        i


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




    