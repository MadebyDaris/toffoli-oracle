from pathlib import Path

from toffoli_oracle import Xag
from toffoli_oracle.formats import read_verilog

DATA = Path(__file__).parent / "data"


def test_build_and_simulate_majority():
    xag = Xag()
    a, b, c = xag.add_input(), xag.add_input(), xag.add_input()
    # MAJ(a, b, c) = a ^ ((a ^ b) & (a ^ c)), one AND (mockturtle's create_maj)
    xag.add_output(xag.add_xor(a, xag.add_and(xag.add_xor(a, b), xag.add_xor(a, c))))
    [tt] = xag.simulate()
    assert tt == 0xE8
    assert xag.num_ands == 1 and xag.and_depth() == 1


def test_complemented_literals_and_constants():
    xag = Xag()
    a, b = xag.add_input(), xag.add_input()
    xag.add_output(xag.add_and(a ^ 1, b ^ 1))  # NOR
    xag.add_output(1)  # constant true
    xag.add_output(a ^ 1)  # NOT a
    nor, one, not_a = xag.simulate()
    assert (nor, one, not_a) == (0b0001, 0b1111, 0b0101)


def test_simulate_matches_evaluate():
    xag = read_verilog(DATA / "multiplier_4.v")
    tts = xag.simulate()
    for x in range(256):
        assert xag.evaluate(x) == sum(((tt >> x) & 1) << j for j, tt in enumerate(tts))
