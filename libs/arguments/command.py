from typing import TypeVar, Generic


T_ = TypeVar("T_")

MISSING = sentinel("MISSING")

class Argument(Generic[T_]):

    def __init__(self, *name: str, type_: type[T_], default: T_ = MISSING, help: str = ""):
        self.names = name
        self.type = type_
        self.default = default 

        self.help = help

        self.value : T_ | MISSING = MISSING

    def set_value(self, value: T_ | MISSING):
        if value is not MISSING:
            self.value = value
        else:
            self.value = self.default

    def get_value(self):
        if self.value is MISSING:
            raise ValueError("未赋值")
        
        return self.value

    
class Arguments(Generic[T_]):

    @classmethod
    def field(cls, *name: str, type: type[T_], default: T_ = None, help: str = ""):
        return Argument(*name, type_=type, default=default, help=help)

    @classmethod
    def get_arguments(cls):
        arguments = []
        for obj in dir(cls):
            if isinstance(obj, Argument):
                arguments.append(obj)

        return arguments

T = TypeVar("T", bound=Argument)

class Command(Generic[T]):
    __command_name__: str
    __help__: str
    __description__: str
    __args__: type[T] | None = None
    __sub_commands__: list[Command] = []

    def __init__(self, args: T | None):
        pass

