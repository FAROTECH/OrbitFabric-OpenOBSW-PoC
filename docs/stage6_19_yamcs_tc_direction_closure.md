# Stage 6.19 - YAMCS TC Direction Closure Probe

Stage 6.19 validates the first YAMCS-originated telecommand direction into live OpenOBSW host-sim execution.

This stage builds on Stage 6.17 and Stage 6.18.

Stage 6.17 proved that live OpenOBSW telemetry can be observed through the real OpenSVF `OBCEmulatorAdapter` and forwarded through the real `YamcsBridge` into YAMCS.

Stage 6.18 proved that a live OpenOBSW-generated event telemetry packet, `TM(5,3)`, can reach YAMCS `tm-in`, packet archive, and MDB classification.

Stage 6.19 closes the opposite command direction for the representative `ping` command:

```text
YAMCS command release
-> YAMCS StreamTcCommandReleaser
-> YAMCS tc_realtime stream
-> YAMCS tc-out UdpTcDataLink
-> real OpenSVF YamcsBridge TC UDP receiver
-> YamcsBridge.get_tc()
-> OBCEmulatorAdapter.receive_tc(...)
-> OpenOBSW obsw_sim
-> representative PUS response telemetry
-> OpenSVF YamcsBridge TM forwarding
-> YAMCS tm-in/archive/classification
```

## Command under test

The command under test is the generated MDB command:

```text
/opensvf/TC_17_1_AreYouAlive
```

The MDB fixed binary command is:

```text
1810c00000041111010000
```

This is the representative `TC(17,1)` Are-You-Alive command used throughout the PoC as the `ping` command path.

## Runtime path

When `../opensvf` and `../openobsw` are present, the validator runs the Docker runtime probe and validates that:

* YAMCS starts with the generated PoC MDB;
* the YAMCS `realtime` processor has commanding enabled;
* YAMCS accepts the REST command release for `/opensvf/TC_17_1_AreYouAlive`;
* YAMCS emits the expected fixed binary command through `tc-out`;
* the real OpenSVF `YamcsBridge` receives the YAMCS-originated TC on UDP port 10025;
* the TC is forwarded to OpenOBSW through `OBCEmulatorAdapter.receive_tc(...)`;
* live OpenOBSW `obsw_sim` handles the command;
* the representative response sequence is observed: `TM(1,1)`, `TM(17,2)`, `TM(1,7)`;
* YAMCS `tm-in` consumes the response telemetry;
* the YAMCS packet archive contains/classifies the response telemetry as `TM_1_1_Accept`, `TM_17_2_Pong`, and `TM_1_7_Complete`.

## Optional sibling repository behavior

This stage preserves the PoC soft-skip rule for optional sibling repositories.

The PoC-local artifacts are always validated. The live runtime probe is skipped with an explicit `NOTICE` when either optional sibling repository is absent:

```text
OPENSVF_ROOT missing -> NOTICE + runtime skipped + PASS
OPENOBSW_ROOT missing -> NOTICE + runtime skipped + PASS
```

A missing optional sibling repository must not produce a `Required file not found` failure.

If both repositories are present, the runtime probe is mandatory and failures are real failures.

## Explicit non-claims

This stage does not claim:

* production commanding authorization;
* production command queueing policy;
* production command security;
* production deployment hardening;
* hardware target execution;
* Renode or STM32 execution;
* broader mission closed-loop campaign execution.

The validated claim is intentionally narrow:

```text
YAMCS-originated representative TC(17,1)
-> OpenSVF YamcsBridge
-> OpenOBSW host-sim command reception
-> representative PUS response telemetry
-> YAMCS visibility/archive/classification
```

## Slow or cold Docker environments

The Stage 6.19 sidecar uses a dedicated cached Docker image with the Ubuntu runtime, OpenOBSW build tooling, `PyYAML`, and `pydantic>=2,<3` pre-installed.

On a fresh Docker environment, the first image build can still be slow, but subsequent validator runs reuse the Docker image cache.

Use the following override when validating on slow or freshly rebuilt Docker setups:

```bash
STAGE619_DRIVER_MARKER_TIMEOUT_S=2400 \
python3 tools/validate_stage6_19_yamcs_tc_direction_closure.py
```

The override only extends the wait for the live driver marker. It does not relax any Stage 6.19 evidence checks or change the claimed runtime path.
