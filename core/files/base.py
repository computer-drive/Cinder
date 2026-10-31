from __future__ import annotations

from pathlib import Path
from typing import Generic, Sequence, TypeVar, get_type_hints


def _validate_name(name: str) -> None:
    """只允许相对当前目录的普通名字，禁止绝对路径和 .. 越界。"""
    if not name:
        raise ValueError("文件名/目录名不能为空")

    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"非法路径名: {name!r}")


class File:
    __filename__ = ""

    def __init__(self, path: Directory, name: str, create: bool = True):
        _validate_name(name)

        self.directory = path
        self.name = name
        self.path = path.path / name
        self._path_string = str(self.path)

        if not self.path.exists():
            if create:
                self.create()
            else:
                raise FileNotFoundError(f"文件 {self.path} 不存在")
        elif not self.path.is_file():
            raise IsADirectoryError(f"路径 {self.path} 不是文件")

    def create(self) -> None:
        """创建文件（父目录不存在时一并创建）。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def open_text(self, mode: str = "r", encoding: str = "utf-8"):
        """打开文本文件。"""
        return self.path.open(mode, encoding=encoding)

    def open_binary(self, mode: str = "rb"):
        """打开二进制文件。"""
        return self.path.open(mode)

    def __fspath__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path!r})"


T = TypeVar("T", bound="Directory")


class Directory(Generic[T]):
    __dirname__ = ""

    def __init__(
        self,
        path: str | Path | Sequence[str],
        create_all: bool = True,
    ):
        if isinstance(path, (str, Path)):
            self.path = Path(path)
        else:
            self.path = Path(*path)

        self.path = self.path.expanduser().resolve()
        self._path_string = str(self.path)

        if not self.path.exists():
            if create_all:
                self.create()
            else:
                raise FileNotFoundError(f"目录 {self.path} 不存在")
        elif not self.path.is_dir():
            raise NotADirectoryError(f"路径 {self.path} 不是目录")

    @classmethod
    def render(
        cls: type[T],
        base_dir: Directory | str | Path,
        create_all: bool = True,
    ) -> T:
        """根据类型注解渲染目录树。"""
        if not isinstance(base_dir, Directory):
            base_dir = Directory(base_dir, create_all=create_all)

        if create_all:
            base_dir.create()

        if not cls.__dirname__:
            raise ValueError(f"目录 {cls.__name__} 未指定目录名")

        directory: T = cls(base_dir.path / cls.__dirname__, create_all)

        for name, annotation in get_type_hints(cls).items():
            if not isinstance(annotation, type):
                continue

            try:
                is_directory = issubclass(annotation, Directory)
                is_file = issubclass(annotation, File)
            except TypeError:
                continue

            if is_directory:
                setattr(
                    directory,
                    name,
                    annotation.render(directory, create_all),
                )
            elif is_file:
                if not annotation.__filename__:
                    raise ValueError(
                        f"文件 {annotation.__name__} 未指定文件名"
                    )
                setattr(
                    directory,
                    name,
                    annotation(
                        directory,
                        annotation.__filename__,
                        create_all,
                    ),
                )

        return directory

    def create(self) -> None:
        """创建目录。"""
        self.path.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[str]:
        """列出目录下所有条目（文件 + 子目录）。"""
        return sorted(item.name for item in self.path.iterdir())

    def list_files(self) -> list[str]:
        """只列出目录下的文件。"""
        return sorted(
            item.name for item in self.path.iterdir() if item.is_file()
        )

    def get_file(
        self,
        name: str,
        create: bool = True,
        file_type: type[File] = File,
    ) -> File:
        """获取文件。"""
        return file_type(self, name, create)

    def get_directory(self, name: str, create: bool = True) -> Directory:
        """获取子目录。"""
        _validate_name(name)
        return Directory(self.path / name, create)

    def get_top(self) -> Directory:
        """获取父目录；已经是根目录时返回自身。"""
        if self.path.parent == self.path:
            return self
        return Directory(self.path.parent, create_all=False)

    def __fspath__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path!r})"


if __name__ == "__main__":
    import tempfile

    class UserData(Directory):
        __dirname__ = "user"

        class Config(File):
            __filename__ = "config.json"

        config: Config

    user_data: UserData = UserData.render(Directory(["."]))
    print(user_data.config.path)
