lazy from peewee import SqliteDatabase

lazy from ..paths import paths

from .model import BaseModel 

database: SqliteDatabase | None = None

def use_database(*models: type[BaseModel]) -> SqliteDatabase:
    global database

    if database is None:
        database = SqliteDatabase(str(paths.userdata_db))

        database.connect()


        database.bind(models)
        database.create_tables(models)

    return database
    
