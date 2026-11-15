"""Resource report (one JSON per oracle) and the hardware cost model from the design doc.

    T_run ~= max(N_tof * t_f / F, D_tof * t_r)       cost = Q_logical * T_run

F factories each make one Toffoli state every t_f; each sequential Toffoli layer costs a reaction
time t_r. With few factories the count dominates, with many the depth does.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from .xag import Xag


@dataclass(frozen=True)
class Hardware:
    factories: int = 1
    t_factory_s: float = 10e-6
    t_reaction_s: float = 1e-6


@dataclass
class Point:
    toffoli_count: int
    toffoli_depth: int
    logical_qubits: int
    mid_circuit_measurements: int = 0
    cnot_count: int = 0

    def runtime_s(self, hw: Hardware) -> float:
        return max(self.toffoli_count * hw.t_factory_s / hw.factories, self.toffoli_depth * hw.t_reaction_s)

    def spacetime(self, hw: Hardware) -> float:
        return self.logical_qubits * self.runtime_s(hw)


@dataclass
class ResourceReport:
    oracle: str
    inputs: int
    outputs: int
    chosen: Point
    front: list[Point] = field(default_factory=list)
    assumptions: dict = field(default_factory=dict)
    verified: dict | None = None

    def to_json(self, **kwargs) -> str:
        return json.dumps(asdict(self), **kwargs)


def lower_bound(xag: Xag) -> Point:
    """What the XAG itself promises, before any circuit is emitted.

    Toffolis = ANDs and depth = AND depth hold only if every uncompute is measurement-based.
    Qubits = inputs + outputs + one ancilla per AND (no reuse): an upper bound, pebbling lowers it.
    """
    return Point(
        toffoli_count=xag.num_ands,
        toffoli_depth=xag.and_depth(),
        logical_qubits=xag.num_inputs + len(xag.outputs) + xag.num_ands,
        mid_circuit_measurements=xag.num_ands,
        cnot_count=xag.num_xors,
    )
