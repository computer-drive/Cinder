from typing import Literal

from pydantic import BaseModel

class Config(BaseModel):

    class Accounts(BaseModel):

        class Override(BaseModel):
            ms_client_id: str = ""

        override: Override = Override()

        allow_offline_account: bool = False

    class System(BaseModel):
        debug: bool = False

        server_port: int = 1231

    system: System = System()


    accounts: Accounts = Accounts()

    





            
