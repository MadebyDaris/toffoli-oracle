# toffoli-oracle

Compile classical logic (arithmetic, comparators, lookups, crypto rounds) into fault-tolerant quantum
oracles whose **emitted cost matches the reported cost**, verified down to the phases.

On a fault-tolerant quantum computer the expensive gate is the Toffoli, and a classical function
written as an AND/XOR network (an XAG) costs about one Toffoli per AND. Existing compilers either
emit a second Toffoli to undo every intermediate AND while reporting only one (caterpillar), or don't
report a cost at all (tweedledum). Qiskit removed its classical-function compiler in 2.0. This project
builds on [mockturtle](https://github.com/lsils/mockturtle) (EPFL LSI), used unmodified, to optimize
the logic, then emits circuits that undo ANDs by measurement instead of a second Toffoli and checks
them against the ideal oracle.

**Status:** early. Logic optimization and cost reporting work; the circuit emitter and verifier are
next. See [ROADMAP.md](ROADMAP.md).

## What the outputs look like

One small function, `g = MAJ(a, b, c) AND d`, written the naive way with 6 ANDs
(`examples/majand_naive.v`):

```
$ ./build/opt/toffoli-opt examples/majand_naive.v examples/majand_opt.v
{"input": "examples/majand_naive.v", "before": {"ands": 6, "xors": 0, "and_depth": 4}, "after": {"ands": 2, "xors": 3, "and_depth": 2}, "equivalent": true}
```

mockturtle cuts it to 2 ANDs and proves the result equivalent with SAT. Turned into a quantum circuit:

| | Toffolis | Qubits | Notes |
|---|---|---|---|
| caterpillar | 3 | 6 | reports 2 |
| tweedledum | 3 | 6 | reports nothing |
| toffoli-oracle (target, hand-built) | 2 + 1 measurement | 6 | verified on all inputs, phases included |

On larger circuits the gap approaches 2x. For an 8x8 multiplier, mockturtle cuts 424 ANDs to 120;
caterpillar then emits 239 Toffolis and tweedledum 238, where measurement-based uncomputation needs 120.

## Quick start

Python package (Python >= 3.10, no runtime dependencies):

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/toffoli-oracle stats examples/majand_naive.v examples/majand_opt.v
```

```
oracle             in  out   ANDs   XORs AND-depth    runtime
majand_naive        4    1      6      0         4     60.0us
majand_opt          4    1      2      3         2     20.0us
```

C++ optimizer (CMake >= 3.16, a C++17 compiler):

```bash
./scripts/fetch_third_party.sh                 # mockturtle, caterpillar, tweedledum at pinned commits
cmake -S . -B build -G Ninja && cmake --build build
./build/opt/toffoli-opt examples/majand_naive.v out.v
```

## Layout

```
src/toffoli_oracle/   Python library: XAG, Verilog reader, resource report, CLI
opt/                  C++ driver over mockturtle (AND-count optimization, SAT-checked)
tests/                pytest, one file per module
examples/             small example circuits
sandbox/              measurements of mockturtle, caterpillar and tweedledum (start with sandbox/GUIDE.md)
scripts/, patches/    pinned source checkouts; a patched tweedledum build for Python 3.11+
```

## Built on

- [mockturtle](https://github.com/lsils/mockturtle): logic network library and the AND-count optimizations
- [caterpillar](https://github.com/gmeuli/caterpillar) and [tweedledum](https://github.com/boschmitt/tweedledum):
  the existing XAG-to-circuit compilers this project measures against
- Gidney, [*Halving the cost of quantum addition*](https://arxiv.org/abs/1709.06648) (2018): measurement-based uncomputation
