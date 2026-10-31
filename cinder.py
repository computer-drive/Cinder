from core.terminal.startup import startup
import time

console = startup()

spinner = console.spinner("下载文件...（建立连接）")


for i in range(10):
    console.println(f"连接重试：{i}")
    time.sleep(0.1)


spinner.loading1("下载文件...（下载中）")

time.sleep(1)

# spinner.loading2("下载文件...（下载中）")

time.sleep(1)

spinner.finish("下载文件...（下载完成）")


# console.stop()