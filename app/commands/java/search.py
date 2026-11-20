from .command import java

from ...services.java.search import SearchJava
from core.terminal.console import Console

@java.command("search", "搜索 Java 运行时环境")
def search_java():
    console = Console.get_instance()

    spinner = console.spinner("正在搜索Java运行时...")

    new_java_list = SearchJava().run()

    spinner.stop()

    if new_java_list:
        console.success(f"搜索到新的 {len(new_java_list)} 个Java运行时。")

        for java in new_java_list:
            console.println(f"{java.path} {java.vendor} {java.version}")
    
    else:
        console.println("未搜索到新的Java运行时。")



    
    

