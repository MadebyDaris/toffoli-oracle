"""Target: what toffoli_oracle's emitter should produce, hand-built for one small example.

g = MAJ(a, b, c) AND d, as optimized by mockturtle in examples/majand_opt.v:
    n7 = (c ^ b) & (c ^ a)     inner AND, lives on an ancilla, must be uncomputed
    g  = d & (n7 ^ c)          outer AND, computed straight onto the output qubit

Cost: 2 Toffolis + 1 X-measurement. For comparison, tweedledum and caterpillar both emit
3 doubly-controlled gates for the same XAG (see docs/tool-outputs.md).

Checks the circuit against the ideal oracle on a random superposition of all 16 inputs, comparing
full amplitudes (phases included), over 20 runs so both measurement outcomes occur. Then drops
the CZ fix-up to show that only a phase-sensitive check notices.

Run:  python sandbox/target/mbu_majand.py   (needs Qiskit 2 + qiskit-aer, e.g. the tweedledum-dev env)
"""

import numpy as np
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

# g = MAJ(a,b,c) & d as in examples/majand_opt.v:
#   n7 = (c^b) & (c^a)   inner AND -> ancilla
#   g  = d & (n7 ^ c)    outer AND -> output qubit
q = QuantumRegister(6, "q")          # 0..3 = a b c d, 4 = out, 5 = anc
m = ClassicalRegister(1, "m")
qc = QuantumCircuit(q, m)
a, b, c, d, out, anc = range(6)
qc.cx(c, b); qc.cx(c, a)             # parities in place: b^c, a^c
qc.ccx(a, b, anc)                    # Toffoli 1: anc = n7
qc.cx(c, a); qc.cx(c, b)             # restore a, b
qc.cx(c, anc)                        # anc = n7 ^ c = MAJ
qc.ccx(d, anc, out)                  # Toffoli 2: out = d & MAJ   (output AND, never uncomputed)
qc.cx(c, anc)                        # anc = n7 again
def uncompute(qc, fixup=True):
    qc.h(anc); qc.measure(anc, m[0])     # measurement-based uncompute of n7 ...
    with qc.if_test((m, 1)):
        qc.x(anc)                        # ... reset ancilla to |0>
        if fixup:
            qc.cx(c, b); qc.cx(c, a)
            qc.cz(a, b)                  # ... phase fix-up CZ on the AND's inputs (b^c, a^c)
            qc.cx(c, a); qc.cx(c, b)
body = qc.copy()
uncompute(qc)
print(qc.draw(output="text", fold=-1))
print("ops:", dict(qc.count_ops()))

def g(x):
    A, B, C, D = [(x >> i) & 1 for i in range(4)]
    return int(A + B + C >= 2) & D

sim = AerSimulator(method="statevector")
# ideal oracle on a random superposition of the 16 inputs (out=0, anc=0)
rng = np.random.default_rng(1)
amps = rng.normal(size=16) + 1j * rng.normal(size=16); amps /= np.linalg.norm(amps)
psi_in = np.zeros(64, complex); psi_out = np.zeros(64, complex)
for x in range(16):
    psi_in[x] = amps[x]; psi_out[x | (g(x) << 4)] = amps[x]
def check(circ, label):
    fid = {0: [], 1: []}
    for seed in range(20):
        t = QuantumCircuit(q, m); t.initialize(psi_in, q); t.compose(circ, inplace=True); t.save_statevector()
        res = sim.run(transpile(t, sim), seed_simulator=seed, shots=1).result()
        outcome = int(next(iter(res.get_counts())))
        fid[outcome].append(abs(np.vdot(psi_out, np.asarray(res.get_statevector()))) ** 2)  # phase-sensitive overlap
    for k in (0, 1):
        print(f"{label}: outcome m={k} seen {len(fid[k])}x, min fidelity {min(fid[k]) if fid[k] else float('nan'):.6f}")

check(qc, "with CZ fix-up   ")
nofix = body.copy(); uncompute(nofix, fixup=False)
check(nofix, "without fix-up   ")
