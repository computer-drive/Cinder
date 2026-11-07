from peewee import (Model,
    DatabaseProxy, CharField, Check, DateTimeField,)



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

