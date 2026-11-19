# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from brine_tables.composition import parse_ions
from brine_tables.phreeqc import Phreeqc
from brine_tables.solubility import saturation


@pytest.fixture(scope="module")
def phreeqc():
    return Phreeqc()


# Measured solubilities: NaCl 6.15 mol/kg at 25 C and 6.71 at 100 C; KCl 4.81 at 25 C
@pytest.mark.parametrize(
    "ions, temperature, molality, mineral",
    [
        ("NA=1 CL=1", 25.0, 6.15, "Halite"),
        ("NA=1 CL=1", 100.0, 6.71, "Halite"),
        ("K=1 CL=1", 25.0, 4.81, "Sylvite"),
    ],
)
def test_single_salt(phreeqc, ions, temperature, molality, mineral):
    result = saturation(phreeqc, parse_ions(ions), temperature, 1.01325)
    assert result.mineral == mineral
    assert result.factor == pytest.approx(molality, rel=0.02)


def test_depends_on_ratios_only(phreeqc):
    brine = parse_ions("NA=3 K=0.3 CA=0.4 MG=0.2 CL=4.5")
    a = saturation(phreeqc, brine, 60.0, 100.0)
    b = saturation(phreeqc, brine.scaled(0.25), 60.0, 100.0)
    assert a.salt_mass_fraction == pytest.approx(b.salt_mass_fraction, rel=1e-6)


def test_calcium_lowers_halite_solubility(phreeqc):
    # Na is 1 in both, so the factor is the sodium molality at halite saturation
    nacl = saturation(phreeqc, parse_ions("NA=1 CL=1"), 60.0, 100.0)
    mixed = saturation(phreeqc, parse_ions("NA=1 CA=0.25 CL=1.5"), 60.0, 100.0)
    assert mixed.mineral == "Halite"
    assert mixed.factor < nacl.factor


def test_scale_minerals_are_reported(phreeqc):
    # A Ca-SO4 brine passes gypsum or anhydrite saturation well before halite
    result = saturation(phreeqc, parse_ions("NA=1 CA=0.05 CL=1 SO4=0.05"), 25.0, 1.01325)
    assert result.mineral == "Halite"
    assert {"Gypsum", "Anhydrite"} & set(result.supersaturated)


def test_no_controlling_mineral(phreeqc):
    with pytest.raises(ValueError):
        saturation(phreeqc, parse_ions("MG=1 SO4=1"), 25.0, 1.01325, minerals=["Halite"])
