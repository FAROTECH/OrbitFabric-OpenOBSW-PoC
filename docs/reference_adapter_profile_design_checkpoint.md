# Reference Profile Design Checkpoint

The OpenOBSW/OpenSVF reference adapter extraction now has a first concrete Projection Profile candidate and integration-owned JSON Schema.

Artifacts:

- `docs/openobsw_opensvf_projection_profile_v0.md`
- `schemas/openobsw_opensvf_projection_profile_v0.schema.json`
- `orbitfabric_models/profiles/openobsw_opensvf_poc_v0.yaml`
- `docs/reference_adapter_profile_validation_note.md`

Key ownership corrections extracted from the PoC:

1. Core command identity is `commands/obc.ping`; `dhs.obc.ping` is treated as a target/SRDB naming override.
2. Housekeeping projection is anchored to Core `packets/obc_hk`, so packet membership and period are not duplicated in the Profile.
3. PUS TM[3,25] is modeled at housekeeping-packet materialization level rather than as telemetry parameter semantics.
4. Event severity/trigger condition/threshold remain Core/fault-owned and are removed from target Profile state.
5. Stable APID allocations used by the target integration are explicit Profile settings rather than hidden mutable adapter state.
6. C symbols and SRDB names remain deterministic adapter defaults unless an explicit target override is required.

The candidate schema structurally validates the current PoC example and rejects representative ownership violations such as reintroducing telemetry `unit` into target config or binding a housekeeping projection to a telemetry source instead of a packet source.

The exact SRDB/XTCE boundary, OpenSVF APID policy shape, flight numeric-ID boundary and verification expectation ownership remain subject to review in `lipofefeyt/OrbitFabric-OpenOBSW-PoC#30`.
