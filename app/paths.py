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
    def config(self):
        return self.data / "configuration.toml"

    @property
    def userdata_db(self):
        return self.data / "userdata.db"

    @property
    def cache_db(self):
        return self.cache / "cache.db"

    @property
    def libraries(self):
        return self.cache / "libraries"

    @property
    def assets(self):
        return self.cache / "assets"

    @property
    def mods(self):
        return self.data / "mods"

    @property
    def instances(self):
        return self.data / "instances"

    @property
    def gamedata(self):
        return self.data / "gamedata"

    def ensure(self):
        '''确保所有路径存在，若不存在则会创建'''
        for path in [self.config, self.cache, self.libraries,
                self.assets, self.mods, self.instances, self.gamedata]:
            path.mkdir(parents=True, exist_ok=True)

        return self

        
paths = Paths.get_paths()