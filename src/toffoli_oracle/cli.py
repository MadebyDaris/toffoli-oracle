"""Command-line entry point. Only ``stats`` exists today; ``compile`` arrives with emit/ and verify/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .formats.verilog import read_verilog
from .report import Hardware, ResourceReport, lower_bound


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="toffoli-oracle")
    sub = parser.add_subparsers(dest="command", required=True)

    stats = sub.add_parser("stats", help="XAG cost lower bound (ANDs, AND depth) and runtime model")
    stats.add_argument("files", nargs="+", type=Path, help="XAG Verilog written by mockturtle")
    stats.add_argument("--factories", type=int, default=1)
    stats.add_argument("--t-factory", type=float, default=10e-6, help="seconds per Toffoli state per factory")
    stats.add_argument("--t-reaction", type=float, default=1e-6, help="seconds per sequential Toffoli layer")
    stats.add_argument("--json", action="store_true", help="print one resource report per file")

    args = parser.parse_args(argv)
    hw = Hardware(args.factories, args.t_factory, args.t_reaction)

    if not args.json:
        print(f"{'oracle':<16} {'in':>4} {'out':>4} {'ANDs':>6} {'XORs':>6} {'AND-depth':>9} {'runtime':>10}")
    for path in args.files:
        xag = read_verilog(path)
        point = lower_bound(xag)
        if args.json:
            report = ResourceReport(
                oracle=path.stem,
                inputs=xag.num_inputs,
                outputs=len(xag.outputs),
                chosen=point,
                assumptions={"uncompute": "measurement", "source": "xag lower bound", **vars(hw)},
            )
            print(report.to_json())
        else:
            print(
                f"{path.stem:<16} {xag.num_inputs:>4} {len(xag.outputs):>4} {point.toffoli_count:>6} "
                f"{point.cnot_count:>6} {point.toffoli_depth:>9} {point.runtime_s(hw) * 1e6:>8.1f}us"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
