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
3. If there's a `LOAD_GLOBAL (GOTO)`, and a `LOAD_ATTR` and a `POP_TOP` right next 2 lines, note down the byte position and the label, it's where we jump from.
4. Hack both `LOAD_ATTR` and `POP_TOP` to `NOP`.
5. If there's a `LOAD_GLOBAL (LABEL)`, and a `LOAD_ATTR` and a `POP_TOP` right next 2 lines, note down the byte position the next line of `POP_TOP` and the label, it's where we jump to. Hack all of them 3 to `NOP`.
6. Iterate over all `(label, from_, to)` pair, check if `from_` is smaller than `to`, to determine the next step behavior.
7. Hack the `from_` byte (where `LOAD_GLOBAL (GOTO)` located) to `JUMP_FORWARD` or `JUMP_BACKWARD`, depends on the previous step.

<details><summary>Raw disassemble content</summary>

```text
  6           0 RESUME                   0

  7           2 LOAD_GLOBAL              1 (NULL + print)
             12 LOAD_CONST               1 ('Hello, ')
             14 CALL                     1
             22 POP_TOP

  8          24 LOAD_GLOBAL              2 (GOTO)
             34 LOAD_ATTR                4 (label_01)
             54 POP_TOP

  9          56 LOAD_GLOBAL              1 (NULL + print)
             66 LOAD_CONST               2 ('Skipped!')
             68 CALL                     1
             76 POP_TOP

 10          78 LOAD_GLOBAL              6 (LABEL)
             88 LOAD_ATTR                4 (label_01)
            108 POP_TOP

 11         110 LOAD_GLOBAL              1 (NULL + print)
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
             26 CACHE
             28 CACHE
             30 CACHE
             32 CACHE
             34 NOP
             36 CACHE
             38 CACHE
             40 CACHE
             42 CACHE
             44 CACHE
             46 CACHE
             48 CACHE
             50 CACHE
             52 CACHE
             54 NOP

 10          56 LOAD_GLOBAL              1 (NULL + print)
             66 LOAD_CONST               2 ('Skipped!')
             68 CALL                     1
             76 POP_TOP

 11          78 NOP
             80 CACHE
             82 CACHE
             84 CACHE
             86 CACHE
             88 NOP
             90 CACHE
             92 CACHE
             94 CACHE
             96 CACHE
             98 CACHE
            100 CACHE
            102 CACHE
            104 CACHE
            106 CACHE
            108 NOP

 12     >>  110 LOAD_GLOBAL              1 (NULL + print)
            120 LOAD_CONST               3 ('world!')
            122 CALL                     1
            130 POP_TOP
            132 RETURN_CONST             0 (None)
```

</details>

## Limitations

- Jump forward only, you can't goto a label defined before the `GOTO`.
- Jump out from nested loop (`for` or `while`), but you can't jump into them.
- You can't jump to somewhere if they are "dead code" (Python intepreter will remove them), such as ...
  - Jump out from a `while True` loop, as the following snippets is unreachable
