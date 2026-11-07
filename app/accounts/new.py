from typing import Literal

lazy from requests.exceptions import RequestException

from core.terminal.console import Console
from core.terminal.control import Fore, Style

from ..services.accounts import AccountsSerivce
from ..services.base import StepFinished, StepUpdate



from .schema import *
from .command import accounts



@accounts.command("new", "添加一个 Minecraft 账户")
def add_account():
    console = Console.get_instance()

    # console.title("添加 Minecraft 账户")

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

                        console.println(f"请在打开的浏览器窗口中输入：{Style.bold}{Style.underline()}{event.data["user_code"]}{Style.reset}。登录 Microsoft 账户。")
                        console.println(f"没有找到浏览器窗口？点击链接：{Style.link("登录 Microsoft 账户", event.data["verification_uri"])}")

                        step_name = "等待登录..."

                        spinner.loading0(f"{step_name}（步骤{step}）")

                    case "error":

                        console.error(f"{event.data["message"]}")

                        if event.data["data"] :
                            console.error(f"详细信息：{event.data["data"]}")

                        spinner.error("登录失败。")

                        break

                    case "getting_xbox":

                        console.println("已登录到 Microsoft 账户。")

                        step_name = "正在登录到 Xbox..."
                        
                        spinner.loading1(f"{step_name}（步骤{step}）")

                    case "getting_xsts":
                        step_name = "正在登录到 Xbox Live..."

                        spinner.loading1(f"{step_name}（步骤{step}）")

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
            
            elif isinstance(event, StepUpdate):
                console.println(event.data["message"])

    except StopIteration as e:
        console.println(f"登录成功。当前的账户名称为：{e.value}")

    except RequestException as e:
        console.error(f"网络错误：{e}")

        spinner.error("登录失败。")

    except KeyboardInterrupt:
        spinner.error("用户取消了登录。")

    finally:
        
        gen.close()
        



        










    