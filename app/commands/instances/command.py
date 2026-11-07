lazy from requests.exceptions import RequestException

from core.arguments import Parser
from core.terminal.console import Console

from ...services.base import TaskError
from ...services.instances import InstancesService

instances = Parser("instances", "管理 Minecraft 实例")

@instances.command("fetch-versions", "获取 Minecraft 版本清单")
def fetch_versions():
    console = Console.get_instance()

    spinner = console.spinner("正在获取 Minecraft 版本清单...")
    spinner.loading1()

    task = InstancesService().fetch_versions()

    gen = task.run()

    try:
        while True:
            event = next(gen)

            spinner.set_text("正在分析 Minecraft 版本清单数据...")

    except StopIteration as e:
        console.println(f"发现并更新了 {e.value["new_versions_count"]} 个新的 Minecraft 版本。({e.value["time_taken"]:.2f} 秒)")

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

