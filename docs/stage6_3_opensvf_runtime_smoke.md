# Stage 6.3 OpenSVF Runtime Smoke

## Objective

Stage 6.3 performs the first real runtime smoke attempt across the OrbitFabric / OpenOBSW / OpenSVF integration boundary.

The goal is to prove that the PoC can use OpenSVF pipe mode as the runtime bridge to an OrbitFabric-enabled OpenOBSW host simulator, without introducing a custom bridge process.

## Runtime path

The validated runtime path is:

```text
OrbitFabric/OpenOBSW PoC-side runtime campaign
-> OpenSVF campaign runner
-> OpenSVF SpacecraftLoader
-> OpenSVF OBCEmulatorAdapter
-> OpenSVF pipe mode
-> OrbitFabric-enabled OpenOBSW obsw_sim
-> PUS TC(17,1)
-> PUS TM(1,1)
-> PUS TM(17,2)
-> PUS TM(1,7)
```

## Scope

Stage 6.3 includes:

- a runtime-specific OpenSVF spacecraft descriptor;
- an OpenSVF campaign descriptor;
- a Python campaign procedure using the public OpenSVF procedure API;
- local runtime evidence generation through OpenSVF JSON campaign output;
- validation of the first closed-loop PUS ping path.

Stage 6.3 does not include:

- YAMCS execution;
- Docker;
- Renode;
- a custom bridge process;
- changes to OpenSVF proper;
- changes to OpenOBSW proper;
- committed runtime evidence JSON.

## Key finding

The first `svf run` smoke completed successfully with OpenSVF pipe mode and the OrbitFabric-enabled OpenOBSW simulator.

The first campaign-based TC/TM attempt failed when the spacecraft descriptor used the default non-realtime simulation mode. In that mode OpenSVF uses a software tick source and the simulation can complete before the operator-style campaign procedure observes telemetry in wall-clock time.

The campaign closed successfully after setting:

```yaml
simulation:
  realtime: true
```

This is the critical Stage 6.3 runtime finding.

## Validated command path

The Stage 6.3 campaign sends:

```text
TC(17,1)
```

using the public OpenSVF campaign API:

```python
ctx.tc(17, 1, apid=0x001)
```

and observes:

```text
TM(1,1)
TM(17,2)
TM(1,7)
```

through `ctx.expect_tm()`.

## Local validation commands

From the PoC repository root:

```bash
../opensvf/.venv/bin/python tools/validate_stage6_3_opensvf_runtime_smoke.py

../opensvf/.venv/bin/python -m svf.campaign.cli validate execution/opensvf/poc_spacecraft_runtime_smoke.yaml

../opensvf/.venv/bin/python -m svf.campaign.cli check execution/opensvf/poc_spacecraft_runtime_smoke.yaml

../opensvf/.venv/bin/python -m svf.campaign.cli campaign execution/campaigns/poc_runtime_ping_smoke.yaml \
  --json execution/evidence/poc_runtime_ping_smoke_report.json
```

Expected campaign result:

```text
PASS:          1
FAIL:          0
Pass rate: 100.0%
```

## Non-blocking warning

The runtime currently emits:

```text
obsw-srdb package not installed — cannot verify SRDB version handshake
```

This does not block Stage 6.3. The TC/TM closed-loop path completes successfully despite the missing optional SRDB version handshake package.

A later stage may decide whether the SRDB package should become part of the clean runtime environment.
