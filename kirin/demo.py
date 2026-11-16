"""Python function -> Kirin IR -> rewrite -> Xag -> mockturtle -> Kirin IR -> verify.

    cd kirin && uv run python demo.py
"""

from __future__ import annotations

from itertools import product

from kirin import ir

from toffoli_oracle.report import lower_bound

import bridge
from rewrite import to_and_xor_form
from xag_dialect import xag_kernel


# 1. Write the oracle as ordinary Python. Kirin parses it into SSA IR.
@xag_kernel
def maj_and(a: bool, b: bool, c: bool, d: bool) -> bool:
    return ((a & b) | (a & c) | (b & c)) & d


# A multi-output oracle: 2-bit adder (sum, carry) of a1a0 + b1b0.
@xag_kernel
def add2(a0: bool, a1: bool, b0: bool, b1: bool):
    s0 = a0 ^ b0
    c0 = a0 & b0
    s1 = a1 ^ b1 ^ c0
    c1 = (a1 & b1) | (c0 & (a1 ^ b1))
    return s0, s1, c1


def truth_table(mt: ir.Method, n: int) -> list:
    """Run the kernel in Kirin's interpreter on every input."""
    return [mt(*bits) for bits in product([False, True], repeat=n)]


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def run(kernel: ir.Method) -> None:
    inputs = kernel.arg_names[1:]  # arg_names[0] is the kernel's `self`
    n = len(inputs)
    reference = truth_table(kernel, n)  # semantics of the source, before any pass

    section(f"[{kernel.sym_name}] 1. Python -> Kirin IR")
    kernel.print()

    section(f"[{kernel.sym_name}] 2. Kirin rewrite: OR -> AND/NOT (De Morgan)")
    to_and_xor_form(kernel)
    kernel.print()
    assert truth_table(kernel, n) == reference, "rewrite changed the function"

    section(f"[{kernel.sym_name}] 3. Kirin IR -> toffoli_oracle.Xag -> toffoli-opt (mockturtle)")
    xag = bridge.to_xag(kernel)
    optimized, stats = bridge.optimize_with_mockturtle(xag)
    print("toffoli-opt:", stats)

    section(f"[{kernel.sym_name}] 4. mockturtle's XAG back into Kirin IR")
    opt_kernel = bridge.from_xag(optimized, f"{kernel.sym_name}_opt", inputs)
    opt_kernel.print()

    section(f"[{kernel.sym_name}] 5. Verify and report")
    ok = truth_table(opt_kernel, n) == reference
    print(f"Kirin interpreter, all {2**n} inputs: optimized == source ? {ok}")
    assert ok
    for label, x in (("before", xag), ("after ", optimized)):
        p = lower_bound(x)
        print(f"  {label}: Toffolis={p.toffoli_count}  Toffoli-depth={p.toffoli_depth}  "
              f"logical qubits<={p.logical_qubits}  CNOTs={p.cnot_count}")


if __name__ == "__main__":
    run(maj_and)
    run(add2)
