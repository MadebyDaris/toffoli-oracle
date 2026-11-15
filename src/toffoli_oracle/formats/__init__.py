"""Readers and writers between toffoli_oracle's IRs and files.

Today: the gate-level Verilog that mockturtle's ``write_verilog`` produces (``read_verilog``).
Later: OpenQASM 3 and Qiskit exporters for emitted circuits.
"""

from .verilog import read_verilog

__all__ = ["read_verilog"]
