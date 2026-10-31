from core.arguments import Parser

accounts = Parser("accounts", "管理 Microsoft 账户")

@accounts.command("add", "添加一个 Microsoft 账户")
def add_account():
    pass