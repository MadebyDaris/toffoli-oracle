from pathlib import Path

import pytest

from toffoli_oracle import Hardware, Point, lower_bound
from toffoli_oracle.formats import read_verilog

DATA = Path(__file__).parent / "data"


def test_runtime_model_switches_regime():
    p = Point(toffoli_count=1000, toffoli_depth=10, logical_qubits=50)
    few = Hardware(factories=1, t_factory_s=10e-6, t_reaction_s=1e-6)
    many = Hardware(factories=10_000, t_factory_s=10e-6, t_reaction_s=1e-6)
    assert p.runtime_s(few) == pytest.approx(1000 * 10e-6)  # count-bound
    assert p.runtime_s(many) == pytest.approx(10 * 1e-6)  # depth-bound
    assert p.spacetime(few) == pytest.approx(50 * 1000 * 10e-6)


def test_lower_bound():
    point = lower_bound(read_verilog(DATA / "adder_4.v"))
    assert point.toffoli_count == 4 and point.mid_circuit_measurements == 4
