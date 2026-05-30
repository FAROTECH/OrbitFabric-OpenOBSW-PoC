# OpenSVF SRDB Alignment

This document records the Stage 3 alignment decision for the
OrbitFabric-OpenOBSW-PoC validation artifact.

## Scope

Stage 3 makes the generated SRDB artifact compatible with the native OpenSVF
SRDB ParameterDefinition schema.

The generated file is:

```text
generated_artifacts/ground_segment/poc_srdb.yaml
```

This file is an OpenSVF-native SRDB artifact. It is not a flight software
artifact.

The flight-side artifact remains:

```text
generated_artifacts/flight_software/mission_contract.h
```

## Decision

The generated SRDB now emits parameters as a YAML mapping, as expected by
OpenSVF SrdbLoader.

Each generated parameter includes the OpenSVF-required fields:

```text
description
unit
dtype
classification
domain
model_id
```

The PUS mapping uses the native OpenSVF shape:

```text
apid
service
subservice
parameter_id
```

## Current PoC parameter mapping

The current vertical slice contains one telemetry parameter:

```text
eps.obc.bus_voltage_mv
```

It is mapped as:

```text
classification: TM
domain: EPS
model_id: eps
dtype: int
apid: 0x100
service: 3
subservice: 25
parameter_id: 0x4001
```

uint16 from the OrbitFabric Mission Model is mapped to OpenSVF int, because
the OpenSVF SRDB schema currently supports float, int, bool, and string.

## Valid range and warning threshold

The SRDB valid_range is generated as:

```text
[0.0, 65535.0]
```

This represents the raw unsigned 16-bit storage range of the telemetry value.

The OrbitFabric warning threshold:

```text
warning_high: 3500
```

is intentionally not emitted into the OpenSVF SRDB artifact at this stage.

That threshold remains part of the OrbitFabric Mission Model fault and limit
semantics. OpenSVF SRDB currently has valid_range, but no native warning-limit
or debounce fault-definition schema in this PoC integration path.

## Commands and events

Stage 3 does not emit commands or events into the SRDB artifact.

The command:

```text
obc.ping
```

and the event:

```text
eps.voltage_out_of_bounds
```

remain represented in the OrbitFabric Mission Model and in the flight contract
artifact where applicable.

They are not represented as OpenSVF SRDB parameters in this stage, because the
native SRDB schema is parameter-definition centric.

## Non-goals

Stage 3 does not:

```text
modify OpenSVF
modify OpenOBSW
execute runtime validation
generate XTCE directly
wire YAMCS runtime execution
introduce Docker or CI
```
