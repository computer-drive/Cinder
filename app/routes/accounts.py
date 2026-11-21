from typing import Any

from playhouse.shortcuts import model_to_dict
from pydantic import BaseModel, Field
from requests.exceptions import RequestException

from .base import CinderBlueprint, Response
from ..services.accounts import AccountService
from core.utils.model import dkeys_snake_to_camel

accounts = CinderBlueprint("accounts", url_prefix="/api/accounts")


@accounts.get("getAll")
def get_all_accounts():
    accounts = AccountService().get_all_accounts()

    results: list[dict[str, Any]] = []

    for account in accounts:
        account.mc_access_token = ""
        account.ms_refresh_token = ""
        account.ms_access_token = ""

        results.append(dkeys_snake_to_camel(model_to_dict(account)))
        
    return Response(status=0, data={
        "accounts": results
    })


class AccountBase(BaseModel):
    account_id: str = Field(alias="accountID")

@accounts.post("delete", AccountBase)
def delete_account(params: AccountBase):

    success = AccountService().delete_account(params.account_id)
    
    if success:
        return Response(status=0)
    else:
        return Response(status=1, message="ACCOUNT_NOT_FOUND")

@accounts.post("refresh", AccountBase)
def refresh_account(params: AccountBase):
    result = AccountService().refresh_account(params.account_id)

    if result[0] == AccountService.RefreshResult.SUCCESS:
        return Response(status=0)
    elif result[0] == AccountService.RefreshResult.ACCOUNT_NOT_FOUND:
        return Response(status=10, message="ACCOUNT_NOT_FOUND")
    elif result[0] == AccountService.RefreshResult.TOKEN_EXPIRED:
        return Response(status=11, message="TOKEN_EXPIRED")
    elif result[0] == AccountService.RefreshResult.OFFLINE_ACCOUNT:
        return Response(status=12, message="OFFLINE_ACCOUNT")

    elif result[0] == AccountService.RefreshResult.XBOX_ERROR:
        return Response(status=13, message="XBOX_ERROR", data={
            "error": result[1]
        })

    elif result[0] == AccountService.RefreshResult.UNREFRESHED:
        return Response(status=14, message="UNREFRESHED")
    else:
        # 不他妈可能走到这里
        return Response(status=15, message="UNKNOWN_ERROR")
    
    
    



    


