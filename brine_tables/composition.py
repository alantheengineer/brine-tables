# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ion compositions as SALINITC gives them, in mol/kg water."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# SALINITC item order
IONS = ("NA", "K", "CA", "MG", "CL", "SO4", "LI", "SR", "BR", "HCO3", "CO3", "B")

# Molar masses in kg/mol, as opm-common uses them; boron counts as B(OH)3
MOLAR_MASS = {
    "NA": 22.9898e-3,
    "K": 39.0983e-3,
    "CA": 40.078e-3,
    "MG": 24.305e-3,
    "CL": 35.45e-3,
    "SO4": 96.06e-3,
    "LI": 6.94e-3,
    "SR": 87.62e-3,
    "BR": 79.904e-3,
    "HCO3": 61.016e-3,
    "CO3": 60.008e-3,
    "B": 61.83e-3,
}

CHARGE = {
    "NA": 1,
    "K": 1,
    "CA": 2,
    "MG": 2,
    "CL": -1,
    "SO4": -2,
    "LI": 1,
    "SR": 2,
    "BR": -1,
    "HCO3": -1,
    "CO3": -2,
    "B": 0,
}


@dataclass(frozen=True)
class Composition:
    """Ion molalities in mol/kg water."""

    molality: dict[str, float]

    def scaled(self, factor: float) -> Composition:
        return Composition({ion: factor * m for ion, m in self.molality.items()})

    def salt_mass_fraction(self) -> float:
        """Dissolved salt over brine mass, with ion masses as opm-common counts them."""
        salt = sum(m * MOLAR_MASS[ion] for ion, m in self.molality.items())
        return salt / (1.0 + salt)

    def charge_imbalance(self) -> float:
        """Net charge over total charge, 0 for a balanced brine."""
        net = sum(m * CHARGE[ion] for ion, m in self.molality.items())
        total = sum(m * abs(CHARGE[ion]) for ion, m in self.molality.items())
        return net / total if total > 0.0 else 0.0


def parse_ions(text: str) -> Composition:
    """Read 'NA=4.0 CL=4.0 ...' into a composition."""
    molality = dict.fromkeys(IONS, 0.0)
    for item in text.replace(",", " ").split():
        name, _, value = item.partition("=")
        name = name.upper()
        if name not in molality or not value:
            raise ValueError(f"Bad ion entry '{item}'; use NAME=molality with NAME in {IONS}")
        molality[name] = float(value)
    return Composition(molality)


def _tokens(record: str) -> list[str]:
    """Expand ECLIPSE repeat counts: '2*0.5' gives two values, '3*' three defaults."""
    out = []
    for token in record.split():
        match = re.fullmatch(r"(\d+)\*(.*)", token)
        if match:
            count, value = int(match.group(1)), match.group(2)
            out.extend([value or "1*"] * count)
        else:
            out.append(token)
    return out


def read_salinitc(deck: Path) -> list[Composition]:
    """Read every SALINITC record of a deck, one per PVT region. Defaulted items are zero."""
    text = Path(deck).read_text(errors="replace")
    lines = [line.split("--", 1)[0] for line in text.splitlines()]
    body = "\n".join(lines)
    keyword = r"^\s*SALINITC\b(.*?)(?=^\s*[A-Z][A-Z0-9_]{1,7}\s*$)"
    match = re.search(keyword, body, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"No SALINITC keyword in {deck}")
    records = [r for r in match.group(1).split("/") if r.strip()]

    compositions = []
    for record in records:
        tokens = _tokens(record)
        if len(tokens) > len(IONS):
            raise ValueError(f"SALINITC record has more than {len(IONS)} items: {record!r}")
        molality = dict.fromkeys(IONS, 0.0)
        for ion, token in zip(IONS, tokens):
            molality[ion] = 0.0 if token == "1*" else float(token)
        compositions.append(Composition(molality))
    return compositions


def deck_units(deck: Path) -> str:
    """METRIC or FIELD, from the RUNSPEC unit keyword."""
    text = Path(deck).read_text(errors="replace")
    for line in text.splitlines():
        word = line.split("--", 1)[0].strip()
        if word in ("METRIC", "FIELD", "LAB", "PVT-M"):
            if word not in ("METRIC", "FIELD"):
                raise ValueError(f"{word} units are not supported")
            return word
    return "METRIC"
