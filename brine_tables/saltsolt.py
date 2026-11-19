# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
"""SALTSOLT tables from PHREEQC solubilities."""

from __future__ import annotations

from dataclasses import dataclass

from .composition import Composition
from .phreeqc import Phreeqc
from .solubility import Saturation, saturation
from .units import Units

STANDARD_TEMPERATURE_C = 15.56
STANDARD_PRESSURE_BAR = 1.01325


@dataclass(frozen=True)
class RegionTable:
    region: int
    reference_density: float  # kg/m3
    density_source: str
    rows: list[Saturation]


def phreeqc_reference_density(phreeqc: Phreeqc, composition: Composition) -> float:
    """PHREEQC density of the brine at standard conditions, kg/m3."""
    state = phreeqc.state(composition, STANDARD_TEMPERATURE_C, STANDARD_PRESSURE_BAR, [])
    return state.density


def region_table(
    phreeqc: Phreeqc,
    region: int,
    composition: Composition,
    temperatures_c: list[float],
    pressure_bar: float,
    minerals: list[str] | None,
    reference_density: float | None,
) -> RegionTable:
    if reference_density is None:
        reference_density = phreeqc_reference_density(phreeqc, composition)
        source = "PHREEQC at standard conditions; use the value flow logs for an exact match"
    else:
        source = "given"
    rows = [saturation(phreeqc, composition, t, pressure_bar, minerals) for t in temperatures_c]
    return RegionTable(region, reference_density, source, rows)


def format_saltsolt(
    tables: list[RegionTable],
    units: Units,
    temperatures: list[float],
    pressure: float,
    smax: float,
    database: str,
) -> str:
    """SALTSOLT keyword text: one table per PVT region, in deck units."""
    out = [
        f"-- SALTSOLT from brine-tables: PHREEQC with {database}",
        f"-- Ion ratios from SALINITC, at {pressure:g} {units.pressure}",
    ]
    for table in tables:
        out.append(
            f"-- Region {table.region}: reference density {table.reference_density:.2f} kg/m3 "
            f"({table.density_source})"
        )
    out.append("SALTSOLT")
    for table in tables:
        out.append(
            f"-- Region {table.region}: T ({units.temperature})  "
            f"solubility ({units.concentration})  S_max"
        )
        for k, (t, row) in enumerate(zip(temperatures, table.rows)):
            concentration = units.from_kg_per_m3(row.salt_mass_fraction * table.reference_density)
            end = " /" if k == len(table.rows) - 1 else ""
            note = f"{row.mineral}, w {row.salt_mass_fraction:.4f}"
            if row.supersaturated:
                over = ", ".join(f"{m} SI {si:.2f}" for m, si in row.supersaturated.items())
                note += f"; above saturation: {over}"
            out.append(f"  {t:8.2f}  {concentration:10.3f}  {smax:5.3f}{end}  -- {note}")
    return "\n".join(out) + "\n"
