# Stage 7.1 - Target Allocation and Compatibility Audit

Status: engineering audit supporting the Stage 7.1 schema candidate.

This document records the external facts used to refine the OpenOBSW/OpenSVF reference Projection Profile after completion of the PoC. It is not a compatibility manifest. Stage 7.2 must perform compatibility preflight against an explicitly selected tested target baseline.

## Audited upstream baselines

```text
OpenOBSW main
b3b7c3fa9c6edd2a52eef356d113c1eae1b03fec
project version 0.7.0
obsw-srdb package version 0.1.0

OpenSVF main
667d3eadcb0bbd7814ac324b99946c4ed2f11f23
package version 1.0.0
```

The engineering rule remains:

```text
value sufficient to prove the PoC
!=
value safe to freeze into a public Integration Package contract
```

## SRDB handoff correction

The legacy PoC generated:

```text
generated_artifacts/ground_segment/poc_srdb.yaml
```

using the OpenSVF-local `ParameterDefinition` schema.

That artifact was useful to prove the vertical slice, but it is not the correct durable SRDB boundary for the extracted Integration Package.

The audited OpenOBSW baseline contains the `obsw-srdb` package. Its typed model and loader define the target database as:

```text
spacecraft.yaml
parameters.yaml
telecommands.yaml
hk_sets.yaml
events.yaml
```

with explicit models for:

```text
Parameter
Telecommand
HKSet
Event
Spacecraft
```

The package also owns code generation from those SRDB records.

Stage 7 therefore targets `obsw-srdb 0.1.0` compatible data. OrbitFabric does not generate XTCE.

This interpretation is consistent with PR #30 ownership review:

```text
OrbitFabric integration -> SRDB handoff
external OpenOBSW/OpenSVF ecosystem -> XTCE generation
```

## Why the old OpenSVF-local XTCE script is not the production authority

OpenSVF 1.0.0 still contains a repository-local `tools/generate_xtce.py` script used by the completed PoC path.

That script contains fixed containers for some PUS messages and does not contain the complete dynamic SRDB behavior needed by the extracted integration. In particular, it was the reason PoC-local XTCE augmentation was needed for the event path.

By contrast, `obsw-srdb 0.1.0` code generation:

```text
builds TM(3,25) containers from hk_sets.yaml
uses ordered HK parameter lists to compute field offsets
builds TM(5,1), TM(5,2), TM(5,3), TM(5,4)
builds TM(17,2)
builds TM(20,2)
builds telecommands from telecommands.yaml
```

The production Integration Package must therefore target the `obsw-srdb` schema/codegen boundary and must not call or patch the old OpenSVF-local XTCE script.

## TM secondary-header authority

OpenOBSW exposes:

```text
OBSW_PUS_TM_SEC_HDR_LEN = 11U
```

in its public PUS TM header.

The audited `obsw-srdb 0.1.0` code generator currently encodes the corresponding XTCE layout with application data beginning at bit 136:

```text
CCSDS primary header 48 bits
+
PUS TM secondary header 88 bits
=
application data at bit 136
```

This is external target behavior, not an OrbitFabric constant.

Stage 7.2 must compare the OpenOBSW declared secondary-header length with the tested `obsw-srdb` layout assumption before generating a successful target result.

If they diverge, `project` is incompatible. The Adapter must not repair the mismatch by generating its own XTCE offsets.

A future upstream improvement should remove duplicate layout authority inside the target ecosystem, but OrbitFabric must not silently create that upstream interface itself.

## TM APID authority

The legacy PoC generator derived TM APIDs from a private table based on subsystem domain.

That table is PoC scaffolding and is retired from the production design.

The audited OpenOBSW reference mission declares:

```text
spacecraft.apid_default = 0x103
```

and uses that value for its PUS TM contexts.

Stage 7.1 therefore authors:

```text
settings.pus.tm_apid = 0x103
```

Stage 7.2 verifies it against the selected tested baseline.

No APID is derived from an OrbitFabric semantic subsystem/domain.

## TC APID semantics

The audited target telecommand database uses:

```text
APID 0x010
service 17
subservice 1
```

for `are_you_alive`.

Stage 6.19 independently exercised a `TC(17,1)` ground representation carrying APID `0x010`.

However the OpenOBSW OrbitFabric contract route currently resolves `OF_CMD_PING` with wildcard APID `0xFFFF` before installing the route into the dispatcher.

Therefore:

