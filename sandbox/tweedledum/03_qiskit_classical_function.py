"""Sandbox 03: the Qiskit 1.x front end that was removed in 2.0.

`qiskit.circuit.classicalfunction` parsed a typed Python function, built an XAG through tweedledum,
and synthesized it (by default with pkrm_synth: one multi-controlled X per ESOP cube, no XAG
optimization at all). Note the MCX with 4 controls in grover_oracle: its Toffoli cost depends on how
it is later decomposed (ancillas or not), and nothing here reports it. This is the user experience toffoli-oracle's Python front end should match.

Run:  python sandbox/tweedledum/03_qiskit_classical_function.py   (in the toffoli-sandbox env)
"""

import warnings

from qiskit.circuit.classicalfunction import classical_function
from qiskit.circuit.classicalfunction.types import Int1

warnings.filterwarnings("ignore", category=DeprecationWarning)


@classical_function
def majority(a: Int1, b: Int1, c: Int1) -> Int1:
    return (a and b) or (a and c) or (b and c)


@classical_function
def grover_oracle(a: Int1, b: Int1, c: Int1, d: Int1) -> Int1:
    return (not a and b and not c and d)


for name, fn in [("majority", majority), ("grover_oracle", grover_oracle)]:
    qc = fn.synth()  # default synthesizer: PKRM (truth table -> ESOP -> MCX gates)
    print(f"== {name}: {len(fn.args)} inputs ==")
    print(qc.draw(output="text", fold=-1))
    print("  ops as synthesized:   ", dict(qc.count_ops()))
    print()
