from dis import dis
from io import StringIO
from types import CodeType
from typing import Callable

from opcode import opname

from ._constants import _COMMAND_TYPE, LOAD_ATTR, LOAD_GLOBAL_GOTO, LOAD_GLOBAL_LABEL, POP_TOP, HackingError, _JumpPair


def with_goto(func: Callable) -> Callable:
    """
    Bytecode-level hacking for `goto` implememtation

    Args:
        func (Callable): Type of wrapped function

    Returns:
        _T: Type of already wrapped function
    """
    # 跳转表
    jump_table: dict[str, _JumpPair] = {}

    # 获取原始函数的字节码
    flag = _COMMAND_TYPE.NORMAL
    c = func.__code__
    byte_array = bytearray(c.co_code)

    # 获取原始函数的可读字节码
    with StringIO() as fp:
        dis(c, file=fp)
        fp.seek(0)

        current_jump_start, current_label = 0, ""
        for line in fp.readlines():
            if line == "\n":
                # 可视化字节码是空行，这行直接跳过
                continue
            # 遍历字节码
            if flag is _COMMAND_TYPE.NORMAL:
                if m := LOAD_GLOBAL_GOTO.findall(line):
                    # 遇到 GOTO 标记，下一行就是标签，但要从此处起跳
                    flag = _COMMAND_TYPE.FROM
                    current_jump_start = int(m[0])
                elif m := LOAD_GLOBAL_LABEL.findall(line):
                    # 遇到 LABEL 标记，下一行是标签
                    flag = _COMMAND_TYPE.TO
                    byte_array[int(m[0])] = opname.index("NOP")
                    byte_array[int(m[0]) + 1] = 0
                # 其他场景则保留原始字节码
            elif flag is _COMMAND_TYPE.FROM:
                if m := LOAD_ATTR.findall(line):
                    # 这是 GOTO 后的标签位置
                    if (label := m[0][1]) not in jump_table:
                        jump_table[label] = _JumpPair(goto_begin=current_jump_start)
                    else:
                        jump_table[label].goto_begin = current_jump_start
                    byte_array[int(m[0][0])] = opname.index("NOP")
                    byte_array[int(m[0][0]) + 1] = 0
                elif m := POP_TOP.findall(line):
                    flag = _COMMAND_TYPE.NORMAL
                    byte_array[int(m[0])] = opname.index("NOP")
                    byte_array[int(m[0]) + 1] = 0
            elif flag is _COMMAND_TYPE.TO:
                if m := LOAD_ATTR.findall(line):
                    # 这是 LABEL 后的标签位置
                    current_label: str = m[0][1]  # type: ignore[no-redef]
                    # 其他指令全部变成 NOP
                    byte_array[int(m[0][0])] = opname.index("NOP")
                    byte_array[int(m[0][0]) + 1] = 0
                elif m := POP_TOP.findall(line):
                    flag = _COMMAND_TYPE.NORMAL
                    # 其他指令全部变成 NOP
                    byte_array[int(m[0])] = opname.index("NOP")
                    byte_array[int(m[0]) + 1] = 0
                    # POP_TOP 占2个字节，跳转到它的下一个字节位置上
                    if current_label not in jump_table:
                        jump_table[current_label] = _JumpPair(target=int(m[0]))
                    else:
                        jump_table[current_label].to = int(m[0])

    # 针对跳转表进行处理
    for pair in jump_table.values():
        if pair.goto_begin < 0 or pair.to < 0:
            raise HackingError("Unsupported structure in source code. Failed to hack T_T")
        byte_array[pair.goto_begin] = (
            opname.index("JUMP_FORWARD") if pair.goto_begin < pair.to else opname.index("JUMP_BACKWARD")
        )
        byte_array[pair.goto_begin + 1] = abs(pair.to - pair.goto_begin) // 2

    # 替换底层指令字节串
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
