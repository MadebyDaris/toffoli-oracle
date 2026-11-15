from pathlib import Path

from toffoli_oracle.cli import main as cli_main

DATA = Path(__file__).parent / "data"


def test_stats_json(capsys):
    assert cli_main(["stats", str(DATA / "adder_4.v"), "--json"]) == 0
    assert '"toffoli_count": 4' in capsys.readouterr().out
