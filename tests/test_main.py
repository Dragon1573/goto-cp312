from pytest import CaptureFixture, raises
from pytest_check import check  # type: ignore[import-untyped]

from goto import GOTO, LABEL, HackingError, with_goto


def test_01(capsys: CaptureFixture[str]):
    @with_goto
    def func():
        print("Hello!")
        GOTO.label_01
        print("Skiped...")
        LABEL.label_01
        print("world!")

    func()
    out, _ = capsys.readouterr()
    with check:
        assert out == "Hello!\nworld!\n"


def test_02(capsys: CaptureFixture[str]):
    @with_goto
    def func():
        for i in range(100):
            for j in range(100):
                for k in range(100):
                    print(k)
                    if k > 5:
                        tag = "Check success!"
                        GOTO.label_02
                        print("This should not be their!")
        print("Should not be there either!")
        LABEL.label_02
        print(tag)

    func()
    out, _ = capsys.readouterr()
    with check:
        assert out == "0\n1\n2\n3\n4\n5\n6\nCheck success!\n"


def test_03(capsys: CaptureFixture[str]):
    def func():
        k = 0
        while True:
            print(k)
            if k == 5:
                GOTO.label_03
            k += 1
        LABEL.label_03
        print("Force jump success!")

    with raises(HackingError):
        # Jump out from a forever-loop is impossible,
        # as Python will erase unreachable code
        with_goto(func)


def test_04(capsys: CaptureFixture[str]):
    @with_goto
    def func():
        i, j, k = 0, 0, 0
        while i < 100:
            while j < 100:
                while k < 100:
                    print(k)
                    if k >= 5:
                        GOTO.label_03
                    k += 1
                j += 1
            i += 1
        LABEL.label_03
        print("Force jump success!")

    func()
    out, _ = capsys.readouterr()
    with check:
        assert out == "0\n1\n2\n3\n4\n5\nForce jump success!\n"


def test_05(capsys: CaptureFixture[str]):
    @with_goto
    def func():
        k = 0
        LABEL.label_05
        if k > 5:
            print("Force jump success!")
            GOTO.label_06
        print(k)
        k += 1
        GOTO.label_05
        LABEL.label_06

    func()
    out, _ = capsys.readouterr()
    with check:
        assert out == "0\n1\n2\n3\n4\n5\nForce jump success!\n"
