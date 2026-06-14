# Stage 6.7 - SRDB Runtime Environment Probe

## Purpose

Stage 6.7 turns the Stage 6.6 SRDB warning triage into a reproducible local environment check.

The objective is to prove that the known runtime warning is caused by a missing Python package in the OpenSVF virtual environment, not by a failure in the OpenSVF/OpenOBSW runtime path.

## Finding

OpenOBSW already contains an installable Python package for its SRDB layer:

```text
../openobsw/srdb
```

That package exposes the importable module:

```text
obsw_srdb
```

and the Python distribution name:

```text
obsw-srdb
```

OpenSVF checks the installed `obsw-srdb` distribution when the OBC emulator reads the SRDB version emitted by `obsw_sim`.

Without the package installed in the OpenSVF virtual environment, the runtime emits:

```text
obsw-srdb package not installed - cannot verify SRDB version handshake
```

## Local setup

From the PoC repository root:

```bash
../opensvf/.venv/bin/python -m pip install -e ../openobsw/srdb
```

Expected import probe:

```text
obsw_srdb importable
obsw-srdb version available
svf importable
```

## Runtime validation

After installing the package into the OpenSVF virtual environment, the Stage 6.5 HK runtime campaign remains green:

```text
PASS:          1
FAIL:          0
ERROR:         0
INCONCLUSIVE:  0
Pass rate: 100.0%
```

The campaign output should not contain:

```text
obsw-srdb package not installed
SRDB VERSION MISMATCH
```

The runtime may or may not print the positive `SRDB version handshake OK` line depending on logging level. Absence of the previous warning and absence of mismatch are the acceptance criteria for this stage.

## Validator

Stage 6.7 adds:

```text
tools/validate_stage6_7_srdb_runtime_environment.py
```

Environment-only validation:

```bash
../opensvf/.venv/bin/python tools/validate_stage6_7_srdb_runtime_environment.py
```

Environment plus campaign validation:

```bash
../opensvf/.venv/bin/python tools/validate_stage6_7_srdb_runtime_environment.py --run-campaign
```

## Non-goals

Stage 6.7 does not:

* modify OpenSVF proper;
* modify OpenOBSW proper;
* modify the OpenOBSW SRDB package;
* modify runtime behavior;
* add YAMCS runtime execution;
* validate `eps.obc.bus_voltage_mv` end-to-end;
* validate the event/fault runtime path;
* commit generated runtime evidence JSON.

## Follow-up

Once Stage 6.7 is merged, the clean local runtime setup should treat the editable OpenOBSW SRDB package install as part of the expected developer environment.

This prepares the next substantial stage, most likely YAMCS runtime visibility or event/fault runtime validation.
