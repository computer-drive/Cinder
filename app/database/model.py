from datetime import datetime

from peewee import (BlobField, ForeignKeyField, Model, IntegerField, AutoField,
    CharField, Check, DateTimeField, BooleanField, JSONField
)


class BaseModel(Model):
    pass

class Accounts(BaseModel):
    '''玩家账户'''
    # 玩家的账户类型 可以是 microsoft（微软账号）, offline（离线账号）, thirdparty（第三方账号，暂不支持）
    kind = CharField(constraints=[Check('kind in ("microsoft", "offline" )')])

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

        indexes = (
            (("path", "sha1"), True)
            ,
        )

    id = AutoField()
    path = CharField()
    sha1 = CharField()
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

    # 说明：用于处理1.6.x版本的资源文件索引
    virtual = BooleanField(default=False)

    # 说明：用于处理更早版本（<1.5.2）的资源文件索引
    map_to_resources = BooleanField(default=False)

class MCVersions(BaseModel):
    '''MC版本信息'''

    version = CharField(primary_key=True)

    type = CharField(constraints=[Check('type in ("release", "snapshot", "old_beta", "old_alpha")')])

    url = CharField()  # 版本数据的url
    time = DateTimeField() # 发布时间
    sha1 = CharField() # 版本数据的哈希
    is_safety = BooleanField() # 对应版本索引的complianceLevel键，1=true, 0=false

    assets = ForeignKeyField(MCAssetsIndex, backref='+', null=True)

    main_class = CharField(null=True) # 版本的主类
    
    java_major = IntegerField(null=True)

    client_files = CharField(null=True)  # 客户端jar文件的url
    client_sha1 = CharField(null=True)   # 客户端文件的哈希
    client_size = IntegerField(null=True) # 客户端文件的大小

    logging_argument = CharField(null=True) # 日志的启动参数
    
    logging_file = JSONField(null=True) # 日志的文件信息

    fetched_at = DateTimeField(null=True)

    class Meta:
        table_name = "meta:mc_versions"

        constraints = [
            Check(
                "( "
                "  (java_major   IS NULL     AND "
                "   client_files IS NULL     AND "
                "   client_sha1  IS NULL     AND "
                "   client_size  IS NULL     AND "
                "   fetched_at   IS NULL) "
                "  OR "
                "  (java_major   IS NOT NULL AND "
                "   client_files IS NOT NULL AND "
                "   client_sha1  IS NOT NULL AND "
                "   client_size  IS NOT NULL AND "
                "   logging_argument IS NOT NULL AND "
                "   logging_file IS NOT NULL AND "
                "   fetched_at   IS NOT NULL) "
                ")"
            )
        ]


class MCLibraries(BaseModel):
    '''MC的支持库信息'''
    class Meta:
        table_name = "meta:mc_libraries"

        indexes = (
            (('version', 'maven_path'), True),  # 对于一个版本，应该只出现一个支持库
        )

        constraints = [
            Check('is_native = true OR "order" IS NOT NULL'),
        ]

    version = ForeignKeyField(MCVersions, backref="+")

    maven_path = CharField()

    sha1 = CharField()
    size = IntegerField()
    url = CharField()

    rules = JSONField(null=True)

    is_native = BooleanField(default=False)

    order = IntegerField(null=True)

    name = CharField()

class MCArguments(BaseModel):
    '''MC的启动参数'''
    class Meta:
            table_name = "meta:mc_arguments"


    version = ForeignKeyField(MCVersions, backref="+", primary_key=True)

    jvm = JSONField(null=True)

    game = JSONField()

class MCAssetsObjects(BaseModel):
    '''MC资源文件的对象'''
    class Meta:
        table_name = "meta:mc_assets_objects"

        indexes = (
            (('assets_index', 'name'), True),  # 对于一个索引，应该只出现一个object

        )

    id = AutoField()

    assets_index = ForeignKeyField(MCAssetsIndex, backref="+")

    name = CharField()

    hash = CharField()

    size = IntegerField()


class Java(BaseModel):
    '''Java运行时信息'''
    class Meta:
        table_name = "java"

    path = CharField(primary_key=True)

    major_version = IntegerField()

    version = CharField()

    vendor = CharField()

class Instances(BaseModel):
    class Meta:
        table_name = "instances"

    name = CharField(primary_key=True)

    version = ForeignKeyField(MCVersions, backref="+")

    client_file = ForeignKeyField(Files, backref="+")

    logging_config = ForeignKeyField(Files, backref="+") # 日志配置文件

    default_account = ForeignKeyField(Accounts, backref="+", null=True, on_delete='SET NULL')

    default_java = ForeignKeyField(Java, backref="+", null=True, on_delete='SET NULL')

    

    startup_count = IntegerField(default=0) # 启动次数





class AssetsReference(BaseModel):
    class Meta:
        table_name = "assets_reference"
        indexes = (
            (('instance', 'asset_file'), True),  # 同一个版本，应该只出现一个资源文件的引用
        )

    id =  AutoField()

    asset = ForeignKeyField(MCAssetsObjects, backref="+")

    asset_file = ForeignKeyField(Files, backref="+")

    instance = ForeignKeyField(Instances, backref="+")



class LibrariesReference(BaseModel):
    class Meta:
        table_name = "libraries_reference"
        indexes = (
            (('instance', 'library_file'), True),  # 同一个版本，应该只出现一个支持库的引用
        )

    id =  AutoField()

    library = ForeignKeyField(MCLibraries, backref="+")

    library_file = ForeignKeyField(Files, backref="+")

    instance = ForeignKeyField(Instances, backref="+")



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
    Java,
]




