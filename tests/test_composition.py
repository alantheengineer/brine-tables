# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from brine_tables.composition import deck_units, parse_ions, read_salinitc

DECK = """RUNSPEC
FIELD
PROPS
SALINITC
-- NA  K    CA  MG  CL  SO4 LI  SR  BR  HCO3 CO3 B
   2.0 0.5  0   0   2.5 /
   1.0 2*0.1 0  1.3  7* /   -- second region
ROCK
  50 4E-5 /
"""


@pytest.fixture
def deck(tmp_path):
    path = tmp_path / "TEST.DATA"
    path.write_text(DECK)
    return path


def test_reads_every_region(deck):
    regions = read_salinitc(deck)
    assert len(regions) == 2
    assert regions[0].molality["NA"] == 2.0
    assert regions[0].molality["CL"] == 2.5
    assert regions[0].molality["B"] == 0.0
    # 2*0.1 fills K and CA; MG is 0 and CL 1.3; the rest default
    assert regions[1].molality["K"] == 0.1
    assert regions[1].molality["CA"] == 0.1
    assert regions[1].molality["CL"] == 1.3


def test_deck_units(deck):
    assert deck_units(deck) == "FIELD"


def test_salt_mass_fraction_and_charge():
    nacl = parse_ions("NA=1 CL=1")
    m = 22.9898e-3 + 35.45e-3
    assert nacl.salt_mass_fraction() == pytest.approx(m / (1.0 + m), rel=1e-12)
    assert nacl.charge_imbalance() == 0.0
    assert parse_ions("NA=1 CL=0.5").charge_imbalance() == pytest.approx(1.0 / 3.0)


def test_scaling_keeps_ratios():
    brine = parse_ions("NA=2 CA=0.5 CL=3").scaled(2.0)
    assert brine.molality["NA"] == 4.0
    assert brine.molality["CA"] == 1.0


def test_bad_ion_name():
    with pytest.raises(ValueError):
        parse_ions("XX=1")
