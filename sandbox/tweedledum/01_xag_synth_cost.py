"""Sandbox 01: what does tweedledum's xag_synth actually emit for a mockturtle XAG?

For every XAG in bench/xag/ (written by sandbox/mockturtle/mc_flow) we report
  ANDs in the XAG                -> the Toffoli count a perfect compiler would pay
  (2c)x                          -> plain Toffoli, used when the AND lands on an output qubit (no cleanup)
  (2c)rx  (+pi and -pi)          -> AND computed on an ancilla, then uncomputed with a second
                                    doubly-controlled gate; this pair is the "2 Toffolis per AND" cost
and check the emitted circuit classically against the XAG on every input.

Run:  python sandbox/tweedledum/01_xag_synth_cost.py   (in the toffoli-sandbox env)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from qiskit.converters import dag_to_circuit
from tweedledum.classical import read_verilog, simulate
from tweedledum.passes import count_operators, parity_decomp
from tweedledum.qiskit import to_qiskit
from tweedledum.synthesis import xag_synth

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "bench" / "xag"


def count_ands(verilog: Path) -> int:
    return sum(1 for line in verilog.read_text().splitlines() if re.match(r"\s*assign n\d+ = .*&", line))


def classical_check(path: Path, max_inputs: int = 16) -> str:
    """Run the emitted circuit as a reversible classical circuit on every basis input.

    This is the same kind of check caterpillar's circuit_to_logic_network gives you: it sees
    bit flips only, so it is blind to the -i phase that CC-Rx(pi) leaves behind (see 02_phase.py).
    """
    xag = read_verilog(str(path))
    n_in, n_out = xag.num_pis(), xag.num_pos()
    if n_in > max_inputs:
        return "skipped"
    qc = dag_to_circuit(to_qiskit(parity_decomp(xag_synth(xag, {}))))  # parity_decomp: ext.parity -> CNOTs
    tables = simulate(xag)  # one TruthTable per output, bit i = value on input assignment i

    # Translate the circuit once: (controls with required values, target). Reading qc.data inside
    # the input loop is very slow on Qiskit 2, which builds a new Python object per access.
    gates = []
    for inst in qc.data:
        op, qs = inst.operation, [qc.find_bit(q).index for q in inst.qubits]
        base = getattr(op, "base_gate", op).name
        if base not in ("x", "rx"):
            return f"unknown gate {op.name}"
        # CC-Rx(+-pi) = CCX up to a phase on the controls -> classical action is a bit flip.
        # Negated controls show up as ctrl_state (e.g. "ccrx_o2").
        ctrl = getattr(op, "ctrl_state", 0)
        gates.append(([(q, (ctrl >> i) & 1) for i, q in enumerate(qs[:-1])], qs[-1]))

    for x in range(2**n_in):
        state = [(x >> i) & 1 for i in range(n_in)] + [0] * (qc.num_qubits - n_in)
        for controls, target in gates:
            if all(state[q] == v for q, v in controls):
                state[target] ^= 1
        got = state[n_in : n_in + n_out]
        want = [int(tables[o][x]) for o in range(n_out)]
        if got != want:
            return f"MISMATCH at input {x}"
    return f"ok ({2**n_in} inputs)"


def main() -> int:
    files = sorted(BENCH.glob("*.v"))
    if not files:
        print(f"no XAGs in {BENCH}; build and run sandbox/mockturtle first")
        return 1
    print(f"{'benchmark':<14} {'ANDs':>5} {'CCX':>5} {'CCRx':>5} {'Toffoli-like':>13} {'qubits':>7}  classical check")
    for path in files:
        xag = read_verilog(str(path))
        circuit = xag_synth(xag, {})  # explicit config: tweedledum 1.2.0 rejects the default (see 00_smoke_api.py)
        ops = count_operators(circuit)
        ccx = ops.get("(2c)x", 0)
        ccrx = ops.get("(2c)rx", 0)
        print(
            f"{path.stem:<14} {count_ands(path):>5} {ccx:>5} {ccrx:>5} {ccx + ccrx:>13} {circuit.num_qubits():>7}  "
            f"{classical_check(path)}"
        )
    print("\nToffoli-like = CCX + CCRx = what a per-Toffoli machine pays today.")
    print("With measurement-based uncomputation each CCRx(-pi) becomes a measurement + CZ fix-up (0 Toffolis).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
