from typing import Any

from playhouse.shortcuts import model_to_dict

from .base import CinderBlueprint, Response, EmptyModel
from ..services.accounts import AccountService
from core.utils.model import dkeys_snake_to_camel

accounts = CinderBlueprint("accounts", url_prefix="/api/accounts")


@accounts.get("getAll")
def get_all_accounts():
    accounts = AccountService().get_all_accounts()

    results: list = []

    for account in accounts:
        account.mc_access_token = ""
        account.ms_refresh_token = ""
        account.ms_access_token = ""

        results.append(dkeys_snake_to_camel(model_to_dict(account)))
        
    return Response(status=0, data={
        "accounts": results
    })

