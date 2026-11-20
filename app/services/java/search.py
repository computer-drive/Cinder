import os
import shutil
from dataclasses import dataclass
from pathlib import Path
lazy import winreg
from enum import Enum, auto
import subprocess
from concurrent.futures import ThreadPoolExecutor, Future

from ..base import Task, StepUpdate, StepFinished, TaskError
from ...logging import get_logger
from ...database.model import Java
from ...database import use_database
from ...database.model import Java
from ...paths import paths

# region 一些常量
LINUX_JAVA_PATH = [
    Path("/usr/java"),
    Path("/usr/lib/jvm"),
    Path("/usr/lib32/jvm"),
    Path("/usr/lib64/jvm"),
    Path("~/.sdkman/candidates/java"),
    Path("~/.jdks"),
]

WIN_REGISTRY_KEYS = [
    r"SOFTWARE\JavaSoft\Java Runtime Environment",
    r"SOFTWARE\JavaSoft\Java Development Kit",
    r"SOFTWARE\JavaSoft\JRE",
    r"SOFTWARE\JavaSoft\JDK",
]

VENDORS = ["Java", "BellSoft", "AdoptOpenJDK", "Zulu",
           "Microsoft", "Eclipse Foundation", "Semeru"]

MAC_JAVA_PATH = [
    Path("/Library/Java/JavaVirtualMachines"),
    Path("~/Library/Java/JavaVirtualMachines"),
    Path("/Library/Internet Plug-Ins/JavaAppletPlugin.plugin/Contents/Home/bin/java"),
    Path("/opt/homebrew/opt/java/bin/java"),
    Path("/opt/homebrew/Cellar/openjdk"),


]
#endregion




