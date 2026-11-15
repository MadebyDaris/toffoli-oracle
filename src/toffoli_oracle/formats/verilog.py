"""Read the gate-level Verilog that mockturtle's ``write_verilog`` produces for an XAG.

Supported subset (exactly what mockturtle writes)::

    module top( x0 , x1 , y0 );
      input x0 , x1 ;
      output y0 ;
      wire n3 ;
      assign n3 = ~x0 & x1 ;
      assign y0 = ~n3 ;
    endmodule

Right-hand sides are ``[~]a & [~]b``, ``[~]a ^ [~]b``, or a single ``[~]a``; operands are names
or the constants ``1'b0`` / ``1'b1``. Anything else raises ``ValueError``.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..xag import Xag

_OPERAND = r"(~?)\s*([A-Za-z_][\w\[\]]*|1'b[01])"
_BINARY = re.compile(rf"^{_OPERAND}\s*([&^])\s*{_OPERAND}$")
_UNARY = re.compile(rf"^{_OPERAND}$")


def read_verilog(source: str | Path) -> Xag:
    text = Path(source).read_text() if _looks_like_path(source) else str(source)
    text = re.sub(r"//.*", "", text)
    statements = [s.strip() for s in text.split(";") if s.strip()]

    inputs: list[str] = []
    outputs: list[str] = []
    assigns: list[tuple[str, str]] = []
    for stmt in statements:
        keyword, _, rest = stmt.partition(" ")
        if keyword == "input":
            inputs += _names(rest)
        elif keyword == "output":
            outputs += _names(rest)
        elif keyword == "assign":
            lhs, _, rhs = rest.partition("=")
            assigns.append((lhs.strip(), rhs.strip()))
        elif keyword in ("module", "wire", "endmodule"):
            continue
        else:
            raise ValueError(f"unsupported Verilog statement: {stmt!r}")

    xag = Xag()
    signal: dict[str, int] = {"1'b0": 0, "1'b1": 1}
    for name in inputs:
        signal[name] = xag.add_input(name)

    def operand(neg: str, name: str) -> int:
        if name not in signal:
            raise ValueError(f"{name!r} used before it is assigned (only topologically sorted input is supported)")
        return signal[name] ^ (neg == "~")

    for lhs, rhs in assigns:
        if m := _BINARY.match(rhs):
            a, b = operand(m[1], m[2]), operand(m[4], m[5])
            signal[lhs] = xag.add_and(a, b) if m[3] == "&" else xag.add_xor(a, b)
        elif m := _UNARY.match(rhs):
            signal[lhs] = operand(m[1], m[2])
        else:
            raise ValueError(f"unsupported expression for {lhs}: {rhs!r}")

    for name in outputs:
        if name not in signal:
            raise ValueError(f"output {name!r} is never assigned")
        xag.add_output(signal[name], name)
    return xag


def _names(rest: str) -> list[str]:
    return [n.strip() for n in rest.split(",") if n.strip()]


def _looks_like_path(source: str | Path) -> bool:
    return isinstance(source, Path) or ("\n" not in source and source.endswith(".v"))
