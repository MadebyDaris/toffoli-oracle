# Sandbox

Experiments with the existing tools (mockturtle, caterpillar, tweedledum, Qiskit 1.x). Nothing in
`src/` depends on this folder. Each experiment answers one question, and all results below were
measured on 25 Oct 2026 (Fedora 43, GCC 15.3, Python 3.10 for the old tools).

## Setup

```bash
./scripts/fetch_third_party.sh                     # mockturtle, caterpillar, tweedledum -> third_party/
conda env create -f sandbox/environment.yml        # python 3.10 + tweedledum 1.1.1 + qiskit 1.4 + aer
```

**Calling the env:** on this machine `conda run -n toffoli-sandbox ...` resolved to the system
pip. Call the env's interpreter directly, and set `PYTHONNOUSERSITE=1` so `~/.local` packages don't
leak in:

```bash
alias tsb='PYTHONNOUSERSITE=1 ~/.conda/envs/toffoli-sandbox/bin/python'
tsb -m pip install -e .            # the toffoli_oracle package also installs here (requires >=3.10)
```

### tweedledum on modern Python (3.11+)

`pip install tweedledum` fails on any Python newer than 3.10. There are three separate problems:

| Problem | Where | Fix |
|---|---|---|
| PyPI 1.1.1 has wheels only for ≤ 3.10; its sdist has an invalid `[project]` table (rejected by current setuptools) and bundles pybind11 2.6 | PyPI | Use the 3.10 env above, or build GitHub main |
| GitHub main (unreleased 1.2.0, nanobind) needs the Python C headers; Fedora's `/usr/bin/python3` has none (`python3-devel` not installed) | your machine | Use a conda Python, or `sudo dnf install python3-devel` |
| 1.2.0's nanobind bindings break 9 of 18 calls in `00_smoke_api.py`: `config` defaults need `.none()`, and STL casters (`optional`, `unordered_map`, …) aren't included | tweedledum | `patches/tweedledum-1.2.0-nanobind-bindings.patch` |

```bash
conda create -n tweedledum-dev -c conda-forge python=3.14 pip
~/.conda/envs/tweedledum-dev/bin/python -m pip install "qiskit>=2" qiskit-aer pytest numpy
./scripts/build_tweedledum.sh       # clone pinned main, apply patch, build (~80 s), run 00_smoke_api.py
```

On Python 3.14 + Qiskit 2.6, scripts 00–02 give the same numbers as the 3.10 env. Script 03 needs
Qiskit 1.x (`classicalfunction` is gone in 2.0), so it stays in `toffoli-sandbox`. Unpatched 1.2.0
still works if you always pass the config explicitly (`xag_synth(xag, {})`), which is what the
scripts do.

## mockturtle: what does the MC flow do, pass by pass?

```bash
cmake -S sandbox/mockturtle -B sandbox/mockturtle/build -G Ninja && cmake --build sandbox/mockturtle/build
(cd sandbox/mockturtle && ./build/mc_flow ../../bench/xag)   # writes bench/xag/*.v and bench/xag/naive/*.v
```

`mc_flow.cpp` builds naive AIG versions of the benchmarks (no XOR gates), converts them to XAGs,
and applies the passes one by one. Every result is SAT-checked against the input.

| benchmark | naive AIG→XAG | after `xag_dont_cares` | after `cut_rewriting(minmc)` | known optimum |
|---|---|---|---|---|
| adder_4 | 24 AND, depth 8 | 14 AND | **4 AND**, depth 4 | 4 |
| adder_16 | 108 AND, depth 32 | 62 AND | **16 AND**, depth 16 | 16 |
| less_than_8 | 39 AND, depth 17 | 23 AND | **8 AND**, depth 8 | |
| multiplier_4 | 84 AND, depth 16 | 56 AND | **28 AND**, depth 7 | |
| multiplier_8 | 424 AND, depth 40 | 272 AND | **120 AND**, depth 15 | |

`xag_constant_fanin_optimization` changed nothing here: it needs XOR chains that cancel, and a fresh
AIG has no XORs yet.

**Findings**

- `cut_rewriting_params::min_cand_cut_size` defaults to 3. With that default the adders stalled at
  about 3n ANDs (47 for 16 bits), because the AIG builds XNOR as `(~a & ~b) ^ (a & b)`, a 2-input
  cut. Setting it to 2 reaches the optimum, n.
