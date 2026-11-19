# brine-tables

Offline tables for the SALTMC brine models in OPM Flow.

- `saltsolt` writes the SALTSOLT keyword: total salt solubility against temperature for each
  PVT region's SALINITC brine.
- `density` writes PHREEQC Pitzer densities as CSV, as independent reference values for
  tests of the simulator's density models.

## Install

```
pip install -e .[test]
pytest
```

PHREEQC comes from `phreeqpython`, which bundles IPhreeqc and the `pitzer.dat` database.

## Use

```
brine-tables saltsolt CASE.DATA --temperatures 20:150:10 --pressure 250 \
    --reference-density 1137.36 -o saltsolt.inc

brine-tables density CASE.DATA --temperatures 25,90,150 --pressures 1,250,500 \
    --factors 0.5,1,1.5 -o reference.csv
```

Temperatures and pressures are in the deck's units (METRIC or FIELD). The SALTSOLT table is
written in deck units too. The density CSV is in SI: C, bar and kg/m3.

`--reference-density` is the brine surface density per region, which flow logs at start-up
as `SALTMC region N: brine surface density ... kg/m3`. Give it so the table matches the
simulator exactly. Without it the tool uses the PHREEQC density at standard conditions,
which is usually within 0.1%.

`--smax` sets the S_max column (default 1). `--minerals` changes the minerals that control
the solubility. `--database` selects another PHREEQC database, for example a PhreeSCALE one.

## Method

The SALINITC molalities fix the ion ratios. At each temperature the brine is concentrated
or diluted at those ratios, by bisection on the molality multiplier, until the first
controlling mineral reaches a saturation index of zero. The salt mass fraction w at that
point, counted with the ion molar masses opm-common uses, is the total salt solubility.
SALTSOLT takes it as a concentration, w times the reference density, because the BRINE
salt concentration is salt mass per surface volume of brine.

The default controlling minerals are halite, sylvite, carnallite and bischofite: the bulk
salts the BRINE model precipitates. Sulfates, carbonates and borates are scale minerals
and do not set the solubility by default. Each table row notes the mineral that saturates
first and any scale mineral already above saturation at that point.

## Limits

- `pitzer.dat` has temperature dependence to 200 C (Appelo, 2015). It has no lithium
  minerals, so lithium salts never control the solubility.
- PhreeSCALE databases are not bundled. Pass one with `--database` once obtained.
- PHREEQC viscosity is not used: the bundled database has no viscosity parameters for these
  ions.
- The solubility is for the composition SALINITC gives. In TRACER mode the cell ratios can
  move away from it.

## References

- Parkhurst, D.L. and Appelo, C.A.J., 2013. PHREEQC version 3. USGS Techniques and Methods
  6-A43.
- Appelo, C.A.J., 2015. Principles, caveats and improvements in databases for calculating
  hydrogeochemical reactions in saline waters from 0 to 200 C and 1 to 1000 atm. Appl.
  Geochem. 55, 62-71.
- Lach, A. et al., 2016. Thermal and volumetric properties of complex aqueous electrolyte
  solutions using the Pitzer formalism: the PhreeSCALE code. Comput. Geosci. 92, 58-69.

Copyright 2026 Dr Alan Tominey. Licensed under the GNU General Public License, version 3 or
later; see LICENSE.
