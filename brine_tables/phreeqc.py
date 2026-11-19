# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
"""PHREEQC runs for one brine state: saturation indices and density."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import phreeqpython

from .composition import Composition

# PHREEQC element for each SALINITC ion; carbonate enters as total C(4)
_ELEMENT = {
    "NA": "Na",
    "K": "K",
    "CA": "Ca",
    "MG": "Mg",
    "CL": "Cl",
    "SO4": "S(6)",
    "LI": "Li",
    "SR": "Sr",
    "BR": "Br",
    "B": "B",
}

ATM_PER_BAR = 1.0 / 1.01325

# PHREEQC gives -99.99 as the saturation index of a phase with an absent element
ABSENT = -99.0


def bundled_database(name: str = "pitzer.dat") -> Path:
    return Path(os.path.dirname(phreeqpython.__file__)) / "database" / name


@dataclass(frozen=True)
class State:
    saturation_index: dict[str, float]
    density: float  # kg/m3


class Phreeqc:
    """One PHREEQC instance with its database loaded once."""

    def __init__(self, database: Path | None = None):
        self.database = Path(database) if database else bundled_database()
        self._ip = phreeqpython.PhreeqPython(database=str(self.database)).ip

    def state(
        self,
        composition: Composition,
        temperature_c: float,
        pressure_bar: float,
        minerals: list[str],
    ) -> State:
        lines = [
            "SOLUTION 1",
            f"  temp {temperature_c:.6g}",
            f"  pressure {pressure_bar * ATM_PER_BAR:.6g}",
            "  units mol/kgw",
            "  pH 7",
        ]
        m = composition.molality
        for ion, element in _ELEMENT.items():
            if m.get(ion, 0.0) > 0.0:
                lines.append(f"  {element} {m[ion]:.10g}")
        carbonate = m.get("HCO3", 0.0) + m.get("CO3", 0.0)
        if carbonate > 0.0:
            lines.append(f"  C(4) {carbonate:.10g}")

        heads = " ".join(f"si_{k}" for k in range(len(minerals)))
        punch = ", ".join(f'SI("{name}")' for name in minerals)
        lines += [
            "USER_PUNCH",
            f"  -headings rho {heads}",
            f"  10 PUNCH RHO{', ' + punch if punch else ''}",
            "SELECTED_OUTPUT",
            "  -reset false",
            "  -user_punch true",
            "END",
        ]
        self._ip.run_string("\n".join(lines))
        rows = self._ip.get_selected_output_array()
        if len(rows) < 2:
            raise RuntimeError(f"PHREEQC gave no output:\n{self._ip.get_error_string()}")
        values = rows[-1]
        return State(
            saturation_index={name: float(v) for name, v in zip(minerals, values[1:])},
            density=1000.0 * float(values[0]),
        )
