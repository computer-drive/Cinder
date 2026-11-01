from core.terminal.startup import startup
from core.arguments import Parser

lazy from app.commands import parsers

# 启动渲染
console = startup()

parser = Parser(help="Cinder命令行")

parser.register(*parsers)

if __name__ == "__main__":
    parser.run()

    console.stop()