"""A tiny Kirin dialect for XOR-AND graphs, written as plain Python.

    @xag_kernel
    def maj_and(a: bool, b: bool, c: bool, d: bool) -> bool:
        return ((a & b) | (a & c) | (b & c)) & d

Kirin parses the function body into SSA IR with these statements:

    xag.and  xag.xor  xag.or  xag.not

`&`, `^`, `|`, `~` (and `and`, `or`, `not`) are lowered to them. `xag.or` and
`xag.not` are only surface syntax: an XAG has no OR gate and gets negation for free
(a complemented literal), so `rewrite.EliminateOr` turns every OR into ANDs + NOTs
before the IR is exported to toffoli_oracle.Xag.
"""

from __future__ import annotations

import ast

from kirin import ir, types, lowering
from kirin.decl import info, statement
from kirin.interp import Frame, Interpreter, MethodTable, impl
from kirin.dialects import py, func, ssacfg
from kirin.dialects import lowering as func_lowering

dialect = ir.Dialect("xag")


# statements 


@statement(dialect=dialect)
class And(ir.Statement):
    name = "and"
    traits = frozenset({ir.Pure()})
    lhs: ir.SSAValue = info.argument(types.Bool)
    rhs: ir.SSAValue = info.argument(types.Bool)
    result: ir.ResultValue = info.result(types.Bool)


@statement(dialect=dialect)
class Xor(ir.Statement):
    name = "xor"
    traits = frozenset({ir.Pure()})
    lhs: ir.SSAValue = info.argument(types.Bool)
    rhs: ir.SSAValue = info.argument(types.Bool)
    result: ir.ResultValue = info.result(types.Bool)


@statement(dialect=dialect)
class Or(ir.Statement):
    name = "or"
    traits = frozenset({ir.Pure()})
    lhs: ir.SSAValue = info.argument(types.Bool)
    rhs: ir.SSAValue = info.argument(types.Bool)
    result: ir.ResultValue = info.result(types.Bool)


@statement(dialect=dialect)
class Not(ir.Statement):
    name = "not"
    traits = frozenset({ir.Pure()})
    value: ir.SSAValue = info.argument(types.Bool)
    result: ir.ResultValue = info.result(types.Bool)

_BINARY = {ast.BitAnd: And, ast.BitXor: Xor, ast.BitOr: Or}
_BOOLOP = {ast.And: And, ast.Or: Or}


@dialect.register
class Lowering(lowering.FromPythonAST):

    def lower_BinOp(self, state: lowering.State, node: ast.BinOp) -> lowering.Result:
        stmt = _BINARY.get(type(node.op))
        if stmt is None:
            raise lowering.BuildError(f"xag kernels only support & ^ |, got {node.op}")
        lhs = state.lower(node.left).expect_one()
        rhs = state.lower(node.right).expect_one()
        return state.current_frame.push(stmt(lhs, rhs))

    def lower_BoolOp(self, state: lowering.State, node: ast.BoolOp) -> lowering.Result:
        # `a and b and c` -> and(and(a, b), c); same for `or`
        stmt = _BOOLOP[type(node.op)]
        acc = state.lower(node.values[0]).expect_one()
        for value in node.values[1:]:
            rhs = state.lower(value).expect_one()
            acc = state.current_frame.push(stmt(acc, rhs)).result
        return acc

    def lower_UnaryOp(self, state: lowering.State, node: ast.UnaryOp) -> lowering.Result:
        if not isinstance(node.op, (ast.Invert, ast.Not)):
            raise lowering.BuildError(f"xag kernels only support ~ / not, got {node.op}")
        value = state.lower(node.operand).expect_one()
        return state.current_frame.push(Not(value))

@dialect.register
class Concrete(MethodTable):

    @impl(And)
    def and_(self, interp: Interpreter, frame: Frame, stmt: And):
        return (bool(frame.get(stmt.lhs)) and bool(frame.get(stmt.rhs)),)

    @impl(Xor)
    def xor(self, interp: Interpreter, frame: Frame, stmt: Xor):
        return (bool(frame.get(stmt.lhs)) != bool(frame.get(stmt.rhs)),)

    @impl(Or)
    def or_(self, interp: Interpreter, frame: Frame, stmt: Or):
        return (bool(frame.get(stmt.lhs)) or bool(frame.get(stmt.rhs)),)

    @impl(Not)
    def not_(self, interp: Interpreter, frame: Frame, stmt: Not):
        return (not frame.get(stmt.value),)


# the language: func + assignments + constants + tuples + xag 


@ir.dialect_group(
    [
        func,
        ssacfg,  # how to execute a function body (SSA CFG regions)
        func_lowering.func,
        func_lowering.call,
        py.base,
        py.constant,
        py.assign,
        py.tuple,  # `return y0, y1` for multi-output oracles
        dialect,
    ]
)
def xag_kernel(self):
    def run_pass(mt):  # no automatic passes: the demo runs them explicitly
        return mt

    return run_pass
