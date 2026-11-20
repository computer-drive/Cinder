from typing import Literal, Annotated

lazy from requests.exceptions import RequestException
import pyperclip
from pydantic import ValidationError

from core.terminal.console import Console
from core.terminal.control import Fore, Style
from core.arguments.argument import Argument

from ...config import use_config
from ...services.accounts import AccountsSerivce
from ...services.base import StepFinished, StepUpdate, TaskError

from .command import accounts



@accounts.command("new", "添加一个 Minecraft 账户")
def add_account(
    login_type: Annotated[str, Argument("--type", "-t", optional=(True, "online"))]
):
    console = Console.get_instance()

    config = use_config()

    
    if login_type == "offline":
        if config.accounts.allow_offline_account:
            console.warning(
                "离线用户无法进入开启正版验证的服务器，无法使用披风等功能。如果你喜欢 Minecraft，推荐你购买正版。"
            ,prefix=False)
            console.println(f"{Style.link("购买 Minecraft↗", "https://www.minecraft.net/choose-your-game")} {Style.link("Minecraft 官网↗", "https://www.minecraft.net/")}")

            task = AccountsSerivce().new_offline()

            gen = task.run()

            try:
                while True:
                    event = next(gen)

                    if isinstance(event, StepFinished):
                        if event.step == "input_username":
                            task.username = console.input("请输入玩家名（显示在Minecraft中）：")
                            
                        elif event.step == "input_cinder_name":
                            task.cinder_name = console.input("请输入账户名（显示在Cinder中）：")

                    elif isinstance(event, StepUpdate):
                        if event.step == "account_name_error":
                            console.error("账户名已存在，请选择其他账户名。")

            except StopIteration:
                console.println(f"离线账户 {task.cinder_name} 已添加。")
            
            finally:
                gen.close()

            return

        else:
            console.error("不允许你添加离线账户。")
            return 

            

    step = 1
    step_name = "正在准备..."
    spinner = console.spinner(f"{step_name}（步骤{step}）")
    spinner.loading1()

    task = AccountsSerivce().new()

    gen = task.run()

    try:
        while True:
            event = next(gen)

            if isinstance(event, StepFinished):
                step += 1
                
                match event.step:
                    case "wait_login":
                        try:
                            pyperclip.copy(event.data["user_code"])
                        except pyperclip.PyperclipException as e:
                            console.error(f"复制到剪切板失败：{e}")


                        console.println(f"请在打开的浏览器窗口中输入：{Style.bold}{Style.underline()}{event.data["user_code"]}{Style.reset}（已复制到剪切板），然后登录 Microsoft 账户。")
                        console.println(f"没有找到浏览器窗口？点击链接：{Style.link("登录 Microsoft 账户", event.data["verification_uri"])}\n")

                        step_name = "等待登录..."

                        spinner.loading0(f"{step_name}（步骤{step}）")


                    case "getting_mc_token":
                        step_name = "正在登录到 Minecraft..."
                        
                        spinner.loading1(f"{step_name}（步骤{step}）")

                    case "getting_profile":
                        step_name = "正在获取玩家数据..."
                                            
                        spinner.loading1(f"{step_name}（步骤{step}）")

                    case "unbought_game":
                        console.error("登录失败，这个 Microsoft 账户可能尚未购买 Minecraft。如果你使用了 Xbox Game Pass，请先前往 Minecraft 官网创建一次个人档案")
                        console.println(f"{Style.link("购买 Minecraft↗", "https://www.minecraft.net/choose-your-game")} {Style.link("Minecraft 官网↗", "https://www.minecraft.net/")}")

                        spinner.error("登录失败")

                        break

                    case "input_account_name":
                        account_name = console.input("请输入账户的名称（用于显示在 Cinder 中）：", lambda x: x.strip() != "")

                        task.cinder_name = account_name

                    case "login_success":
                        spinner.finish("登录成功。").wait()

            elif isinstance(event, StepUpdate):
                match event.step:

                    case "username":
                        console.success(f"已登录到 Minecraft。玩家名为 {event.data["username"]}", False)

                    case "account_name_error":
                        console.error("账号名已存在。")
                    

    except StopIteration as e:
        console.println(f"账户 {e.value["account_name"]} 已添加。")

    except RequestException as e:
        console.error(f"网络错误：{e}")

        spinner.error("登录失败。")
        
    except ValidationError as e:
        console.error(f"登录信息获取失败。{e}")
        
        spinner.error("登录失败。")
    except KeyboardInterrupt:
        spinner.error("用户取消了登录。")

    except TaskError as e:
        spinner.error("登录失败。")

        console.error(e.message)
        if e.data is not None:
            console.error(str(e.data))

    finally:
        
        gen.close()
        


@accounts.command("refresh", "刷新账户令牌")
def refresh_account(
    account_name: Annotated[str, Argument("--account", "-a")]
):

    console = Console.get_instance()

    task = AccountsSerivce().refresh(account_name)

    gen = task.run()

    spinner = console.spinner("正在刷新令牌...")

    try:
        while True:
            event = next(gen)

    except TaskError as e:
        if e.message == task.State.TOKEN_EXPIRED:
            console.error("所有令牌均已过期，当前账户已被删除。若想使用，请重新登录。")

        elif e.message == task.State.XBOX_ERROR:
            console.error(f"刷新失败，Xbox 账户错误。详细信息：{e.data}")

        elif e.message == task.State.ACCOUNT_NOT_FOUND:
            console.error(f"账户 {account_name} 不存在。")
        
        elif e.message == task.State.OFFLINE_ACCOUNT:
            console.warning("无须刷新离线账户的令牌。")

    except KeyboardInterrupt:
        console.error("用户取消了刷新。")

    except StopIteration as e:
        if e.value:
            console.success(f"账户 {account_name} 已刷新。")
        else:
            console.warning(f"账户 {account_name} 的令牌均有效。")

    except RequestException as e:
        console.error(f"网络错误：{e}")

    except ValidationError as e:
        console.error(f"刷新失败，登录信息获取失败。{e}")

    finally:
        spinner.stop()
        gen.close()




