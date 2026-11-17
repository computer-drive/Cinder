import tomlkit
from pydantic import ValidationError
import sys

from core.terminal.console import Console
from .schema import Config
from ..paths import paths

_config: Config | None = None

def use_config():
    global _config
    if _config is None:
        config_path = paths.data / "config.toml"

        if not config_path.exists():
            config_path.write_text(
                tomlkit.dumps(tomlkit.item(Config().model_dump(exclude_none=True))),
                encoding="utf-8"
            )

        
        document = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    
        try:
            config = Config.model_validate(document.unwrap())
        except ValidationError as e:
            c = Console.get_instance()
    
            c.error("配置文件格式有误！")
            c.error(str(e))

            sys.exit(1)

        else:
            _config = config

    return _config



