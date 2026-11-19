# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent brine densities from PHREEQC Pitzer molar volumes, for tests."""

from __future__ import annotations

import csv
import io

from .composition import Composition
from .phreeqc import Phreeqc

COLUMNS = ["region", "temperature_c", "pressure_bar", "factor", "salt_mass_fraction", "density"]


def density_rows(
    phreeqc: Phreeqc,
    region: int,
    composition: Composition,
    temperatures_c: list[float],
    pressures_bar: list[float],
    factors: list[float],
) -> list[dict]:
    rows = []
    for factor in factors:
        brine = composition.scaled(factor)
        w = brine.salt_mass_fraction()
        for t in temperatures_c:
            for p in pressures_bar:
                rho = phreeqc.state(brine, t, p, []).density
                rows.append(dict(zip(COLUMNS, [region, t, p, factor, w, rho])))
    return rows


def to_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: f"{v:.8g}" if isinstance(v, float) else v for k, v in row.items()})
    return buffer.getvalue()
