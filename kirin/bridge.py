"""Kirin IR  <->  toffoli_oracle.Xag  <->  Verilog  <->  toffoli-opt (mockturtle)."""

from __future__ import annotations

import json
import tempfile
import subprocess
from pathlib import Path

from kirin import ir, types
from kirin.dialects import py, func

from toffoli_oracle.xag import Op, Xag
from toffoli_oracle.formats import read_verilog

from xag_dialect import Or, And, Not, Xor, xag_kernel

REPO = Path(__file__).resolve().parents[1]
TOFFOLI_OPT = REPO / "build" / "opt" / "toffoli-opt"


# Kirin -> Xag 


def to_xag(mt: ir.Method) -> Xag:
    """Export a kernel (after `rewrite.to_and_xor_form`) to an Xag.

    Walks the SSA body in order; every SSA value maps to an AIGER literal.
    `not` costs nothing: it just flips the literal's complement bit.
    """
    block = mt.callable_region.blocks[0]
    xag = Xag()
    lit: dict[ir.SSAValue, int] = {}
    for arg in block.args[1:]:  # args[0] is the kernel's `self`
        lit[arg] = xag.add_input(arg.name)

    for stmt in block.stmts:
        if isinstance(stmt, And):
            lit[stmt.result] = xag.add_and(lit[stmt.lhs], lit[stmt.rhs])
        elif isinstance(stmt, Xor):
            lit[stmt.result] = xag.add_xor(lit[stmt.lhs], lit[stmt.rhs])
        elif isinstance(stmt, Not):
            lit[stmt.result] = lit[stmt.value] ^ 1
        elif isinstance(stmt, py.Constant):
            lit[stmt.result] = int(bool(stmt.value.unwrap()))
        elif isinstance(stmt, py.tuple.New):
            lit[stmt.result] = -1  # only used by the return below
        elif isinstance(stmt, func.Return):
            ret = stmt.value
            outs = ret.owner.args if isinstance(ret.owner, py.tuple.New) else [ret]
            for k, out in enumerate(outs):
                xag.add_output(lit[out], f"y{k}")
        elif isinstance(stmt, Or):
            raise ValueError("run rewrite.to_and_xor_form first: XAGs have no OR gate")
        else:
            raise ValueError(f"unsupported statement in an xag kernel: {stmt.name}")
    return xag


# Xag -> Kirin


def from_xag(xag: Xag, name: str, arg_names: list[str] | None = None) -> ir.Method:
    """Build a Kirin kernel from an Xag (e.g. one mockturtle optimized)."""
    arg_names = arg_names or xag.input_names
    block = ir.Block()
    block.args.append_from(types.MethodType, f"{name}_self")
    node_value: dict[int, ir.SSAValue] = {}
    for i, arg_name in enumerate(arg_names, start=1):
        node_value[i] = block.args.append_from(types.Bool, arg_name)

    negated: dict[int, ir.SSAValue] = {}

    def push(stmt: ir.Statement) -> ir.SSAValue:
        block.stmts.append(stmt)
        return stmt.results[0]

    def value(literal: int) -> ir.SSAValue:
        node = literal >> 1
        if node == 0:  # constant false / true
            return push(py.Constant(bool(literal & 1)))
        if not literal & 1:
            return node_value[node]
        if node not in negated:
            negated[node] = push(Not(node_value[node]))
        return negated[node]

    for k, gate in enumerate(xag.gates):
        stmt = And if gate.op is Op.AND else Xor
        node_value[xag.num_inputs + 1 + k] = push(stmt(value(gate.a), value(gate.b)))

    outs = [value(o) for o in xag.outputs]
    if len(outs) == 1:
        ret, out_type = outs[0], types.Bool
    else:
        ret = push(py.tuple.New(tuple(outs)))
        out_type = types.Tuple[tuple(types.Bool for _ in outs)]
    block.stmts.append(func.Return(ret))

    code = func.Function(
        sym_name=name,
        slots=tuple(arg_names),  # parameter names shown in the printed signature
        signature=func.Signature(inputs=(types.Bool,) * xag.num_inputs, output=out_type),
        body=ir.Region(block),
    )
    mt = ir.Method(
        dialects=xag_kernel, code=code, sym_name=name, arg_names=[f"{name}_self", *arg_names]
    )
    mt.verify()
    return mt


# Xag -> Verilog -> mockturtle -> Xag


def write_verilog(xag: Xag) -> str:
    """The same Verilog subset mockturtle writes and formats.read_verilog reads."""
    names = {0: "1'b0"} | {i: f"x{i - 1}" for i in range(1, xag.num_inputs + 1)}
    wires = [f"n{xag.num_inputs + 1 + k}" for k in range(len(xag.gates))]
    names |= {xag.num_inputs + 1 + k: w for k, w in enumerate(wires)}

    def lit(literal: int) -> str:
        if literal == 1:
            return "1'b1"
        return ("~" if literal & 1 else "") + names[literal >> 1]

    ins = [f"x{i}" for i in range(xag.num_inputs)]
    outs = [f"y{k}" for k in range(len(xag.outputs))]
    lines = [f"module top( {' , '.join(ins + outs)} );"]
    lines.append(f"  input {' , '.join(ins)} ;")
    lines.append(f"  output {' , '.join(outs)} ;")
    if wires:
        lines.append(f"  wire {' , '.join(wires)} ;")
    for wire, gate in zip(wires, xag.gates):
        lines.append(f"  assign {wire} = {lit(gate.a)} {gate.op.value} {lit(gate.b)} ;")
    for out, o in zip(outs, xag.outputs):
        lines.append(f"  assign {out} = {lit(o)} ;")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def optimize_with_mockturtle(xag: Xag) -> tuple[Xag, dict]:
    """Round-trip through the C++ toffoli-opt driver; returns the optimized Xag + its JSON."""
    if not TOFFOLI_OPT.exists():
        raise FileNotFoundError(f"{TOFFOLI_OPT} not built; see the repo README (C++ optimizer)")
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "in.v", Path(tmp) / "out.v"
        src.write_text(write_verilog(xag))
        out = subprocess.run([str(TOFFOLI_OPT), str(src), str(dst)], check=True, capture_output=True, text=True)
        return read_verilog(dst), json.loads(out.stdout)
