# Copyright 2026 Dr Alan Tominey.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line: SALTSOLT tables and reference densities from a deck's SALINITC."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import reference, saltsolt
from .composition import deck_units, read_salinitc
from .phreeqc import Phreeqc
from .units import units_named


def _grid(text: str) -> list[float]:
    """'20:150:10' gives 20, 30, ..., 150; '20,60,90' gives those values."""
    if ":" in text:
        start, stop, step = (float(x) for x in text.split(":"))
        if step <= 0.0 or stop < start:
            raise argparse.ArgumentTypeError(f"Bad range '{text}'")
        count = round((stop - start) / step)
        return [start + k * step for k in range(count + 1)]
    return [float(x) for x in text.split(",")]


def _regions(text: str, available: int) -> list[int]:
    if text == "all":
        return list(range(1, available + 1))
    regions = [int(x) for x in text.split(",")]
    for r in regions:
        if not 1 <= r <= available:
            raise SystemExit(f"Region {r} not in the deck's {available} SALINITC records")
    return regions


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("deck", type=Path, help="deck with SALINITC")
    parser.add_argument("--regions", default="all", help="PVT regions, e.g. 1,2 (default all)")
    parser.add_argument(
        "--temperatures",
        type=_grid,
        required=True,
        help="deck temperature units: start:stop:step or a list",
    )
    parser.add_argument("--database", type=Path, help="PHREEQC database (default pitzer.dat)")
    parser.add_argument("-o", "--output", type=Path, help="write here instead of stdout")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brine-tables", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    table = sub.add_parser("saltsolt", help="SALTSOLT keyword for the deck's regions")
    _common(table)
    table.add_argument("--pressure", type=float, required=True, help="deck pressure units")
    table.add_argument("--smax", type=float, default=1.0, help="S_max column (default 1)")
    table.add_argument(
        "--minerals",
        help="controlling minerals, comma separated (default Halite,Sylvite,Carnallite,Bischofite)",
    )
    table.add_argument(
        "--reference-density",
        help="brine surface density per region, kg/m3, as flow logs it; comma separated",
    )

    dens = sub.add_parser("density", help="reference densities as CSV, SI units")
    _common(dens)
    dens.add_argument("--pressures", type=_grid, required=True, help="deck pressure units")
    dens.add_argument(
        "--factors",
        type=_grid,
        default=[1.0],
        help="salt multipliers on the SALINITC molalities (default 1)",
    )

    args = parser.parse_args(argv)
    units = units_named(deck_units(args.deck))
    compositions = read_salinitc(args.deck)
    regions = _regions(args.regions, len(compositions))
    for r in regions:
        imbalance = compositions[r - 1].charge_imbalance()
        if abs(imbalance) > 0.01:
            print(
                f"Warning: SALINITC region {r} is off charge balance by {100 * imbalance:.1f}%",
                file=sys.stderr,
            )
    temperatures_c = [units.to_celsius(t) for t in args.temperatures]
    phreeqc = Phreeqc(args.database)

    if args.command == "saltsolt":
        if args.smax < 1.0:
            raise SystemExit("S_max must be at least 1")
        densities = [None] * len(regions)
        if args.reference_density:
            densities = [float(x) for x in args.reference_density.split(",")]
            if len(densities) != len(regions):
                raise SystemExit("Give one reference density per region")
        minerals = args.minerals.split(",") if args.minerals else None
        tables = [
            saltsolt.region_table(
                phreeqc,
                r,
                compositions[r - 1],
                temperatures_c,
                units.to_bar(args.pressure),
                minerals,
                rho,
            )
            for r, rho in zip(regions, densities)
        ]
        text = saltsolt.format_saltsolt(
            tables, units, args.temperatures, args.pressure, args.smax, phreeqc.database.name
        )
    else:
        pressures_bar = [units.to_bar(p) for p in args.pressures]
        rows = []
        for r in regions:
            rows += reference.density_rows(
                phreeqc, r, compositions[r - 1], temperatures_c, pressures_bar, args.factors
            )
        text = reference.to_csv(rows)

    if args.output:
        args.output.write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
