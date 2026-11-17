from enum import Enum, auto
import hashlib

from pydantic import TypeAdapter, BaseModel

from ..base import Task, StepFinished, StepUpdate, TaskError
from ...database import use_database
from ...database.model import LibrariesReference, MCLibraries, MCVersions, Instances, MCArguments
from .schema import Rule, match_rules
from ...paths import paths
from core.utils.format import substitute

class State(Enum):
    VERSION_NOT_FOUND = auto()


class ArgumentRules(BaseModel):
    rules: list[Rule]
    value: str | list[str]

rule = TypeAdapter(list[ArgumentRules | str])

class LaunchTask(Task):

    def __init__(self, instance_name: str):
        self.instance_name = instance_name

        self.database = use_database()

        self.State = State

        self.features = {
            "is_demo_user": True,
            "has_custom_resolution": False,
            "has_custom_resolution": False,
            "is_quick_play_singleplayer": False,
            "is_quick_play_multiplayer":  False,
            "is_quick_play_realms": False
        }

        self.formatter ={
            "auth_player_name": "",
            "version_name": "",
            "game_directory": "",
            "assets_root": "",
            "assets_index_name": "",
            "auth_uuid": "",
            "auth_access_token": "",
            "clientid": "",
            "auth_xuid": "",
            "user_type": "",
            "version_type": "",
            "natives_directory":"",
            "classpath": "",
            "library_directory": "",
            "launchder_name": "",
            "launchder_version": "",
            "resolution_width":"",
            "rsolution_height": "",
            "quickPlayPath": "",
            "quickPlaySingleplayer": "",
            "quickPlayMultiplayer": "",
            "quickPlayRealms": ""
        }

    def run(self):
        # TODO: 补全文件功能
        # 从数据库中获取实例    
        instance = Instances.get_or_none(Instances.name == self.instance_name)


        if instance is None:
            raise TaskError(State.VERSION_NOT_FOUND)

        version_info = instance.version


        game_dir = paths.gamedata / instance.name
        game_dir.mkdir(parents=True, exist_ok=True)


        (game_dir / 'natives').mkdir(parents=True, exist_ok=True)
        native_libraries = list(LibrariesReference.select()
            .join(MCLibraries)
            .where(MCLibraries.is_native == True)
            .where(LibrariesReference.instance == instance)
        )


        for native_library in native_libraries:

            lib_path = paths.data / native_library.library_file.path
            
            for child in lib_path.iterdir():
                print(child)
                (game_dir / "natives").hardlink_to(child)


        self.formatter["version_name"] = version_info.version
        self.formatter["game_directory"] = str(game_dir)
        self.formatter["assets_root"] = str(paths.assets)
        self.formatter["assets_index_name"] = version_info.assets.id
        
        # TODO: 取真实的Authuuid
        self.formatter["auth_uuid"] = hashlib.md5("fuck".encode()).hexdigest()
        self.formatter["auth_access_token"] = hashlib.md5("fuck".encode()).hexdigest()
        self.formatter["clientid"] = "rnadom"
        self.formatter["auth_xuid"] = "rnadom"

        self.formatter["user_type"] = "legacy"

        self.formatter["version_type"] = version_info.type

        # region 参数解析
        arguments_info = MCArguments.get(version_id=instance.version)
        args_rules = rule.validate_python(arguments_info.jvm) +rule.validate_python(arguments_info.game)

        arguments: list[str] = []

        for arg_rule in args_rules:
            args: list[str] = []
            if isinstance(arg_rule, str):
                args.append(arg_rule)

            else:
                if match_rules(arg_rule.rules, self.features):
                    args.extend(arg_rule.value if isinstance(arg_rule.value, list) else [arg_rule.value])
                else:
                    continue

            for arg in args:
                arguments.append(substitute(arg, self.formatter))

            # arguments.extend(args)
            

        # endregion
        

        print(arguments)





if __name__ == "__main__":
    import sys
    launch_task = LaunchTask(sys.argv[1])

    launch_task.run()
        

        



        
        

        




