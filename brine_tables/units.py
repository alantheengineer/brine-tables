# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Deck unit conversions for the columns this tool writes and reads."""

from __future__ import annotations

from dataclasses import dataclass

_LB_PER_STB_PER_KG_PER_M3 = 0.158987294928 / 0.45359237


@dataclass(frozen=True)
class Units:
    name: str
    temperature: str
    pressure: str
    concentration: str

    def to_celsius(self, t: float) -> float:
        return (t - 32.0) * 5.0 / 9.0 if self.name == "FIELD" else t

    def to_bar(self, p: float) -> float:
        return p * 0.0689475729 if self.name == "FIELD" else p

    def from_kg_per_m3(self, c: float) -> float:
        return c * _LB_PER_STB_PER_KG_PER_M3 if self.name == "FIELD" else c


METRIC = Units("METRIC", "C", "bar", "kg/m3")
FIELD = Units("FIELD", "F", "psia", "lb/stb")


def units_named(name: str) -> Units:
    return {"METRIC": METRIC, "FIELD": FIELD}[name]
