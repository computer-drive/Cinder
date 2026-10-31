lazy from peewee import SqliteDatabase

lazy from .model import db_proxy
lazy from ..paths import paths

from .model import Accounts # 导出

def use_database():
    db = SqliteDatabase(str(paths.userdata_db))

    db_proxy.initialize(db)
