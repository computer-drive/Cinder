

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


class MCVersions(BaseModel):
    class Meta:
        table_name = "meta:mc_versions"
        
    version = CharField(primary_key=True)
    type = CharField(constraints=[Check('type in ("release", "snapshot", "old_beta", "old_alpha")')])

    url = CharField()  # 版本数据的url

    time = DateTimeField() # 发布时间

    sha1 = CharField() # 版本数据的哈希

    is_safety = BooleanField()

    data = JSONField(null=True)
    
    fetchd_at = DateTimeField(null=True)


class ClientFiles(BaseModel):
    class Meta:
        table_name = "client_files"

    id =  AutoField()

    path = CharField(unique=True)

    sha1 = CharField(unique=True)

    size = IntegerField()

    created_at = DateTimeField()




class Instances(BaseModel):
    class Meta:
        table_name = "instances"

    name = CharField(primary_key=True)

    version = ForeignKeyField(MCVersions, backref="tweets")

    client_file = ForeignKeyField(ClientFiles, backref="tweets")





