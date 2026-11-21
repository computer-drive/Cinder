from typing import Annotated, cast, Any
from threading import Event

lazy from requests.exceptions import RequestException

from core.arguments import Parser, Argument
from core.terminal.console import Console
from core.terminal.elements.live import DownloadProgress, Progress
from core.utils.format import format_size

from ...services.base import TaskError, StepUpdate, StepFinished
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

    spinner = console.spinner(f"正在获取 {version} 的清单数据...")
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
                elif event.step == "fetch_manifest.cache":
                    console.success("成功获取清单数据（命中缓存）。")
                elif event.step == "fetch_manifest.network":
                    console.success("成功获取清单数据。")
                elif event.step == "libraries.unused":
                    console.warning(f"库 {event.data['library_name']} 未被使用。")

            else:
                if event.step == "analyze_manifest":
                    spinner.set_text("正在分析数据...")

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
        elif e.message == "native_library.platform_not_supported":
            e.data = cast(dict[str, Any], e.data)

            console.error(f"本地（Native）库 {e.data['library_name']} 在当前平台上不可用（支持的平台：{"，".join(e.data['supported_platforms'])}）")

        elif e.message == "unknown_manifest_type":
            console.error(f"解析清单数据失败。{e.data["message"] if e.data else '未知错误'}")


        spinner.error("获取失败。")

    except RequestException as e:
        console.error(f"网络错误。{e}")  

        spinner.error("获取失败")


@instances.command("install", "安装一个 Minecraft 实例")
def install_instance(
    version: Annotated[str, Argument("-v", "--version", help="要安装的版本")],
    update: Annotated[bool, Argument("-u", "--update", help="是否先更新版本索引", optional=(True, False))]
):

    console = Console.get_instance()

    service = InstancesService()

    spinner = console.spinner(f"正在准备安装 {version}...")
    spinner.loading1()

    stop_event = Event()


    if update:
        service.update_versions_index().run_complete()

        service.fetch_version_manifest(version).run_complete()


    task = service.install_instance(version, stop_event)
    gen = task.run()

    download_progress = DownloadProgress(console.output_queue, 0, 0, "下载文件")

    buildref_progress = Progress(console.output_queue, 0, 0, "构建引用")

    extract_progress = Progress(console.output_queue, 0, 0, "提取本地（Natives）库")

    try:
        while True:
            event = next(gen)

            if isinstance(event, StepFinished):
                if event.step == "downloading":
                    spinner.finish("准备完成。")

                    if not console.confirm(f"将会下载 {event.data["count"]} 个文件，共 {format_size(event.data['total_size'])} ，是否继续？"):
                        break
                    
                    download_progress.set_total(event.data["total_size"])
                    console.put(download_progress)

                elif event.step == "canceling":
                    download_progress.stop()
    
                    console.error("用户取消了下载操作，正在执行清理操作...")
    
                    continue
            
                elif event.step == "canceled":
                    console.println("清理完成。")
                    console.warning("已下载的文件未被删除。若想清理这些文件请运行self gc；若想继续安装 Minecraft 请重新运行此命令。")

                    break

                elif event.step == "input_instance_name":
                    task.instance_name = console.input("请输入实例名称：", lambda x: x.strip() != "")

                elif event.step == "instance_name_exists":
                    console.println(f"实例名称 {task.instance_name} 已存在。")

                    

                elif event.step == "building_references":

                    buildref_progress.set_total(event.data["total"])
                    console.put(buildref_progress)

                elif event.step == "download_aleady_finished":

                    download_progress.stop()


                    console.println("需要的文件已经下载过了。")

                elif event.step == "download_all_finished":

                    download_progress.stop()

                elif event.step == "extracting_natives":
                    console.println("正在提取本地（Natives）库...")

                    buildref_progress.stop()

                    extract_progress.set_total(event.data["count"])
                    console.put(extract_progress)


                

            else:
                if event.step == "download_progress":
                    if event.data["type"] == "progress":
                        download_progress.add_progress(event.data["data"]["new_size"])

                    

                    elif event.data["type"] == "download_error":
                        # print(event.data["data"])
                        console.error(f"下载失败 {event.data["id"]}：{event.data["data"]["message"]}", prefix=False)

                elif event.step == "file_finished":
                    console.println(f"下载成功 {event.data["id"]}：{event.data["name"]}")

                elif event.step == "has_error":
                    console.warning(f"共有 {event.data["count"]} 个文件未能下载。")
                    console.warning("已下载的文件未被删除。若想清理这些文件请运行self gc；若想继续安装 Minecraft 请重新运行此命令。")
                    
                elif event.step == "building_progress":
                    buildref_progress.set_progress(event.data["finished"])

                elif event.step == "extracting_progress":
                    extract_progress.set_progress(event.data["finished"])

                elif event.step == "building_references_finished":
                    buildref_progress.stop()

                elif event.step == "extracting_natives_finished":
                    extract_progress.stop()
                    
                                       
    except StopIteration as e:
        if e.value:
            buildref_progress.stop()
            
            console.println(f"成功安装版本 {version}。")

        

    except TaskError as e:
        if e.message == task.State.VERSION_NOT_FOUND.value:
            console.error(f"版本 {version} 不存在。")
            console.println("若你确定版本存在，请先运行 instances:update 命令。")

        elif e.message == task.State.VERSION_UNFETCHED.value:
            console.error(f"版本 {version}（{task.instance_name}）的数据未获取过。")

        else:
            print(e.message)


    finally:
        gen.close()

@instances.command("launch", "启动实例")
def launch_instance(
    instance_name: Annotated[str, Argument("-n", "--name", help="实例名称")],
):

    console = Console.get_instance()


    task = InstancesService().launch_instance(instance_name)

    gen = task.run()

    try:
        while True:
            event = next(gen)


    except TaskError as e:
        
        match e.message:
            case task.State.VERSION_NOT_FOUND:
                console.error(f"版本 {instance_name} 不存在。")

            case task.State.JAVA_VERSION_UNSET:
                console.error("Java运行时未设置。请使用 instances set-java 设置Java运行时。")

            case task.State.ACCOUNT_UNSET:
                console.error("账号未设置。请使用 instances set-account 设置账号。")

    except StopIteration as e:
        print(e.value)
         




        
        



