"""Sandbox 00: call each tweedledum Python API once and report which bindings are broken.

Written for tweedledum 1.2.0 (unreleased, GitHub main), whose bindings moved from pybind11 to
nanobind. Typical nanobind porting bugs show up as
  "incompatible function arguments"            (a None default without nb::arg(...).none())
  "Unable to convert function return value"    (a missing #include <nanobind/stl/...>)

Run:  python sandbox/tweedledum/00_smoke_api.py   (in any env with tweedledum installed)
"""

from __future__ import annotations

import sys
from importlib.metadata import version

from tweedledum.bool_function_compiler import BoolFunction
from tweedledum.classical import LogicNetwork, TruthTable, create_from_binary_string, simulate
from tweedledum.ir import Circuit, rotation_angle
from tweedledum.operators import Rx, X
from tweedledum.passes import (
    compute_alap_layers,
    compute_asap_layers,
    compute_critical_paths,
    compute_depth,
    count_operators,
    gate_cancellation,
    inverse,
    parity_decomp,
    phase_folding,
)
from tweedledum.synthesis import pkrm_synth, pprm_synth, xag_synth


def xag() -> LogicNetwork:
    ntk = LogicNetwork()
    a, b, c = ntk.create_pi(), ntk.create_pi(), ntk.create_pi()
    ntk.create_po(ntk.create_and(ntk.create_and(a, b), c))
    return ntk


def truth_table() -> TruthTable:
    tt = TruthTable(3)
    create_from_binary_string(tt, "10000000")
    return tt


def first_rx(c: Circuit):
    return next(inst for inst in c if "rx" in inst.kind())


CHECKS = {
    "xag_synth(xag)": lambda: xag_synth(xag()),
    "xag_synth(xag, {})": lambda: xag_synth(xag(), {}),
    "pkrm_synth(tt)": lambda: pkrm_synth(truth_table()),
    "pprm_synth(tt)": lambda: pprm_synth(truth_table()),
    "simulate(xag)": lambda: simulate(xag()),
    "BoolFunction.from_expression": lambda: BoolFunction.from_expression("(a & b) ^ c").simulate_all(),
    "count_operators": lambda: count_operators(xag_synth(xag(), {})),
    "compute_depth": lambda: compute_depth(xag_synth(xag(), {})),
    "compute_asap_layers": lambda: compute_asap_layers(xag_synth(xag(), {})),
    "compute_alap_layers": lambda: compute_alap_layers(xag_synth(xag(), {})),
    "compute_critical_paths": lambda: compute_critical_paths(xag_synth(xag(), {})),
    "parity_decomp": lambda: parity_decomp(xag_synth(xag(), {})),
    "inverse": lambda: inverse(xag_synth(xag(), {})),
    "gate_cancellation": lambda: gate_cancellation(xag_synth(xag(), {})),
    "phase_folding": lambda: phase_folding(parity_decomp(xag_synth(xag(), {}))),
    "rotation_angle": lambda: rotation_angle(first_rx(xag_synth(xag(), {}))),
    "Circuit.apply_operator": lambda: _apply(),
    "qiskit converters": lambda: _qiskit_roundtrip(),
}


def _apply():
    c = Circuit()
    q = [c.create_qubit() for _ in range(3)]
    c.apply_operator(X(), q)
    c.apply_operator(Rx(0.5), [q[0]])
    return c.num_qubits()


def _qiskit_roundtrip():
    from tweedledum.qiskit import from_qiskit, to_qiskit

    return from_qiskit(to_qiskit(parity_decomp(xag_synth(xag(), {})), circuit_type="gatelist")).num_qubits()


def main() -> int:
    print(f"tweedledum {version('tweedledum')}, Python {sys.version.split()[0]}")
    failed = 0
    for name, check in CHECKS.items():
        try:
            check()
            print(f"  ok    {name}")
        except Exception as e:  # noqa: BLE001 - we want every failure listed, not the first
            failed += 1
            print(f"  FAIL  {name}: {type(e).__name__}: {str(e).splitlines()[0]}")
    print(f"{len(CHECKS) - failed}/{len(CHECKS)} ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
