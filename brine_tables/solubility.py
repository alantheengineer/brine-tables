# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Total salt solubility at fixed ion ratios.

The brine is concentrated or diluted at fixed ion ratios until the first of the controlling
minerals reaches saturation. The salt mass fraction at that point is the total salt
solubility the BRINE precipitation model uses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .composition import Composition
from .phreeqc import ABSENT, Phreeqc

# Bulk salts that precipitate as SALT in the BRINE model. Sulfates, carbonates and borates
# are scale minerals; they are reported but do not set the solubility unless asked.
DEFAULT_MINERALS = ["Halite", "Sylvite", "Carnallite", "Bischofite"]
WATCH_MINERALS = [
    "Anhydrite",
    "Gypsum",
    "Glauberite",
    "Thenardite",
    "Mirabilite",
    "Kieserite",
    "Epsomite",
    "Polyhalite",
    "Kainite",
    "Celestite",
    "Calcite",
    "Borax",
]


@dataclass(frozen=True)
class Saturation:
    temperature_c: float
    factor: float  # molality multiplier on the given composition
    salt_mass_fraction: float
    mineral: str  # the controlling mineral that saturates first
    density: float  # PHREEQC density of the saturated brine, kg/m3
    supersaturated: dict[str, float]  # watched minerals already above saturation


def _max_si(si: dict[str, float], minerals: list[str]) -> tuple[float, str]:
    present = [(si[m], m) for m in minerals if si[m] > ABSENT]
    if not present:
        raise ValueError(f"None of {minerals} can form from this brine")
    return max(present)


def saturation(
    phreeqc: Phreeqc,
    composition: Composition,
    temperature_c: float,
    pressure_bar: float,
    minerals: list[str] | None = None,
    tolerance: float = 1e-7,
) -> Saturation:
    """Find where the brine, at its own ion ratios, first saturates a controlling mineral."""
    minerals = minerals or DEFAULT_MINERALS
    watch = [m for m in WATCH_MINERALS if m not in minerals]

    def si_at(factor: float) -> float:
        state = phreeqc.state(composition.scaled(factor), temperature_c, pressure_bar, minerals)
        return _max_si(state.saturation_index, minerals)[0]

    # Bracket the root in log(factor); saturation index rises with concentration
    lo, hi = 1.0, 1.0
    if si_at(1.0) > 0.0:
        while si_at(lo) > 0.0:
            lo *= 0.5
            if lo < 1e-6:
                raise ValueError("Brine stays supersaturated at any dilution")
    else:
        while si_at(hi) < 0.0:
            hi *= 1.5
            if hi > 1e3:
                raise ValueError("No controlling mineral saturates within 1000x concentration")

    a, b = math.log(lo), math.log(hi)
    while b - a > tolerance:
        mid = 0.5 * (a + b)
        if si_at(math.exp(mid)) < 0.0:
            a = mid
        else:
            b = mid
    factor = math.exp(0.5 * (a + b))

    saturated = composition.scaled(factor)
    state = phreeqc.state(saturated, temperature_c, pressure_bar, minerals + watch)
    _, mineral = _max_si(state.saturation_index, minerals)
    over = {m: state.saturation_index[m] for m in watch if state.saturation_index[m] > 0.0}
    return Saturation(
        temperature_c=temperature_c,
        factor=factor,
        salt_mass_fraction=saturated.salt_mass_fraction(),
        mineral=mineral,
        density=state.density,
        supersaturated=over,
    )
