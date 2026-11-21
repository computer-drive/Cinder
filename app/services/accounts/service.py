from ...database import use_database
from ...database.model import Accounts

class AccountService:
    def __init__(self):
        self.db = use_database()

    def get_all_accounts(self):
        return list(Accounts.select())
        
