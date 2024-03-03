from dataclasses import dataclass
from enum import Enum
from re import compile
from typing import Any

LOAD_GLOBAL_GOTO = compile(r"(\d+) LOAD_GLOBAL +\d+ \(GOTO\)")
LOAD_GLOBAL_LABEL = compile(r"(\d+) LOAD_GLOBAL +\d+ \(LABEL\)")
LOAD_ATTR = compile(r"(\d+) LOAD_ATTR +\d+ \((.*)\)")
POP_TOP = compile(r"(\d+) POP_TOP")


class _COMMAND_TYPE(Enum):
    FROM = "FROM"
    TO = "TO"
    NORMAL = "NORMAL"


class HackingError(RuntimeError):
    """A subclass of `RuntimeError`, use when the module unable to hack the bytecode."""

    pass


class _Placeholder:
    """Just a placeholder to prevent complaints from Static Type Checkers."""

    def __getattribute__(self, _: str) -> Any:
        pass


GOTO, LABEL = _Placeholder(), _Placeholder()


@dataclass
class _JumpPair:
    def __init__(self, goto_begin: int = -1, target: int = -1) -> None:
        self.goto_begin = goto_begin
        self.to = target
