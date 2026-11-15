from pathlib import Path

import pytest

from toffoli_oracle.formats import read_verilog

DATA = Path(__file__).parent / "data"


def unpack(x: int, n: int) -> tuple[int, int]:
    """Split an input assignment into operands a (inputs 0..n-1) and b (inputs n..2n-1)."""
    mask = (1 << n) - 1
    return x & mask, (x >> n) & mask


def test_mockturtle_adder_4():
    xag = read_verilog(DATA / "adder_4.v")
    for x in range(256):
        a, b = unpack(x, 4)
        assert xag.evaluate(x) == a + b  # 4 sum bits + carry out


def test_mockturtle_adder_4_costs():
    xag = read_verilog(DATA / "adder_4.v")
    assert (xag.num_inputs, len(xag.outputs)) == (8, 5)
    assert xag.num_ands == 4  # MC of an n-bit adder is n
    assert xag.and_depth() == 4


def test_mockturtle_less_than_8():
    xag = read_verilog(DATA / "less_than_8.v")
    [tt] = xag.simulate()
    for x in range(1 << 16):
        a, b = unpack(x, 8)
        assert (tt >> x) & 1 == (a < b)


def test_mockturtle_multiplier_4():
    xag = read_verilog(DATA / "multiplier_4.v")
    for x in range(256):
        a, b = unpack(x, 4)
        assert xag.evaluate(x) == a * b


def test_reader_rejects_unknown_syntax():
    with pytest.raises(ValueError):
        read_verilog("module top(x0, y0);\n input x0;\n output y0;\n assign y0 = x0 | x0;\nendmodule\n")
