from datetime import datetime

from peewee import (BlobField, ForeignKeyField, Model, IntegerField, AutoField,
    CharField, Check, DateTimeField, BooleanField, JSONField
)


class BaseModel(Model):
    pass

class Accounts(BaseModel):
    '''玩家账户'''
    # 玩家的账户类型 可以是 microsoft（微软账号）, offline（离线账号）, thirdparty（第三方账号，暂不支持）
    kind = CharField(constraints=[Check('kind in ("microsoft", "offline", )')])

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

class Files(BaseModel):
    class Meta:
        table_name = "files"

    id = AutoField()
    path = CharField(unique=True)
    sha1 = CharField(unique=True)
    size = IntegerField()
    created_at = DateTimeField(default=datetime.now)


class MCAssetsIndex(BaseModel):
    '''MC资源文件的索引'''
    class Meta:
        table_name = "meta:mc_assets_index"

    id = CharField(primary_key=True)

    sha1 = CharField()

    size = IntegerField()
    total_size = IntegerField()

    url = CharField()

    virtual = BooleanField(default=False)

class MCVersions(BaseModel):
    '''MC版本信息'''

    version = CharField(primary_key=True)

    type = CharField(constraints=[Check('type in ("release", "snapshot", "old_beta", "old_alpha")')])

    url = CharField()  # 版本数据的url
    time = DateTimeField() # 发布时间
    sha1 = CharField() # 版本数据的哈希
    is_safety = BooleanField() # 对应版本索引的complianceLevel键，1=true, 0=false

    assets = ForeignKeyField(MCAssetsIndex, backref='tweets', null=True)

    main_class = CharField(null=True) # 版本的主类
    
    java_major = IntegerField(null=True)

    client_files = CharField(null=True)  # 客户端jar文件的url
    client_sha1 = CharField(null=True)   # 客户端文件的哈希
    client_size = IntegerField(null=True) # 客户端文件的大小


    fetched_at = DateTimeField(null=True)

    class Meta:
        table_name = "meta:mc_versions"


class MCLibraries(BaseModel):
    '''MC的支持库信息'''
    class Meta:
        table_name = "meta:mc_libraries"

        indexs = (
            (('version', 'maven_path'), True),  # 对于一个版本，应该只出现一个支持库
        )

    version = ForeignKeyField(MCVersions, backref="tweets")

    maven_path = CharField()

    sha1 = CharField()
    size = IntegerField()
    url = CharField()


    name = CharField()

class MCArguments(BaseModel):
    '''MC的启动参数'''
    class Meta:
            table_name = "meta:mc_arguments"


    version = ForeignKeyField(MCVersions, backref="tweets", primary_key=True)

    default_user_jvm = JSONField(null=True) # 这个参数是26.3版本新加的

    jvm = JSONField(null=True)

    game = JSONField()

class MCAssetsObjects(BaseModel):
    '''MC资源文件的对象'''
    class Meta:
        table_name = "meta:mc_assets_objects"

        indexs = (
            (('assets_index', 'name'), True),  # 对于一个索引，应该只出现一个object

        )

    id = AutoField()

    assets_index = ForeignKeyField(MCAssetsIndex, backref="tweets")

    name = CharField()

    hash = CharField()

    size = IntegerField()


class AssetsReference(BaseModel):
    class Meta:
        table_name = "assets_reference"
        indexs = (
            (('version', 'asset_file'), True),  # 同一个版本，应该只出现一个资源文件的引用
        )

    id =  AutoField()

    asset_file = ForeignKeyField(Files, backref="+")

    version = ForeignKeyField(MCVersions, backref="+")

class LibrariesReference(BaseModel):
    class Meta:
        table_name = "libraries_reference"
        indexs = (
            (('version', 'library_file'), True),  # 同一个版本，应该只出现一个支持库的引用
        )

    id =  AutoField()

    library_file = ForeignKeyField(Files, backref="+")

    version = ForeignKeyField(MCVersions, backref="+")

class Instances(BaseModel):
    class Meta:
        table_name = "instances"

    name = CharField(primary_key=True)

    version = ForeignKeyField(MCVersions, backref="+")

    client_file = ForeignKeyField(Files, backref="+")



ALL = [Accounts,
    MCVersions,
    Instances, 
    MCAssetsObjects,
    MCAssetsIndex,
    AssetsReference,
    LibrariesReference,
    Files,
    MCLibraries,
    MCArguments,
    MCAssetsObjects,
]




