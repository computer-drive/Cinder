from typing import Literal

from pydantic import BaseModel

class Config(BaseModel):

    class Accounts(BaseModel):

        class Override(BaseModel):
            ms_client_id: str = ""
            ms_redirect_uri: str = ""

        override: Override = Override()

        allow_offline_account: bool = False

    class System(BaseModel):
        debug: bool = False

        server_port: int = 1231

        auto_start_web_browser: bool = True # 在启动服务器后自动打开浏览器

    system: System = System()


    accounts: Accounts = Accounts()

    





            
