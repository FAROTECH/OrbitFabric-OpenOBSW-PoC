# Stage 7.6 — External assembled-SRDB build consumption

## Purpose

Stage 7.6 moves the reference integration from target-native in-memory composition to native OpenOBSW build consumption without copying or patching generated contribution files into the OpenOBSW checkout.

The intended chain is:

```text
OrbitFabric Integration Input Set
        ↓
Projection Profile / Adapter
        ↓
obsw-srdb additive contribution
        ↓
target-owned SRDB composition
        ↓
target-owned complete SRDB materialization
        ↓
external SRDB_DATA_DIR
        ↓
OpenOBSW native CMake srdb_codegen target
        ├── srdb_generated.h
        └── mission.xtce
```

## Ownership

`obsw-srdb` owns:

- additive composition semantics;
- complete SRDB materialization;
- loader validation and round-trip semantics;
- C/XTCE code generation.

OpenOBSW CMake owns selection of the complete SRDB directory used by native code generation.

The OrbitFabric Adapter remains responsible only for producing the additive target-native contribution established in Stage 7.4.

## Target change

The target-side Stage 7.6 reference adds:

```text
SRDBMaterializer.write(srdb, output_dir)
```

which writes the standard complete SRDB contract files:

```text
spacecraft.yaml
parameters.yaml
telecommands.yaml
hk_sets.yaml
events.yaml
```

and round-trips the result through `SRDBLoader` before returning successfully.

OpenOBSW `srdb/CMakeLists.txt` keeps the current default:

```text
<checkout>/srdb/data
```

but exposes `SRDB_DATA_DIR` as a CMake cache path so an explicitly assembled complete SRDB can be selected:

```text
-DSRDB_DATA_DIR=<external-complete-srdb-dir>
```

The five required complete-SRDB files are checked during configure.

## Acceptance

`tools/validate_stage7_6_external_build_consumption.py`:

1. requires the exact Stage 7.6 OpenOBSW reference commit;
2. fingerprints the original `srdb/data` contract files;
3. loads the Stage 7.4 contribution bundle;
4. composes it through the target-owned Stage 7.5 API;
5. materializes a complete SRDB through `SRDBMaterializer`;
6. reloads the materialized directory with `SRDBLoader`;
7. configures OpenOBSW with the external directory via `SRDB_DATA_DIR`;
8. builds the native `srdb_codegen` CMake target;
9. verifies the generated C header contains the contributed parameter, event and HK records while preserving `are_you_alive`;
10. compiles the CMake-produced header with strict C11 warnings-as-errors;
11. verifies the generated XTCE contains the contributed parameter and HK container;
12. proves the checkout's original `srdb/data` files stayed byte-identical.

## Explicit non-goals

This stage does not:

- build or run the OpenOBSW host simulator;
- execute OpenSVF;
- introduce runtime discovery or orchestration;
- modify the generic `orbitfabric.adapter_cli.v0` context;
- patch the OpenOBSW source SRDB;
- claim full runtime integration.

It establishes the narrower target build-input boundary required before runtime integration can be approached cleanly.
