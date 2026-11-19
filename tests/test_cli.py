# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from brine_tables.cli import main
from brine_tables.units import FIELD

DECK = """RUNSPEC
{units}
PROPS
SALINITC
  1.0 0 0 0 1.0 /
  2.0 0 0 0.5 3.0 /
ROCK
  50 4E-5 /
"""


def write_deck(tmp_path, units):
    path = tmp_path / "TEST.DATA"
    path.write_text(DECK.format(units=units))
    return path


def table_rows(text):
    body = text.split("SALTSOLT\n", 1)[1]
    return [
        line.split("--")[0].split() for line in body.splitlines() if line.split("--")[0].strip()
    ]


def test_saltsolt_two_regions(tmp_path, capsys):
    deck = write_deck(tmp_path, "METRIC")
    main(
        [
            "saltsolt",
            str(deck),
            "--temperatures",
            "20:80:30",
            "--pressure",
            "100",
            "--reference-density",
            "1040,1100",
            "--smax",
            "1.1",
        ]
    )
    rows = table_rows(capsys.readouterr().out)
    assert len(rows) == 6
    assert sum(r[-1] == "/" for r in rows) == 2
    assert [float(r[0]) for r in rows[:3]] == [20.0, 50.0, 80.0]
    assert all(float(r[2]) == 1.1 for r in rows)
    # Solubility rises with temperature for these chloride brines
    assert float(rows[0][1]) < float(rows[2][1])


def test_field_units(tmp_path, capsys):
    metric = write_deck(tmp_path, "METRIC")
    main(
        [
            "saltsolt",
            str(metric),
            "--regions",
            "1",
            "--temperatures",
            "25",
            "--pressure",
            "1.01325",
            "--reference-density",
            "1040",
        ]
    )
    c_metric = float(table_rows(capsys.readouterr().out)[0][1])

    field = write_deck(tmp_path, "FIELD")
    main(
        [
            "saltsolt",
            str(field),
            "--regions",
            "1",
            "--temperatures",
            "77",
            "--pressure",
            "14.696",
            "--reference-density",
            "1040",
        ]
    )
    c_field = float(table_rows(capsys.readouterr().out)[0][1])
    assert c_field == pytest.approx(FIELD.from_kg_per_m3(c_metric), rel=1e-4)


def test_density_reference(tmp_path, capsys):
    deck = write_deck(tmp_path, "METRIC")
    main(["density", str(deck), "--regions", "1", "--temperatures", "25", "--pressures", "1.01325"])
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("region,temperature_c")
    # 1 mol/kg NaCl at 25 C: 1036.2 kg/m3 measured
    assert float(lines[1].split(",")[-1]) == pytest.approx(1036.2, rel=5e-4)


def test_rejects_low_smax(tmp_path):
    deck = write_deck(tmp_path, "METRIC")
    with pytest.raises(SystemExit):
        main(["saltsolt", str(deck), "--temperatures", "25", "--pressure", "1", "--smax", "0.9"])
