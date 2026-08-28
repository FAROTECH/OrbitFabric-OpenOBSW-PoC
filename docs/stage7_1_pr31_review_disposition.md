# Stage 7.1 - PR #31 review disposition

Status: focused review note for the OpenOBSW/OpenSVF-facing points raised during approval of Stage 7.0.

This note records how the Stage 7.1 schema candidate responds to the review of PR #31 without starting Adapter implementation.

## 1. `flight_contract.command_id` is an independent ABI allocation

PR #31 correctly flagged that the Stage 7.0 PoC value:

```text
0x1701
```

happens to equal:

```text
(0x17 << 8) | 0x01
```

for PUS TC(17,1).

The Stage 7.1 decision is explicit:

```text
flight_contract.command_id
!=
derived PUS service/subtype encoding
```

`flight_contract.command_id` is an independent 16-bit identifier in the generated flight-contract ABI namespace.

The PUS tuple is a separate target projection choice.

This is not only a modeling preference. The audited OpenOBSW integration boundary demonstrates the separation directly:

```text
generated mission_contract.h
    OF_CMD_PING = 0x1701

OpenOBSW orbitfabric_contract_adapter.c
    switch (command_id)
        case OF_CMD_PING
            -> route APID wildcard
            -> service 17
            -> subservice 1
```

The contract identifier is therefore the input key from which OpenOBSW resolves a PUS route. It is not computed from that route.

Stage 7.1 keeps `0x1701` in the reference Profile because changing it merely to avoid the visual coincidence would introduce an arbitrary ABI reallocation with no engineering benefit.

Instead, the schema now documents the independence explicitly and the validation suite contains a positive case in which the command ID is changed to `0x7101` while the PUS tuple remains TC(17,1). That Profile remains structurally valid.

The only Stage 7.1 invariant on command IDs is uniqueness within the flight-contract command-ID namespace.

## 2. `dhs.obc.ping` needs one precise ownership confirmation

PR #31 also confirmed the Stage 7.0 `srdb_name: dhs.obc.ping` override because existing OpenSVF campaign procedures may depend on that name.

The subsequent Stage 7.1 target-model audit reached a more specific SRDB boundary:

```text
OrbitFabric Integration Package
    -> obsw-srdb-compatible target data
    -> target-owned codegen / XTCE
```

In the pinned OpenOBSW/obsw-srdb baseline, the existing telecommand record for the required target tuple is:

```text
name       = are_you_alive
APID       = 0x010
service    = 17
subservice = 1
parameters = []
```

The `obsw-srdb` loader requires the `(APID, service, subservice)` telecommand tuple to be unique.

Stage 7.1 therefore resolves the Core command by exact target tuple and compatible argument shape:

```text
Core command obc.ping
    + Profile TC(17,1), APID 0x010
        -> existing target telecommand are_you_alive
        -> reuse_existing
```

It must not create a second SRDB telecommand only to preserve a different name.

For this reason the current Stage 7.1 schema deliberately rejects the generic field name `srdb_name`.

However, the PR #31 review identifies a potentially real external verification-facing naming dependency that should not be lost. Before freezing a replacement field, we would like one OpenSVF-side confirmation:

> Is `dhs.obc.ping` a durable externally-addressable OpenSVF/campaign identifier that must remain available independently of the actual `obsw-srdb` telecommand record name `are_you_alive`, or was it specific to the PoC-era campaign/SRDB path?

If it is durable, Stage 7.1 should model it under a vocabulary that reflects its real owner and role, for example a verification-facing alias/identifier, rather than calling it the `obsw-srdb` record name.

If it is PoC-only, the extracted Integration Package should retire it and use the target-owned telecommand identity resolved from the pinned SRDB baseline.

No Adapter behavior is implemented until this naming boundary is confirmed.

## 3. Other PR #31 confirmations already match Stage 7.1/7.2

The remaining review confirmations already align with the current extracted design:

```text
pus_tm_secondary_header_len
    -> target compatibility authority, never private Adapter constant

telemetry binding vs HK packet binding
    -> separate target concerns

expected ping responses
    -> TM(1,1), TM(17,2), TM(1,7)
```

No additional Stage 7.1 correction is required for those points.

## 4. Review scope

The useful review scope at this point is intentionally narrow:

```text
Stage 7.1 Profile vocabulary
command-ID namespace decision
command target reuse semantics
verification-facing naming ownership
obsw-srdb handoff assumptions
```

Stage 7.2 compatibility-preflight design exists on a later stacked branch but is not required for this review.

No `integration_package.json`, Adapter CLI, target generation or runtime behavior is introduced by this review disposition.
