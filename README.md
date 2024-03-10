# goto-cp312

A simple package that provide limited supports of `goto` keyword like C/C++.

> [!IMPORTANT]
>
> This package is only tested locally on Windows `amd64` on CPython 3.12.2. Use this package with caution!

## Usage

```python
from goto import GOTO, LABEL, with_goto

@with_goto
def example_01() -> None:
    print("Hello, ")
    GOTO.label_01
    print("Skipped!")
    LABEL.label_01
    print("world!")


if __name__ == "__main__":
    example_01()
```

## How this work

1. Disassemble the raw function.
2. Iterate over the disassembled contents.
3. If there‘re `LOAD_GLOBAL (GOTO)`, `LOAD_ATTR` and `POP_TOP` in continuing 3 lines, note down the byte position and the label, it's where we jump from.
4. Hack full byte range of above 3 operations to `NOP`, except the first 2 bytes of `LOAD_GLOBAL`.
5. If there're `LOAD_GLOBAL (LABEL)`, `LOAD_ATTR` and `POP_TOP` in continuing 3 lines, note down the byte position the next line of `POP_TOP` and the label, it's where we jump to.
5. Hack full byte range of above 3 operations to `NOP`.
6. Iterate over all `(label, from_, to)` pair, check if `from_` is smaller than `to`, to determine there should be `JUMP_FORWARD` or `JUMP_BACKWARD`.
7. Hack the `from_` byte position to `JUMP_FORWARD` or `JUMP_BACKWARD` according to step 7. If `from_` is far away from `to` (jump more than 256 operations), add necessary `EXTENDED_ARG`.

<details><summary>Source code</summary>

```python
from dis import dis

from goto import GOTO, LABEL, with_goto


@with_goto
def example_01() -> None:
    print("Hello, ")
    GOTO.label_01
    print("Skipped!")
    LABEL.label_01
    print("world!")


if __name__ == "__main__":
    dis(example_01)
```

</details>

<details><summary>Raw disassemble content</summary>

```text
  7           0 RESUME                   0

  8           2 LOAD_GLOBAL              1 (NULL + print)
             12 LOAD_CONST               1 ('Hello, ')
             14 CALL                     1
             22 POP_TOP

  9          24 LOAD_GLOBAL              2 (GOTO)
             34 LOAD_ATTR                4 (label_01)
             54 POP_TOP

 10          56 LOAD_GLOBAL              1 (NULL + print)
             66 LOAD_CONST               2 ('Skipped!')
             68 CALL                     1
             76 POP_TOP

 11          78 LOAD_GLOBAL              6 (LABEL)
             88 LOAD_ATTR                4 (label_01)
            108 POP_TOP

 12         110 LOAD_GLOBAL              1 (NULL + print)
            120 LOAD_CONST               3 ('world!')
            122 CALL                     1
            130 POP_TOP
            132 RETURN_CONST             0 (None)
```

</details>

<details><summary>Hacked disassemble content</summary>

```text
  6           0 RESUME                   0

  8           2 LOAD_GLOBAL              1 (NULL + print)
             12 LOAD_CONST               1 ('Hello, ')
             14 CALL                     1
             22 POP_TOP

  9          24 JUMP_FORWARD            42 (to 110)
             26 NOP
             28 NOP
             30 NOP
             32 NOP
             34 NOP
             36 NOP
             38 NOP
             40 NOP
             42 NOP
             44 NOP
             46 NOP
             48 NOP
             50 NOP
             52 NOP
             54 NOP

 10          56 LOAD_GLOBAL              1 (NULL + print)
             66 LOAD_CONST               2 ('Skipped!')
             68 CALL                     1
             76 POP_TOP

 11          78 NOP
             80 NOP
             82 NOP
             84 NOP
             86 NOP
             88 NOP
             90 NOP
             92 NOP
             94 NOP
             96 NOP
             98 NOP
            100 NOP
            102 NOP
            104 NOP
            106 NOP
            108 NOP

 12     >>  110 LOAD_GLOBAL              1 (NULL + print)
            120 LOAD_CONST               3 ('world!')
            122 CALL                     1
            130 POP_TOP
            132 RETURN_CONST             0 (None)
```

</details>

## Limitations

- It's able to jump out from nested loop (`for` or `while`), but you can't jump into them.
- There're 3 `EXTENDED_ARG` operation before other operations at most, means that the jumping gap is no more than 4G. You can't jump such that HUGE distance. (This limitation has no chance to reach for human-written source code)
- You can't jump to somewhere if they are "dead code" (Python intepreter will remove them directly), such as ...
  - Jump out from a `while True` loop, as the following snippets is unreachable
