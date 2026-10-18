import sys

from .command import Command
from ..ui.manager import Manager as UIManager
class Parser:

    def __init__(self, ui_manager: UIManager):
        self.commands: dict[str, Command] = {}
        self.ui = ui_manager

    def register(self, command: Command):
        self.commands[command.__command_name__] = command

    def show_help(self):
        # TODO!!!
        self.ui.println("TODO!!!!!!")

    def parse(self):
        args = sys.argv[1:]

        if not args:
            self.show_help()
        else:
            pass
            # TODO!!!!!