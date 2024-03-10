from dis import dis
from io import StringIO
from types import CodeType
from typing import Callable

from opcode import opname

from ._constants import (
    _COMMAND_TYPE,
    LOAD_ATTR,
    LOAD_GLOBAL_GOTO,
    LOAD_GLOBAL_LABEL,
    POP_TOP,
    HackingError,
    _JumpPair,
)

# Convenient constants for OP_CODE
JUMP_FORWARD = opname.index("JUMP_FORWARD")
JUMP_BACKWARD = opname.index("JUMP_BACKWARD")
NOP = opname.index("NOP")
EXTENDED_ARG = opname.index("EXTENDED_ARG")


def with_goto(func: Callable) -> Callable:
    """
    Bytecode-level hacking for `goto` implememtation

    Args:
        func (Callable): Type of wrapped function

    Returns:
        _T: Type of already wrapped function
    """
    jump_table: dict[str, _JumpPair] = {}
    hack_table: dict[str, _JumpPair] = {}

    # Get bytecode of the raw function
    flag = _COMMAND_TYPE.NORMAL
    c = func.__code__
    byte_array = bytearray(c.co_code)

    # Get readable commands of the raw function
    with StringIO() as fp:
        dis(c, file=fp)
        fp.seek(0)

        current_jump_start, current_jump_label = 0, ""
        current_hack_start, current_hack_label = 0, ""
        for line in fp.readlines():
            # Iterate over commands
            if line == "\n":
                continue
            if flag is _COMMAND_TYPE.NORMAL:
                if m := LOAD_GLOBAL_GOTO.findall(line):
                    # We meet a `GOTO` tag, and the next command contains our label.
                    # We should jump from here.
                    flag = _COMMAND_TYPE.FROM
                    current_jump_start = int(m[0])
                    # We should leave at lease 2 bytes for replacing OP_CODE to `JUMP_???WARD`,
                    # hack following bytes to `NOP`.
                    current_hack_start = current_jump_start + 2
                elif m := LOAD_GLOBAL_LABEL.findall(line):
                    # We meet a `LABEL` tag, and the next command contains our label.
                    flag = _COMMAND_TYPE.TO
                    # This OP_CODE snippets is no needed, hack these bytes to `NOP`.
                    current_hack_start = int(m[0])
                # For other commands just keep them as-is.
            elif flag is _COMMAND_TYPE.FROM:
                if m := LOAD_ATTR.findall(line):
                    # Here contains the label name.
                    if (label := m[0][1]) not in jump_table:
                        jump_table[label] = _JumpPair(goto_begin=current_jump_start)
                    else:
                        jump_table[label].goto_begin = current_jump_start
                    # Note down the label and hack range information.
                    hack_table[current_hack_label := "GOTO." + label] = _JumpPair(goto_begin=current_hack_start)
                elif m := POP_TOP.findall(line):
                    flag = _COMMAND_TYPE.NORMAL
                    # `POP_TOP` takes 2 bytes, hack byte ranges until the next 2 bytes (excluded).
                    hack_table[current_hack_label].to = int(m[0]) + 2
            elif flag is _COMMAND_TYPE.TO:
                if m := LOAD_ATTR.findall(line):
                    # This is the command where label loaded.
                    current_jump_label: str = m[0][1]  # type: ignore[no-redef]
                    hack_table[current_hack_label := "LABEL." + current_jump_label] = _JumpPair(
                        goto_begin=current_hack_start
                    )
                elif m := POP_TOP.findall(line):
                    flag = _COMMAND_TYPE.NORMAL
                    # `POP_TOP` command only takes 2 bytes, we should jump the command right next to it.
                    if current_jump_label not in jump_table:
                        jump_table[current_jump_label] = _JumpPair(target=int(m[0]) + 2)
                    else:
                        jump_table[current_jump_label].to = int(m[0]) + 2
                    hack_table[current_hack_label].to = int(m[0]) + 2

    # Iterate over hack table, fill the byte range with `NOP`
    for name, pair in hack_table.items():
        if pair.goto_begin < 0 or pair.to < 0:
            raise HackingError(f"Unable to erase `{name}`. Failed to hack T_T")
        for _ in range(pair.goto_begin, pair.to, 2):
            byte_array[_] = NOP
            byte_array[_ + 1] = 0
    # Iterate over jump table, fixup all JUMP_XXX relationship.
    for pair in jump_table.values():
        if pair.goto_begin < 0:
            raise HackingError(f"There are missing `GOTO.{name}`. Failed to hack T_T")
        if pair.to < 0:
            raise HackingError(f"There are missing `LABEL.{name}`. Failed to hack T_T")
        # One byte only supports from 0 to 256, if we want to jump further, there's an EXTENDED_ARG
        # operation for us.
        gap, direction = abs(pair.to - pair.goto_begin) // 2, (-1 if pair.goto_begin < pair.to else 1)
        # Calculate original `EXTENDED_ARG` needed for gap.
        extend_count = gap.bit_length() // 8 - bool(gap.bit_length() % 8 == 0)
        # `EXTENDED_ARG` are included in gap, they may change the actual needed count.
        extend_count = (gap + extend_count).bit_length() // 8 - bool((gap + extend_count).bit_length() % 8 == 0)
        if extend_count > 3:
            raise HackingError("Only 3 `EXTENDED_ARG` are allowed in bytecode. You jump too far away!")
        # Now it's the actual gap we need to jump.
        gap += extend_count + direction
        for _ in range(extend_count, 0, -1):
            byte_array[pair.goto_begin] = EXTENDED_ARG
            byte_array[pair.goto_begin + 1] = (gap & (0xFF << (_ * 8))) >> (_ * 8)
            pair.goto_begin += 2
        byte_array[pair.goto_begin] = JUMP_BACKWARD if direction > 0 else JUMP_FORWARD
        byte_array[pair.goto_begin + 1] = gap & 0xFF

    # Replace code object of the raw function.
    func.__code__ = CodeType(
        c.co_argcount,
        c.co_posonlyargcount,
        c.co_kwonlyargcount,
        c.co_nlocals,
        c.co_stacksize,
        c.co_flags,
        bytes(byte_array),
        c.co_consts,
        c.co_names,
        c.co_varnames,
        c.co_filename,
        c.co_name,
        c.co_qualname,
        c.co_firstlineno,
        c.co_linetable,
        c.co_exceptiontable,
        c.co_freevars,
        c.co_cellvars,
    )

    return func