```text
Profile tc_apid = target ground/telecommand representation
!=
mandatory fixed OpenOBSW runtime acceptance APID
```

Stage 7.2 validates the selected target representation and route compatibility separately. It must not invent a requirement that TC APID must equal the TM APID.

## obsw-srdb parameter allocation

The legacy PoC used `0x4001` for `eps.obc.bus_voltage_mv`.

The audited `obsw-srdb` baseline already assigns:

```text
parameter ID 0x4001 -> obc_mode
```

Therefore the old value cannot be appended to the target SRDB as a new parameter allocation.

Stage 7.1 uses:

```text
obsw_srdb.parameter_id = 0x6001
```

`0x6001` was not found in the audited target baseline. It is version-controlled state of the reference Profile only and is not claimed as a reserved range.

Important correction:

`obsw-srdb Parameter.id` is a database/code-generation allocation. It is not a parameter identifier carried for each field inside `TM(3,25)`.

OpenOBSW Service 3 serializes:

```text
HK SID
+ ordered field values
```

The field layout is therefore modeled separately through the packet binding.

## Housekeeping SID and field layout

The audited target SRDB already assigns:

```text
1 -> nominal_hk
2 -> fdir_hk
3 -> dhs_obc_hk
4 -> aocs_hk
```

The PoC `obc_hk` packet is not semantically identical to any of those sets.

Stage 7.1 therefore uses:

```text
HK SID = 5
```

SID 5 is free in the audited baseline.

The real target layout authority is the ordered `HKSet.parameters` list in `obsw-srdb`.

OrbitFabric Core packet membership is a logical semantic grouping and does not define wire order. Therefore Stage 7.1 adds explicit target configuration:

```text
packet binding
    -> hk_set.sid
    -> ordered hk_set.fields as Core telemetry references
```

The Adapter derives each target parameter definition from Core semantics, but the Profile owns the target packing order.

The first package does not author collection scheduling. `obsw-srdb` requires `default_interval_ticks`; Stage 7.2 should use an Adapter default of `0` for newly generated HK sets unless a later reviewed target scheduling feature is introduced. That default means no scheduling behavior is inferred from Core packet period.

## Command target resolution

Stage 7.1 keeps:

```text
flight_contract.command_id = 0x1701
PUS TC = 17/1
```

The flight-contract command ID is a separate contract ABI namespace.

The audited `obsw-srdb` baseline already contains target telecommand:

```text
name = are_you_alive
APID = 0x010
service = 17
subservice = 1
parameters = []
```

The first Adapter must therefore resolve the Core command to this existing target record when the argument shape is compatible.

Correct behavior:

```text
existing exact tuple + compatible arguments
    -> reuse/map existing SRDB telecommand
```

Incorrect behavior:

```text
existing exact tuple
    -> append second telecommand with same tuple
```

The `obsw-srdb` loader explicitly rejects duplicate `(APID, service, subservice)` telecommand tuples.

## Event allocation and severity projection

The PoC event allocation:

```text
0x5001
```

is free in the audited `obsw-srdb` event ID namespace.

Stage 7.1 retains it as:

```text
obsw_srdb.event_id = 0x5001
```

Core owns event severity.

`obsw-srdb` uses a target severity vocabulary:

```text
INFO
LOW
MEDIUM
HIGH
```

and maps it to:

```text
TM(5,1)
TM(5,2)
TM(5,3)
TM(5,4)
```

Stage 7.1 therefore uses a Profile-authored severity projection map instead of duplicating `service: 5` and a subtype on every event binding.

The canonical map keeps the exercised PoC behavior:

```text
Core warning -> obsw-srdb MEDIUM -> TM(5,3)
```

The package validator requires target severity mapping to remain non-decreasing as Core severity increases.

## Exact PUS message capability

A broad statement such as:

```text
PUS Service 5 supported
```

is not precise enough for compatibility.

The Stage 7.2 baseline must record exact message capabilities relevant to the requested operation.

For the reference slice the audited target path supports:

```text
TC(17,1) command representation
TM(1,1) acceptance success
TM(1,7) completion success
TM(17,2) are-you-alive response
TM(3,25) HK report
TM(5,3) medium event report
```

OpenOBSW runtime and `obsw-srdb` code generation are separate authorities and Stage 7.2 should establish both where both are required.

## C symbol continuity

The PoC contract defines:

```text
OF_TM_OBC_BUS_VOLTAGE_MV
OF_HK_SET_OBC
OF_CMD_PING
OF_EVENT_VOLTAGE_OUT_OF_BOUNDS
```

