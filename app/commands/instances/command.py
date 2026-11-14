from typing import Annotated

lazy from requests.exceptions import RequestException

from core.arguments import Parser, Argument
from core.terminal.console import Console

from ...services.base import TaskError, StepUpdate
from ...services.instances.instances import InstancesService

instances = Parser("instances", "管理 Minecraft 实例")

@instances.command("get::update", "更新 Minecraft 版本索引")
def update_versions_index():
    console = Console.get_instance()

    console.title("更新 Minecraft 版本索引")

    spinner = console.spinner("正在获取数据...")
    spinner.loading1()

    task = InstancesService().update_versions_index()

    gen = task.run()

    try:
        while True:
            event = next(gen)

            console.println(f"成功获取版本清单数据。（{event.data['time_taken']:.2f} 秒）")

            spinner.set_text("正在分析数据...")

    except StopIteration as e:
        if e.value["new_versions_count"] == 0:
            console.println("没有发现新的 Minecraft 版本。")
        
        else:
            console.println(f"发现并更新了 {e.value["new_versions_count"]} 个新的 Minecraft 版本。（{e.value["time_taken"]:.2f} 秒）")

        spinner.finish("更新成功。")

    except RequestException as e:
        console.error(f"网络错误。{e}")  

        spinner.error("更新失败。")

    except KeyboardInterrupt:
        spinner.error("用户取消了操作。")

    except TaskError as e:
        console.error(f"更新失败，{e}")

        spinner.error("更新失败。")

    finally:
        gen.close()

@instances.command("get::fetch-manifest", "获取一个 Minecraft 版本的清单数据")
def fetch_version_manifest(
    version: Annotated[str, Argument("-v", "--version", help="要获取的版本")]
):
    console = Console.get_instance()

    spinner = console.spinner(f"正在获取版本清单数据...")
    spinner.loading1()

    task = InstancesService().fetch_version_manifest(version)
    gen = task.run()

    is_fetched = False

    try:
        while True:
            event = next(gen)

            if isinstance(event, StepUpdate):
                if event.step == "version_data_already_fetched":
                    console.println(f"版本 {version} 的数据已经获取过了。")
                    is_fetched = True

    except StopIteration as e:
        if not is_fetched:
            console.println(f"成功获取版本 {version} 的数据。")

        spinner.finish("获取成功。")

    except KeyboardInterrupt:
        spinner.error("用户取消了操作。")

    except TaskError as e:
        if e.message == "version_not_found":
            console.error(f"版本 {version} 不存在。")
            console.println("若你确定版本存在，请先运行 instances:update 命令。")

        spinner.error("获取失败。")

    except RequestException as e:
        console.error(f"网络错误。{e}")  

        spinner.error("获取失败")

@instances.command("test")
def test():
    from ...database.model import MCVersions
    from ...database import use_database

    db = use_database(MCVersions)

    versions = [v.version for v in MCVersions.select()]

    for v in versions:
        fetch_version_manifest(v)
        



