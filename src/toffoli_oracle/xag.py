"""XOR-AND graphs (XAGs): the interchange format between mockturtle and the quantum back end.

Signals are AIGER-style literals: ``2 * node + complemented``. Node 0 is constant false,
nodes ``1..num_inputs`` are primary inputs, every later node is a 2-input AND or XOR gate.

Simulation is bit-parallel over Python ints: input ``i`` is the truth table whose bit ``x`` is
bit ``i`` of the assignment ``x``, so one pass over the gates evaluates all ``2**n`` inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Op(Enum):
    AND = "&"
    XOR = "^"


@dataclass(frozen=True)
class Gate:
    op: Op
    a: int  # literal
    b: int  # literal


@dataclass
class Xag:
    num_inputs: int = 0
    gates: list[Gate] = field(default_factory=list)  # gate k is node num_inputs + 1 + k
    outputs: list[int] = field(default_factory=list)  # literals
    input_names: list[str] = field(default_factory=list)
    output_names: list[str] = field(default_factory=list)

    # construction

    def add_input(self, name: str | None = None) -> int:
        if self.gates:
            raise ValueError("inputs must be created before gates")
        self.num_inputs += 1
        self.input_names.append(name or f"x{self.num_inputs - 1}")
        return 2 * self.num_inputs

    def add_and(self, a: int, b: int) -> int:
        return self._add(Op.AND, a, b)

    def add_xor(self, a: int, b: int) -> int:
        return self._add(Op.XOR, a, b)

    def add_output(self, lit: int, name: str | None = None) -> None:
        self.outputs.append(lit)
        self.output_names.append(name or f"y{len(self.outputs) - 1}")

    def _add(self, op: Op, a: int, b: int) -> int:
        self.gates.append(Gate(op, a, b))
        return 2 * (self.num_inputs + len(self.gates))

    # properties

    @property
    def num_ands(self) -> int:
        """Multiplicative complexity of this network = Toffoli count with measurement-based uncompute."""
        return sum(g.op is Op.AND for g in self.gates)

    @property
    def num_xors(self) -> int:
        return sum(g.op is Op.XOR for g in self.gates)

    def and_depth(self) -> int:
        """Multiplicative depth: most ANDs on any input-to-output path (~ Toffoli depth)."""
        depth = [0] * (self.num_inputs + 1 + len(self.gates))
        for k, g in enumerate(self.gates):
            d = max(depth[g.a >> 1], depth[g.b >> 1])
            depth[self.num_inputs + 1 + k] = d + (g.op is Op.AND)
        return max((depth[o >> 1] for o in self.outputs), default=0)

    # simulation

    def simulate(self) -> list[int]:
        """Truth table of every output (bit ``x`` = value on input assignment ``x``)."""
        n = self.num_inputs
        if n > 24:
            raise ValueError(f"exhaustive simulation of {n} inputs is too large; use evaluate()")
        mask = (1 << (1 << n)) - 1
        inputs = [_projection(i, n) for i in range(n)]
        return self._run(inputs, mask)

    def evaluate(self, assignment: int) -> int:
        """Outputs (bit ``j`` = output ``j``) for one input assignment (bit ``i`` = input ``i``)."""
        values = self._run([(assignment >> i) & 1 for i in range(self.num_inputs)], 1)
        return sum(v << j for j, v in enumerate(values))

    def _run(self, inputs: list[int], mask: int) -> list[int]:
        values = [0, *inputs]

        def lit(literal: int) -> int:
            v = values[literal >> 1]
            return v ^ mask if literal & 1 else v

        for g in self.gates:
            a, b = lit(g.a), lit(g.b)
            values.append(a & b if g.op is Op.AND else a ^ b)
        return [lit(o) for o in self.outputs]


def _projection(i: int, n: int) -> int:
    """Truth table of input ``i`` over ``n`` variables, as an int with ``2**n`` bits."""
    block = 1 << i
    pattern = ((1 << block) - 1) << block  # 'block' zeros then 'block' ones
    period = 2 * block
    tt = 0
    for start in range(0, 1 << n, period):
        tt |= pattern << start
    return tt