class SearchJava(Task[None]):

    class State(Enum):
        UNSUPPORTED_PLATFORM = auto()
    
    def __init__(self):
        self.java_list: list[Path] = []

        self.logger = get_logger()

        self.database = use_database()

    def search_java(self):
        #region 1、JAVA_HOME环境变量
        java_home = os.environ.get("JAVA_HOME", "")

        if java_home:
            java_bin_path = Path(java_home) / "bin"
            java_exec_path = java_bin_path / ("java.exe" if os.name == "nt" else "java")

            if java_bin_path.exists() and java_exec_path.exists() and java_exec_path.is_file():

                self.logger.info(f"找到可能的Java运行时：{java_bin_path}")

                # 添加bin目录
                self.java_list.append(java_bin_path)
        #endregion
        

        #region 2、PATH环境变量
        java_path = shutil.which("java")
        if java_path:
            path = Path(java_path)
            if path.exists() and path.is_file():
                self.logger.info(f"找到可能的Java运行时：{path.parent}")
                # 添加bin目录
                self.java_list.append(path.parent)
        #endregion

        #region 3、根据系统分别查找
        if os.name == "posix":
            # linux 系统
            for path in LINUX_JAVA_PATH:
                bin_path = path / "bin"
                java_path = bin_path / "java"
                if java_path.exists() and java_path.is_file():
                    self.logger.info(f"找到可能的Java运行时：{java_path}")
                    # 添加bin目录
                    self.java_list.append(bin_path)

        elif os.name == "nt":
            # windows 系统
            
            # 先查找注册表
            for key in WIN_REGISTRY_KEYS:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as sub_key:
                        

                        # 枚举子键
                        i = 0
                        while True:
                            # 获取子键名称
                            try:
                                version = winreg.EnumKey(sub_key, i)
                            except OSError:
                                # 枚举完了
                                break
                            
                            i += 1
                            

                            try: 
                                java_home, _ = winreg.QueryValueEx(sub_key, version + r"\JavaHome")
                            except FileNotFoundError:
                                continue
                            else:
                                bin_path = Path(java_home) / "bin"
                                java_exec_path = bin_path / "java.exe"

                                if bin_path.exists() and java_exec_path.exists() and java_exec_path.is_file():
                                    self.java_list.append(JRE(bin_path))

                                    self.logger.info(f"找到可能的Java运行时：{bin_path}")

                except FileNotFoundError:
                    continue
            
            # 遍历Programs Files下的目录
            program_files = os.environ.get("ProgramFiles", r"C:\Program Files", ) # 从环境变量取，默认C:\Program Files
            program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)", ) # 从环境变量取，默认C:\Program Files (x86)

            for program_file in [program_files, program_files_x86]:
                
                for vendor in VENDORS:
                    bin_path = Path(program_file) / vendor / "bin"
                    java_exec_path = bin_path / "java.exe"

                    if java_exec_path.exists() and java_exec_path.is_file():
                        self.java_list.append(bin_path)
                        self.logger.info(f"找到可能的Java运行时：{bin_path}")
                        

        elif os.name == "mac":
            # mac 系统

            for path in MAC_JAVA_PATH:
                java_path = path / "bin" / "java"
                if java_path.exists() and java_path.is_file():
                    self.java_list.append(path)
                    self.logger.info(f"找到可能的Java运行时：{java_path}")


        else:
            raise TaskError(self.State.UNSUPPORTED_PLATFORM)

        #endregion


    def _validate_java_task(self, java_exec_path: Path):

        try:
            result = subprocess.run(
                [java_exec_path, "-XshowSettings:properties","-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
        except subprocess.TimeoutExpired:
            self.logger.error(f"{java_exec_path} 验证失败，运行超时。")
            return (False, "")

        else:
            if result.returncode != 0:
                self.logger.error(f"{java_exec_path} 验证失败，程序异常退出：{result.returncode}。")
                return (False, result.stderr)
            else:
                return (True, result.stderr)




    def validate_java(self):
        result: dict[Path, tuple[bool, str]] = {}

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures: dict[Path, Future[tuple[bool, str]]] = {}

            for path in self.java_list:
                java_exec_path = (path / ("java.exe" if os.name == "nt" else "java")).resolve()


                futures[java_exec_path] = executor.submit(self._validate_java_task, java_exec_path)

            for java_exec_path, future in futures.items():
                result[java_exec_path] = future.result()



            self.logger.info("所有Java运行时都运行完了。")
            return result

    
        
    def run(self) -> list[Java]:
        '''运行任务'''

        self.logger.info("正在搜索Java运行时...")
        
        self.search_java()

        self.logger.info("正在通过运行验证Java运行时...")

        result = self.validate_java()

        new_java_list: list[Java] = []

        for path, (success, output) in result.items():

            if success:
                output_items = output.split("\n")

                if "Property settings" in output_items[0]:
                    output_items.pop(0)  # 移除第一条信息
                else:
                    self.logger.error(f"{path} 验证失败，输出中没有Property settings头。")
                    continue


                properties: dict[str, list[str]] = {}
                last_key: str | None = None

                for item in output_items:
                    item = item.strip()

                    if "=" in item:
                        key, value =[item.strip() for item in item.split("=", 2)]
                        properties[key] = [value]

                        last_key = key
                    elif item.strip() != "":
                        if last_key is not None:
                            properties[last_key].append(item.strip())
                        else:
                            self.logger.error(f"{path} 验证失败，解析到无键值对的行：{item}")
                            continue
                    
                    else:
                        break


                for key in  ("java.vendor", "java.specification.version", "java.version"):
                    if key not in properties.keys():
                        self.logger.error(f"{path} 验证失败，缺少属性：{key}。")


                else:
                    self.logger.info(f"{path} 有效！")


                if Java.get_or_none(Java.path == str(path)) is not None:
                    self.logger.info(f"{path} 在数据库中已存在，跳过。")
                    continue

                
                with self.database.atomic():
                    java = Java.create(
                        path=str(path),
                        major_version=int(properties["java.specification.version"][0]),
                        version=properties["java.version"][0],
                        vendor=properties["java.vendor"][0],
                    )

                    new_java_list.append(java)

                self.logger.info(f"发现了新的Java运行时：{path}。")


            else:
                self.logger.error(f"{path} 验证失败，Java主程序错误退出了：{output}")

        return new_java_list

            

            

                        

                        


       




    
