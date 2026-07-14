# Stage 6.17 - Live OpenOBSW HK TM to YAMCS Path Probe

Stage 6.17 validates the first live OpenOBSW-generated housekeeping telemetry path into YAMCS.

This stage builds on Stage 6.16. Stage 6.16 proved that the real OpenSVF `YamcsBridge` can deliver representative TM packets into the YAMCS `tm-in` link and that YAMCS can archive/classify them. Stage 6.17 replaces representative TM generation with a Linux-built OpenOBSW `obsw_sim` executed inside the Docker runtime.

## Live OpenOBSW APID alignment

The live OpenOBSW simulator emits TM packets on APID `0x103`. The Stage 6.17 driver configures the OpenSVF `OBCEmulatorAdapter` with `--apid 0x103` so that the adapter parser and queue are aligned with the live OpenOBSW packet stream.

## Runtime path

```text
Linux-built OpenOBSW obsw_sim
-> OpenSVF OBCEmulatorAdapter pipe mode
-> OBCEmulatorAdapter live TM parsing
-> existing OBCEmulatorAdapter._yamcs_bridge TM hook
-> real OpenSVF YamcsBridge
-> YAMCS tm-in TcpTmDataLink
-> YAMCS packet archive
-> MDB packet classification
```

## What is validated

When `../opensvf` and `../openobsw` are present, the validator runs the Docker runtime probe and validates that:

* OpenOBSW `obsw_sim` is built inside the Linux sidecar container;
* the built simulator is an ELF x86-64 Linux executable;
* the real OpenSVF `OBCEmulatorAdapter` starts `obsw_sim` in pipe mode;
* live `TM(3,25)` is observed at the `OBCEmulatorAdapter._parse_tm` instrumentation point before forwarding through the existing adapter TM hook;
* the real OpenSVF `YamcsBridge` is attached through the adapter TM hook;
* YAMCS `tm-in` consumes the forwarded packets;
* the YAMCS packet archive contains a live `TM(3,25)` packet;
* the archived packet is classified against the generated MDB container `TM_3_25_HK`.

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

* YAMCS TC command path execution;
* live event/fault generation by OpenOBSW;
* full OpenSVF/OpenOBSW/YAMCS closed-loop campaign execution;
* hardware target execution;
* production deployment hardening.

The OpenSVF adapter may send its own internal heartbeat traffic to OpenOBSW as part of pipe-mode operation. This is not a claim of YAMCS-originated TC command execution.

### Slow or cold Docker environments

The live OpenOBSW sidecar uses a dedicated cached Docker image with the
Ubuntu runtime and build tooling pre-installed. On a fresh Docker environment,
the first image build can still be slow, but subsequent validator runs reuse the
Docker image cache instead of reinstalling build tools at container runtime.

Use the following override when validating on slow or freshly rebuilt Docker
setups:

```bash
STAGE617_DRIVER_MARKER_TIMEOUT_S=2400 \
python3 tools/validate_stage6_17_live_openobsw_hk_tm_yamcs_path_probe.py
```

The override only extends the wait for the live driver marker. It does not relax
any Stage 6.17 evidence checks or change the claimed runtime path.
