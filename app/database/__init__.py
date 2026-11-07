lazy from peewee import SqliteDatabase

lazy from ..paths import paths

from .model import BaseModel 

def use_database(*models: type[BaseModel]):

    db = SqliteDatabase(str(paths.userdata_db))

    db.connect()


    db.bind(models)
    db.create_tables(models)

    return db
    
