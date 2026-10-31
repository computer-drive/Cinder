import os
from typing import TypeVar, Generic

class File:
    __filename__ = ""

    def __init__(self, path: Directory, name: str, create: bool = True):
        self.path = path
        self.name = name

        self._path_string = os.path.join(self.path._path_string, self.name)

        if not os.path.exists(self._path_string):
            if create:
                self.create()
            else:
                raise FileNotFoundError(f"文件 {self._path_string} 不存在")
            
        elif not os.path.isfile(self._path_string):
            raise FileNotFoundError(f"路径 {self._path_string} 不是文件")

    def create(self):
        '''创建文件'''
        os.makedirs(os.path.dirname(self._path_string), exist_ok=True)

        os.open(self._path_string, os.O_CREAT | os.O_WRONLY, 0o644)

    def open_text(self, mode: str = "r", encoding: str = "utf-8"):
        '''打开文本文件'''
        return open(self._path_string, mode, encoding=encoding)

    def open_binary(self, mode: str = "rb"):
        '''打开二进制文件'''
        return open(self._path_string, mode)


T = TypeVar("T", bound="Directory")

class Directory(Generic[T]):
    __dirname__ = ""
     
    def __init__(self, path: list[str], create_all: bool = True):
        self.path = path

        self._path_string = os.path.abspath(os.path.join(*(self.path)))

        if not os.path.exists(self._path_string):
            if create_all:
                self.create()
            else:
                raise FileNotFoundError(f"目录 {self._path_string} 不存在")
        elif not os.path.isdir(self._path_string):
            raise FileNotFoundError(f"路径 {self._path_string} 不是目录")

    @classmethod
    def render(cls: type[T], base_dir: Directory, create_all: bool = True) -> T:
        '''渲染目录树'''

        if create_all:
            base_dir.create()

        if cls.__dirname__ == "":
            raise ValueError(f"目录 {cls.__name__} 未指定目录名")

        print(cls.__annotations__)
        subs = {name: sub for name, sub in cls.__annotations__.items() if isinstance(sub, (type(Directory), type(File)))}

        directory: T = cls([*base_dir.path, cls.__dirname__], create_all)

        for name, sub in subs.items():
            print(name)
            if isinstance(sub, type(Directory)):
                setattr(directory, name, sub.render(directory, create_all))
                
            elif isinstance(sub, type(File)):
                setattr(directory, name, directory.get_file(sub.__filename__, create_all))

        return directory

        
    def create(self):
        '''创建目录'''
        os.makedirs(os.path.join(*(self.path)), exist_ok=True)

    def list(self):
        '''列出目录下的文件'''
        return os.listdir(self._path_string)

    def get_file(self, name: str, create: bool = True):
        '''获取文件'''
        return File(self, name, create)

    def get_directory(self, name: str, create: bool = True):
        '''获取子目录'''
        return Directory([*self.path, name], create)

    def get_top(self):
        '''获取根目录'''
        return Directory(self.path[:-1])

    



if __name__ == "__main__":

    class UserData(Directory):
        __dirname__ = "user"

        class Config(File):
            __filename__ = "config.json"

        config: Config


    user_data: UserData = UserData.render(Directory(["."]))
    print(user_data.config._path_string)


    


    