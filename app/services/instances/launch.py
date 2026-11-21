from enum import Enum, auto
from pathlib import Path
from typing import cast
import os
import subprocess

from pydantic import TypeAdapter, BaseModel

from ..base import Task, StepFinished, StepUpdate, TaskError
from ...database import use_database
from ...database.model import LibrariesReference, MCLibraries, MCVersions, Instances, MCArguments
from .schema import Rule, match_rules
from ...paths import paths
from core.utils.format import substitute
from ...logging import get_logger

from ..accounts import RefreshAccount

class State(Enum):
    VERSION_NOT_FOUND = auto()
    JAVA_VERSION_UNSET = auto()
    ACCOUNT_UNSET = auto()

    REFRESH_ACCOUNT_FAILED = auto()


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
            "is_demo_user": False,
            "has_custom_resolution": False,
            "has_custom_resolution": False,
            "is_quick_play_singleplayer": False,
            "is_quick_play_multiplayer":  False,
            "is_quick_play_realms": False
        }

        self.formatter:dict[str, str] ={
            "auth_player_name": None,
            "version_name": None,
            "game_directory": None,
            "assets_root": None,
            "assets_index_name": None,
            "auth_uuid": None,
            "auth_access_token": None,
            "clientid": None,
            "auth_xuid": None,
            "user_type": None,
            "version_type": None,
            "natives_directory":None,
            "classpath": None,
            "library_directory": None,
            "launcher_name": None,
            "launcher_version": None,
            "resolution_width":None,
            "resolution_height": None,
            "quickPlayPath": None,
            "quickPlaySingleplayer": None,
            "quickPlayMultiplayer": None,
            "quickPlayRealms": None
        }

    def run(self):
        # TODO: 补全文件功能

        logger = get_logger()

        # 从数据库中获取实例    
        instance = Instances.get_or_none(Instances.name == self.instance_name)


        if instance is None:
            logger.error(f"实例 {self.instance_name} 不存在")
            raise TaskError[State](State.VERSION_NOT_FOUND)

        if instance.default_java is None:
            logger.error(f"实例 {self.instance_name} 没有设置默认的Java版本")
            raise TaskError[State](State.JAVA_VERSION_UNSET)

        if instance.default_account is None:
            logger.error(f"实例 {self.instance_name} 没有设置默认的账户")
            raise TaskError[State](State.ACCOUNT_UNSET)

        logger.info("正在刷新账户...")
        # 刷新账户
        try:

            _,  account = RefreshAccount(instance.default_account.id).run_complete()
            
        except TaskError as e:
            match e.message:
                case RefreshAccount.State.OFFLINE_ACCOUNT:
                    # 离线账户，不刷新也行
                    pass
                case RefreshAccount.State.TOKEN_EXPIRED:
                    logger.error(f"账户 {instance.default_account.name} 的令牌过期了，无法刷新。")
                    logger.error(f"未能启动实例。")
                    
                    raise TaskError[State](State.REFRESH_ACCOUNT_FAILED)

                case _:
                    logger.error(f"未知错误：{e.message}")

                    raise TaskError[State](State.REFRESH_ACCOUNT_FAILED)
        
        except Exception as e:
            raise e from None



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

                (game_dir / "natives").hardlink_to(child)

        self.formatter["launcher_name"] = "Cinder"
        self.formatter["launcher_version"] = "1.0.0"


        self.formatter["version_name"] = version_info.version
        self.formatter["game_directory"] = str(game_dir)
        self.formatter["assets_root"] = str(paths.assets)
        self.formatter["assets_index_name"] = version_info.assets.id

        

        # TODO: 根据离线账户和在线账户设置参数
        self.formatter["auth_uuid"] = account.uuid
        self.formatter["auth_player_name"] = account.name
        self.formatter["auth_access_token"] = account.mc_access_token 
        self.formatter["clientid"] = "?" # TODO: 用app_id
        self.formatter["auth_xuid"] = "?" # TODO: 以后加
        self.formatter["user_type"] = "online" # TODO: 我也不知道填啥，以后弄



        self.formatter["version_type"] = version_info.type
        self.formatter["natives_directory"] = "natives"

        # 查询所有libraries
        library_files: list[str] = []

        for library in (LibrariesReference().
            select().
            join(MCLibraries).
            where(
            LibrariesReference.instance == instance,
            MCLibraries.is_native == False)
            .order_by(
                MCLibraries.order
            )
        ):
            library_files.append(
                os.path.relpath(paths.data / library.library_file.path, game_dir)
            )
        
        library_files.append(
            os.path.relpath(paths.data / instance.client_file.path, game_dir)
        )


        self.formatter["classpath"] = (";" if os.name == "nt" else ":").join(library_files)
        

        self.formatter["XMainClass"] = cast(str, version_info.main_class)

        # 日志的path
        self.formatter["path"] = os.path.relpath(instance.logging_config.path, game_dir)

        # region 参数解析
        arguments_info = MCArguments.get(version_id=instance.version)
        args_rules = rule.validate_python(arguments_info.jvm) + [r"${XMainClass}", cast(str, version_info.logging_argument)] + rule.validate_python(arguments_info.game)

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

            
        # endregion
    


        argv = [instance.default_java.path] +  arguments

         # !去除敏感信息再记录日志
        show_argv = argv.copy()
        show_argv[argv.index(account.mc_access_token)] = "(敏感信息已隐藏)"

        logger.info(f"实例启动的命令行：{ ' '.join(show_argv)}")


        yield StepUpdate("test_argument", {
            "arguments": str(show_argv)
        })
        
        process = subprocess.Popen(
            argv,
            cwd=game_dir,
            env=os.environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            # start_new_session=True,  
        )

        

        for line in process.stdout:
            print(line, end="")






if __name__ == "__main__":
    import sys
    launch_task = LaunchTask(sys.argv[1])

    launch_task.run()
        

        



        
        

        




