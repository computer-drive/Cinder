lazy from peewee import SqliteDatabase

lazy from ..paths import paths

from .model import BaseModel, ALL

database: SqliteDatabase | None = None

def use_database(*models: type[BaseModel]) -> SqliteDatabase:
    '''使用数据库。注意models参数现在没有作用了。'''
    global database

    if database is None:
        database = SqliteDatabase(str(paths.userdata_db))

        database.connect()


        database.bind(ALL)
        database.create_tables(ALL, safe=True)

    return database
    