- `exact_linear_resynthesis_optimization` (which reduces XORs, i.e. CNOTs) calls `std::abort()`
  ("No NOTs in linear forms allowed") on any network whose linear part has inverted edges, which
  is every adder here. It's left out of the flow for now.
- The same 16-bit adder generated *natively* as an XAG (`create_maj` = 1 AND) already has 16 ANDs.
  The front end matters as much as the optimizer.

## caterpillar: reported cost vs emitted circuit

```bash
cmake -S sandbox/caterpillar -B sandbox/caterpillar/build -G Ninja && cmake --build sandbox/caterpillar/build
./sandbox/caterpillar/build/strategies bench/xag
```

caterpillar bundles its own 2020 mockturtle and tweedledum, so it builds on its own. On GCC 15
only its bundled Catch2 fails (`MINSIGSTKSZ` isn't constexpr on glibc ≥ 2.34). Its own test suite
passes (115 cases) when built with `-DCMAKE_CXX_FLAGS="-DCATCH_CONFIG_NO_POSIX_SIGNALS"`.

| benchmark | ANDs | strategy | reported T (÷4 = Toffoli) | **emitted CCX** | qubits | T-depth |
|---|---|---|---|---|---|---|
| adder_16 | 16 | xag low-T | 64 (16) | **32** | 65 | 17 |
| adder_16 | 16 | bennett | 64 (16) | **32** | 124 | 17 |
| multiplier_8 | 120 | xag low-T | 480 (120) | **239** | 151 | 37 |
| multiplier_8 | 120 | xag low-depth | 480 (120) | **239** | 192 | 15 |
| multiplier_8 | 120 | bennett | 480 (120) | **239** | 382 | 16 |

Every strategy reports one Toffoli per AND and emits about two. The classical check
(`circuit_to_logic_network`) passes on every benchmark small enough to run it (≤ 16 inputs).

## tweedledum `xag_synth`: what it emits

```bash
tsb sandbox/tweedledum/01_xag_synth_cost.py
```

| benchmark | ANDs | CCX (on output, no cleanup) | CC-Rx(±π) pairs | Toffoli-like total |
|---|---|---|---|---|
| adder_4 | 4 | 4 | 0 | **4** |
| adder_16 | 16 | 16 | 0 | **16** |
| less_than_8 | 8 | 1 | 14 | 15 |
| multiplier_4 | 28 | 2 | 52 | 54 |
| multiplier_8 | 120 | 2 | 236 | 238 |

**Finding (it changes the README's claim):** `xag_synth` is smarter than "two gates per AND". It
groups each AND with the XORs above it (a "parity" graph). An AND whose result goes straight into
an output parity is computed onto the output qubit with one CCX and never uncomputed. Adders are
already optimal there (n Toffolis). The 2× overhead shows up on circuits whose ANDs feed other
ANDs, such as multipliers and comparators.

## Why the verifier must check phases

```bash
tsb sandbox/tweedledum/02_phase.py
```

- CC-Rx(π) = CCX · diag(1, …, −i on |11⟩ of the controls). It is a *relative* phase, not a global
  one.
- If the uncompute CC-Rx(−π) is swapped for a CCX (same truth table), the circuit is wrong. The
  classical check still passes; only the amplitude check catches it.

## The Qiskit 1.x front end that was removed in 2.0

```bash
tsb sandbox/tweedledum/03_qiskit_classical_function.py
```

`@classical_function` parses a typed Python function, and `.synth()` by default goes truth table →
ESOP → multi-controlled X (`pkrm_synth`). There is no XAG optimization and no Toffoli count. This
is the user experience a future Python front end should match.

## The target: what toffoli_oracle's emitter should produce

```bash
tdev sandbox/target/mbu_majand.py      # tdev = the tweedledum-dev env (Qiskit 2 + Aer)
```

A hand-built circuit for `g = MAJ(a,b,c) AND d` (mockturtle's 2-AND version in
`examples/majand_opt.v`): 2 Toffolis plus 1 measurement-based uncompute, where tweedledum and
caterpillar both emit 3 Toffolis. Verified on a superposition of all inputs with full amplitudes;
dropping the CZ fix-up drops the fidelity to 0.52 on half the runs. The side-by-side comparison of
all tools on this example is in `docs/tool-outputs.md`.

