

from peewee import (BlobField, ForeignKeyField, Model, IntegerField, AutoField,
    CharField, Check, DateTimeField, BooleanField, JSONField
)


class BaseModel(Model):
    pass

class Accounts(BaseModel):
    # 玩家的账户类型 可以是 microsoft（微软账号）, offline（离线账号）, thirdparty（第三方账号）
    kind = CharField(constraints=[Check('kind in ("microsoft", "offline")')])

    id = CharField(primary_key=True,) # 玩家的账户的ID，在启动器内部的唯一标识

    name = CharField() # 玩家的账户名称（也就是玩家的Xbox名称，游戏里的名称）
    uuid = CharField() # 玩家的账户UUID（注意这里与传统的uuid不同，应该取消"-"连字符）

    ms_refresh_token = CharField() # 微软账号的令牌
    ms_access_token = CharField() # 微软账号的访问令牌
    ms_expires_at = DateTimeField() # 微软账号的访问令牌过期时间

    mc_access_token = CharField() # 游戏凭证
    mc_expires_at = DateTimeField() # 游戏凭证过期时间

    class Meta:
        table_name = 'accounts'


class MCAssetsIndex(BaseModel):

    class Meta:
        table_name = "meta:mc_assets_index"

    id = IntegerField(primary_key=True)

    sha1 = CharField()

    size = IntegerField()
    total_size = IntegerField()

    url = CharField()

    virtual = BooleanField(default=False)

class MCVersions(BaseModel):
    version = CharField(primary_key=True)
    type = CharField(constraints=[Check('type in ("release", "snapshot", "old_beta", "old_alpha")')])

    url = CharField()  # 版本数据的url
    time = DateTimeField() # 发布时间
    sha1 = CharField() # 版本数据的哈希
    is_safety = BooleanField()


    assets = ForeignKeyField(MCAssetsIndex, backref='tweets', null=True)

    main_class = CharField(null=True) # 版本的主类
    
    java_major = IntegerField(null=True)

    client_files = CharField(null=True)  # 客户端jar文件的url
    client_sha1 = CharField(null=True)   # 客户端文件的哈希
    client_size = IntegerField(null=True) # 客户端文件的大小

    fetched_at = DateTimeField(null=True)

    class Meta:
        table_name = "meta:mc_versions"
        constraints = [Check('')]

# ! WIP
# class MCLibraries(BaseModel):
#     class Meta:
#         table_name = "meta:mc_libraries"

#     version = ForeignKeyField(MCVersions, backref="tweets", primary_key=True)

#     name = CharField()

class MCArguments(BaseModel):
    class Meta:
        table_name = "meta:mc_arguments"

        version = ForeignKeyField(MCVersions, backref="tweets", primary_key=True)

        default_user_jvm = JSONField(null=True)

        jvm = JSONField(null=True)

        game = JSONField()

class MCAssetsObjects(BaseModel):
    class Meta:
        table_name = "meta:mc_assets_objects"

    id = AutoField()

    assets_index = ForeignKeyField(MCAssetsIndex, backref="tweets")

    name = CharField()

    hash = CharField()

    size = CharField()



class ClientFiles(BaseModel):
    class Meta:
        table_name = "client_files"

    id =  AutoField()

    path = CharField(unique=True)

    sha1 = CharField(unique=True)

    size = IntegerField()

    created_at = DateTimeField()

class AssetsFiles(BaseModel):
    class Meta:
        table_name = "assets_files"

    id =  AutoField()

    path = CharField(unique=True) # 存储相对路径

    sha1 = CharField(unique=True)

    size = IntegerField()

    created_at = DateTimeField()

class AssetsReference(BaseModel):
    class Meta:
        table_name = "assets_reference"

    id =  AutoField()

    asset_file = ForeignKeyField(AssetsFiles, backref="tweets")
    version = ForeignKeyField(MCVersions, backref="tweets")

class LibrariesFiles(BaseModel):
    class Meta:
        table_name = "libraries_files"

    id =  AutoField()

    path = CharField(unique=True) # 存储相对路径

    sha1 = CharField(unique=True)

    size = IntegerField()

    created_at = DateTimeField()

class LibrariesReference(BaseModel):
    class Meta:
        table_name = "libraries_reference"

    id =  AutoField()

    library_file = ForeignKeyField(LibrariesFiles, backref="tweets")
    version = ForeignKeyField(MCVersions, backref="tweets")


class Instances(BaseModel):
    class Meta:
        table_name = "instances"

    name = CharField(primary_key=True)

    version = ForeignKeyField(MCVersions, backref="tweets")

    client_file = ForeignKeyField(ClientFiles, backref="tweets")


ALL = [Accounts,
    MCVersions,
    ClientFiles,
    Instances, 
    MCAssetsObjects,
    MCAssetsIndex,
    AssetsFiles,
    AssetsReference,
    LibrariesFiles,
    LibrariesReference
]




