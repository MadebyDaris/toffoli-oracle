# kirin/: write oracles in Python, compile them with Kirin

A small showcase of [Kirin](https://github.com/QuEraComputing/kirin) (QuEra's compiler
infrastructure, the base of Bloqade) as a front end for toffoli-oracle.

```python
@xag_kernel
def maj_and(a: bool, b: bool, c: bool, d: bool) -> bool:
    return ((a & b) | (a & c) | (b & c)) & d
```

`demo.py` takes that function through:

## Run

Needs `build/opt/toffoli-opt` (see the top-level README, "C++ optimizer").

```bash
cd kirin
uv run python demo.py
```

## Files

| file | what |
|---|---|
| `xag_dialect.py` | the dialect: statements, Python lowering, concrete interpreter, `xag_kernel` group |
| `rewrite.py` | `EliminateOr`, `DoubleNegation`, `to_and_xor_form` |
| `bridge.py` | `to_xag` / `from_xag` (Kirin ↔ Xag), `write_verilog`, `optimize_with_mockturtle` |
| `demo.py` | the end-to-end walkthrough on `maj_and` and a 2-bit adder |

## Where this could go

- Emit the circuit as a Bloqade `squin` kernel (Gidney AND compute, measurement-based uncompute)
  as a Kirin rewrite from `xag` to `squin`, and verify it with PyQrack / tsim.
- Move the AND-count / AND-depth into a Kirin analysis pass instead of going through `Xag`.
