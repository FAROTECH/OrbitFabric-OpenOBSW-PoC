# Stage 6.5 OpenSVF HK Telemetry Runtime Smoke

## Objective

Stage 6.5 validates the first housekeeping telemetry runtime path across the OrbitFabric / OpenOBSW / OpenSVF integration boundary.

The goal is to prove that the existing OpenSVF pipe-mode runtime path can observe an OpenOBSW housekeeping telemetry report, not only a command-response ping exchange.

## Runtime path

The validated runtime path is:

```text
OrbitFabric/OpenOBSW PoC-side runtime campaign
-> OpenSVF campaign runner
-> OpenSVF SpacecraftLoader
-> OpenSVF OBCEmulatorAdapter
-> OpenSVF pipe mode
-> OrbitFabric-enabled OpenOBSW obsw_sim
-> OpenOBSW sensor tick
-> OpenOBSW PUS Service 3 housekeeping tick
-> PUS TM(3,25)
-> OpenSVF telemetry observation
-> OpenSVF ParameterStore DHS OBC HK visibility
```

## Scope

Stage 6.5 includes:

- an OpenSVF campaign descriptor for housekeeping telemetry runtime smoke;
- a Python campaign procedure using the public OpenSVF procedure API;
- observation of `TM(3,25)` through `ctx.expect_tm()`;
- confirmation that a DHS OBC housekeeping parameter becomes visible in the OpenSVF `ParameterStore`;
- local runtime evidence generation through OpenSVF JSON campaign output;
- validation of the first OpenOBSW housekeeping telemetry runtime path visible from OpenSVF.

Stage 6.5 does not include:

- YAMCS execution;
- Docker;
- Renode;
- a custom bridge process;
- changes to OpenSVF proper;
- changes to OpenOBSW proper;
- changes to OrbitFabric Core;
- full OrbitFabric housekeeping telemetry contract runtime validation;
- `eps.obc.bus_voltage_mv` runtime validation;
- SRDB package/version-handshake cleanup;
- committed runtime evidence JSON.

## Validated telemetry path

The Stage 6.5 campaign observes:

```text
TM(3,25)
```

using the public OpenSVF campaign API:

```python
ctx.expect_tm(3, 25, timeout=15.0)
```

The campaign then confirms that the DHS OBC on-board time parameter is visible in the OpenSVF `ParameterStore`:

```python
ctx.wait_until(
    lambda store: (
        store.read("dhs.obc.obt") is not None
        and store.read("dhs.obc.obt").value >= 1.0
    ),
    timeout=10.0,
)
ctx.assert_parameter("dhs.obc.obt", greater_than=0.0)
```

This proves that the housekeeping telemetry path is not limited to raw TM detection. The OpenSVF runtime path also exposes a parsed DHS OBC housekeeping value through the validation-side state store.

## Key finding

OpenOBSW already auto-enables the DHS OBC housekeeping set used by OpenSVF.

The runtime campaign does not need to send `TC(3,5)` to enable housekeeping reporting. It observes the periodic housekeeping report emitted by OpenOBSW during sensor-driven runtime ticks.

This keeps Stage 6.5 focused on runtime observability rather than changing housekeeping configuration.

## Local validation commands

From the PoC repository root:

```bash
../opensvf/.venv/bin/python tools/validate_stage6_5_hk_telemetry_runtime_smoke.py

../opensvf/.venv/bin/python -m svf.campaign.cli validate execution/opensvf/poc_spacecraft_runtime_smoke.yaml

../opensvf/.venv/bin/python -m svf.campaign.cli check execution/opensvf/poc_spacecraft_runtime_smoke.yaml

../opensvf/.venv/bin/python -m svf.campaign.cli campaign execution/campaigns/poc_runtime_hk_smoke.yaml \
  --json execution/evidence/poc_runtime_hk_smoke_report.json

../opensvf/.venv/bin/python tools/validate_stage6_5_hk_telemetry_runtime_smoke.py
```

Expected campaign result:

```text
PASS:          1
FAIL:          0
ERROR:         0
INCONCLUSIVE:  0
Pass rate: 100.0%
```

## Non-blocking warning

The runtime currently emits:

```text
obsw-srdb package not installed - cannot verify SRDB version handshake
```

This does not block Stage 6.5.

The campaign validates the OpenSVF-observed housekeeping runtime path despite the missing optional SRDB package/version-handshake check.

A later stage may decide whether the SRDB package should become part of the clean runtime environment.
