from typing import Any

class Argument:
    def __init__(self, *name: str, optional: tuple[bool, Any] = (False, None), help: str | None = None):
        self.names: tuple[str, ...] = name
        self.optional = optional
        self.help = help

    def is_positional(self):
        return len(self.names) == 0
        