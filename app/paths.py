from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Paths:
    data: Path
    cache: Path

    @classmethod
    def get_paths(cls):
        return cls(
            Path.home() / ".cinder",
            Path.home() / ".cinder" / "cache"
        ).ensure()

    

    @property
    def lock(self):
        return self.data / "cinder.lock" # 排它锁文件
    
    @property
    def config(self):
        return self.data / "configuration.toml" # 配置文件

    @property
    def userdata_db(self):
        return self.data / "userdata.db" # 用户数据

    @property
    def libraries(self):
        return self.data / "libraries"  # 共享库

    @property
    def assets(self):
        return self.data / "assets"   # 共享assets资源

    @property
    def mods(self):
        return self.data / "mods" # 共享mods

    @property
    def instances(self):
        return self.data / "instances" # 实例的jar文件

    @property
    def gamedata(self):
        return self.data / "gamedata" # 游戏数据

    def ensure(self):
        '''确保所有路径存在，若不存在则会创建'''
        for path in [self.config, self.cache, self.libraries,
                self.assets, self.mods, self.instances, self.gamedata]:
            path.mkdir(parents=True, exist_ok=True)

        return self

        
paths: Paths = Paths.get_paths().ensure()