Current OpenOBSW integration code directly consumes `OF_CMD_PING` and `OF_EVENT_VOLTAGE_OUT_OF_BOUNDS`.

Stage 7.1 preserves all four symbols as explicit target-facing contract choices. They are not Core identities.

## Telemetry evidence scope

Stage 6.17 proves:

```text
live OpenOBSW TM(3,25)
-> OpenSVF OBCEmulatorAdapter
-> OpenSVF YamcsBridge
-> YAMCS archive/classification
```

It does not prove byte-for-byte runtime materialization of the specific Core entity `eps.obc.bus_voltage_mv`.

The Stage 6.20 closure remains valid for its PoC scope because it combines projection evidence with live transport evidence.

The production Integration Result must keep separate:

```text
static projection mapping established
runtime transport evidence established
specific runtime materialization established
```

Static `project` coverage must not be downgraded merely because runtime materialization is outside that operation.

## OpenSVF runtime compatibility

OpenSVF package version `1.0.0` is an audited runtime baseline fact.

It is not required to execute the first static `project` operation if that operation only consumes Core inputs and produces flight-contract plus `obsw-srdb` artifacts.

Runtime-only compatibility includes:

```text
wire protocol version
OBCEmulatorAdapter API
YamcsBridge API/lifecycle
YAMCS orchestration
verification campaign execution
```

Those facts become mandatory only for operations that advertise the corresponding runtime/verification capabilities.

The first `project` operation must not fail because a runtime-only API marker is unavailable.

## Compatibility marker audit

### OpenOBSW version

Machine-readable authority exists through CMake project version `0.7.0`.

### obsw-srdb

Machine-readable package version exists: `0.1.0`.

The typed model/loader and codegen behavior are available at the audited OpenOBSW commit.

### PUS TM secondary header

Public compile-time authority exists:

```text
OBSW_PUS_TM_SEC_HDR_LEN = 11U
```

### Exact static PUS message support

No single capability descriptor currently exports all exact message tuples. The tested baseline snapshot may record exact capabilities established from audited target source because it is pinned to an exact commit.

Runtime discovery must not pretend that this is a live capability query.

### Wire protocol

OpenSVF documentation and OpenOBSW protocol headers describe wire protocol v3.

No dedicated machine-readable version marker was found. A stale host-sim banner still refers to an older version, so log/banner parsing is forbidden.

This is runtime-only for the first `project` operation.

### OBCEmulatorAdapter API

No separate API identity/version marker was found.

OpenSVF package version must not be mislabeled as an `OBCEmulatorAdapter` API version.

This is runtime-only for the first `project` operation.

## Stage 7.2 preflight requirements

Before target artifact generation, `project` must establish at least:

```text
selected tested projection baseline is known
OpenOBSW target version is supported
obsw-srdb package/schema version is supported
Profile TM APID is compatible with target TM source
command TC tuple can be resolved or safely added
required exact TM response messages are supported
Core packet HK fields resolve and belong to the packet
obsw-srdb parameter IDs do not collide
obsw-srdb event IDs do not collide
obsw-srdb HK SIDs do not collide
generated target names do not collide
OpenOBSW TM secondary-header declaration matches tested obsw-srdb XTCE layout
```

A missing required authority is not permission to guess.

Correct states include:

```text
compatible
incompatible
unavailable
not_applicable
```

## Upstream interface improvements to discuss later

The audit still identifies useful future upstream improvements:

```text
single machine-readable exact PUS capability descriptor
shared versioned TM layout authority used directly by obsw-srdb codegen
machine-readable wire protocol version
stable public OpenSVF TM observation/sink API
explicit OBCEmulatorAdapter API identity/version marker
```

OrbitFabric must not silently add or emulate these upstream interfaces.

## Stage 7.1 disposition

The audit does not invalidate the Stage 6 PoC.

It identifies which PoC facts are safe to promote and which experimental artifacts must be replaced by the real target contract.

Stage 7.1 may proceed only with these corrections:

```text
obsw-srdb is the target SRDB schema
telemetry parameter ID is an SRDB allocation, not HK wire identity
HK field order is explicit target configuration
command tuple reuse is distinguished from allocation collision
event subtype is derived from explicit severity projection
exact PUS messages replace broad service-only compatibility
runtime-only compatibility does not block static project
OrbitFabric does not generate XTCE
```
