# Geometry

- `cygno_04_v3_ASCII/`: original CYGNO04 geometry; optional.
- `cygno04_v4_ASCII/`: default; updated N66, PMMA, copper, GEM alignment and full-cavity gas; 500 × 800 × 510 mm sensitive envelope per side.

On the updated CYGNO04 branches, select legacy v3 before startup:
```sh
CYGNO_GEOMETRY_PATH=../geometry/cygno_04_v3_ASCII ./CYGNO run.mac
```
Keep all eight required v4 STL files together. Sensitive cuts follow the loaded parts directly. Generation notes: [tools/gas_geometry.txt](tools/gas_geometry.txt).
