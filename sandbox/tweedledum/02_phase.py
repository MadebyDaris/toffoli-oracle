"""Sandbox 02: why the verifier must check phases, not just bit flips.

1. CC-Rx(pi) is not a Toffoli: it is CCX times a -i phase when both controls are 1.
   tweedledum uses it for ANDs it will uncompute, pairing it with CC-Rx(-pi) so the phases cancel.
2. If a later pass "simplifies" the uncompute gate (here: swaps CC-Rx(-pi) for a CCX, which looks
   classically identical), the circuit is broken, but a classical (permutation) check still passes.
   Only a statevector check that compares amplitudes catches it.

Run:  python sandbox/tweedledum/02_phase.py   (in the toffoli-sandbox env)
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import CCXGate, RXGate
from qiskit.converters import dag_to_circuit
from qiskit.quantum_info import Operator, Statevector
from tweedledum.classical import LogicNetwork
from tweedledum.passes import parity_decomp
from tweedledum.qiskit import to_qiskit
from tweedledum.synthesis import xag_synth


def gate_level() -> None:
    ccrx = QuantumCircuit(3)
    ccrx.append(RXGate(np.pi).control(2), [0, 1, 2])
    ccx = QuantumCircuit(3)
    ccx.append(CCXGate(), [0, 1, 2])
    diff = Operator(ccx).adjoint().compose(Operator(ccrx)).data
    print("1. CCX^dagger . CC-Rx(pi) = diag(...) =", np.round(np.diag(diff), 3))
    print("   equal up to global phase?", Operator(ccrx).equiv(Operator(ccx)), "(it is a *relative* phase)\n")


def build_circuit() -> tuple[QuantumCircuit, int]:
    # f(a, b, c) = (a & b) & c : the inner AND lives on an ancilla and must be uncomputed
    xag = LogicNetwork()
    a, b, c = xag.create_pi(), xag.create_pi(), xag.create_pi()
    xag.create_po(xag.create_and(xag.create_and(a, b), c))
    qc = dag_to_circuit(to_qiskit(parity_decomp(xag_synth(xag, {}))))
    return qc, 3


def phase_check(qc: QuantumCircuit, n_in: int) -> tuple[bool, bool]:
    """Return (classical_ok, amplitude_ok) over all basis inputs, ancillas starting in |0>."""
    classical_ok = amplitude_ok = True
    for x in range(2**n_in):
        a, b, c = (x >> 0) & 1, (x >> 1) & 1, (x >> 2) & 1
        f = a & b & c
        want = x | (f << n_in)  # inputs unchanged, output qubit = f, ancillas back to 0
        amp = Statevector.from_int(x, 2**qc.num_qubits).evolve(qc).data
        classical_ok &= bool(np.argmax(np.abs(amp)) == want)
        amplitude_ok &= bool(np.isclose(amp[want], 1.0))
    return classical_ok, amplitude_ok


def main() -> None:
    gate_level()

    qc, n_in = build_circuit()
    print("2. tweedledum circuit for f = (a & b) & c:")
    print(qc.draw(output="text", fold=-1))
    ok_c, ok_a = phase_check(qc, n_in)
    print(f"   as emitted     -> classical check: {ok_c},  amplitude check: {ok_a}")

    # "optimize" the uncompute: CC-Rx(-pi) -> CCX (same truth table, different phase)
    broken = qc.copy_empty_like()
    for inst in qc.data:
        op = inst.operation
        if op.name.startswith("ccrx") and op.base_gate.params[0] < 0:
            broken.append(CCXGate(ctrl_state=op.ctrl_state), inst.qubits)
        else:
            broken.append(op, inst.qubits, inst.clbits)
    ok_c, ok_a = phase_check(broken, n_in)
    print(f"   uncompute->CCX -> classical check: {ok_c},  amplitude check: {ok_a}   <- only the amplitude check sees it")


if __name__ == "__main__":
    main()
