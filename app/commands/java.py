from libs.arguments import Arguments, Command

class JavaCommand(Command):
    __name__ = "java"
    __help__ = "管理Java运行时"

    class __new_command__(Command):
        __name__ = "discover"
        __help__ = "查找Java运行时"

        class __args__(Arguments):
            deeply = Arguments.field("--deeply", "-d", type=bool, 
                help="是否开启深度查找。当此项为true时，将递归查询整个磁盘；当此项为false时，仅查找常用目录。")


        def __init__(self, args: __args__):
            print(args.deeply.value)




