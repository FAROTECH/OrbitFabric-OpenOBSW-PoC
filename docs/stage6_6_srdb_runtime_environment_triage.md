# Stage 6.6 - SRDB Runtime Environment Triage

## Purpose

Stage 6.6 is a documentation and technical-triage stage after the Stage 6.5 merge.

Its purpose is to close the roadmap state after the first HK telemetry runtime smoke and to make the remaining SRDB package/version-handshake warning explicit before selecting the next runtime implementation stage.

## Baseline

Stage 6.5 is merged on `main` through PR #16.

It validates the first OpenSVF-observed OpenOBSW housekeeping runtime path:

```text
OpenSVF campaign runner
-> OpenSVF SpacecraftLoader
-> OpenSVF OBCEmulatorAdapter
-> OpenSVF pipe mode
-> OrbitFabric-enabled OpenOBSW obsw_sim
-> OpenOBSW sensor tick
-> OpenOBSW PUS Service 3 housekeeping tick
-> TM(3,25)
-> OpenSVF runtime observation
-> OpenSVF ParameterStore DHS OBC HK visibility
```

The Stage 6.5 boundary remains intentionally narrow:

```text
TM(3,25) observed
dhs.obc.obt visible in OpenSVF ParameterStore
```

It does not claim full OrbitFabric housekeeping contract runtime validation for:

```text
eps.obc.bus_voltage_mv
```

## SRDB runtime warning

The current runtime path still emits the known non-blocking warning:

```text
obsw-srdb package not installed - cannot verify SRDB version handshake
```

This warning does not block the Stage 6.3 ping runtime smoke and does not block the Stage 6.5 housekeeping runtime smoke.

However, it remains relevant because future stages may need a cleaner SRDB/MDB runtime environment, especially for:

* YAMCS runtime visibility;
* stronger generated MDB reproducibility;
* OpenSVF/OpenOBSW version-handshake evidence;
* clean-clone or CI-style validation.

## Stage 6.5 guard carried forward

Stage 6.5 intentionally observes auto-enabled housekeeping.

It does not configure housekeeping through `TC(3,5)`.

The validator guard against `TC(3,5)` should be preserved as a traceable design boundary. A later stage that needs to configure a custom housekeeping set must explicitly remove or replace that constraint and explain why the runtime objective has changed.

## Stage 6.6 decision

Stage 6.6 does not resolve the SRDB package/version-handshake warning.

It records the warning as a deliberate follow-up item and prevents it from becoming an implicit or forgotten limitation.

The next technical stage should choose one of these paths deliberately:

```text
SRDB package/version-handshake cleanup
YAMCS runtime visibility
event/fault runtime path
```

## Non-goals

Stage 6.6 does not:

* modify OpenSVF proper;
* modify OpenOBSW proper;
* modify runtime behavior;
* add a YAMCS runtime execution path;
* add a new HK runtime procedure;
* validate `eps.obc.bus_voltage_mv` end-to-end;
* validate the `TM(5,3)` event/fault runtime path.

## Validation

This stage is documentation-only.

Expected validation:

```bash
git diff --check
grep -n "Stage 6.6" docs/roadmap.md
grep -n "obsw-srdb package not installed" docs/roadmap.md docs/stage6_6_srdb_runtime_environment_triage.md
```
