"""Kirin rewrite rules over the xag dialect."""

from __future__ import annotations

from dataclasses import dataclass

from kirin import ir
from kirin.rewrite import Walk, Fixpoint
from kirin.rewrite.abc import RewriteRule, RewriteResult

from xag_dialect import Or, And, Not


@dataclass
class EliminateOr(RewriteRule):
    """De Morgan: a | b  ->  ~(~a & ~b). An XAG has no OR gate, and NOT is free."""

    def rewrite_Statement(self, node: ir.Statement) -> RewriteResult:
        if not isinstance(node, Or):
            return RewriteResult()
        not_a = Not(node.lhs)
        not_b = Not(node.rhs)
        both = And(not_a.result, not_b.result)
        not_a.insert_before(node)
        not_b.insert_before(node)
        both.insert_before(node)
        node.replace_by(Not(both.result))
        return RewriteResult(has_done_something=True)


@dataclass
class DoubleNegation(RewriteRule):
    """~~a -> a"""

    def rewrite_Statement(self, node: ir.Statement) -> RewriteResult:
        if not isinstance(node, Not):
            return RewriteResult()
        inner = node.value.owner
        if not isinstance(inner, Not):
            return RewriteResult()
        node.result.replace_by(inner.value)
        node.delete()
        if not inner.result.uses:
            inner.delete()
        return RewriteResult(has_done_something=True)


def to_and_xor_form(mt: ir.Method) -> ir.Method:
    """Rewrite in place until only and / xor / not remain."""
    Fixpoint(Walk(EliminateOr())).rewrite(mt.code)
    Fixpoint(Walk(DoubleNegation())).rewrite(mt.code)
    return mt
