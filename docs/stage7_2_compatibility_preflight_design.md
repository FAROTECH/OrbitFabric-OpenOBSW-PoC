# Stage 7.2 - Compatibility Preflight Design

Status: design candidate on stacked branch `stage7.2/compatibility-preflight-design`.

This document defines the target compatibility preflight for the first executable OpenOBSW/OpenSVF Integration Package.

It deliberately does not implement the Adapter CLI, create `integration_package.json`, or advertise executable capabilities that do not yet exist.

Depends on:

```text
Stage 7.0 extraction baseline
Stage 7.1 Projection Profile schema candidate
Stage 7.1 target compatibility audit
OrbitFabric Core v1.2.0
Integration Package Manifest and Adapter Execution Contract 0.1-candidate
Integration Result Contract 0.1-candidate
PR #30 OpenOBSW/OpenSVF ownership review
```

## 1. Objective

The preflight converts the PoC audit findings into deterministic rules that run before any target artifact is generated.

The governing distinction is:

```text
PoC evidence proved one exercised path
!=
production compatibility established for an explicitly selected target baseline
```

A missing required authority is not permission to guess.

The first operation is intentionally narrower than deployment or target mutation:

```text
project
    -> validate projection against a pinned target baseline
    -> generate extension-owned target-facing artifacts
    -> record mappings, resolutions, diagnostics and provenance

project
    != apply generated records into an OpenOBSW checkout
    != assemble a complete OpenOBSW SRDB
    != build OpenOBSW
    != generate XTCE
    != run OpenSVF or YAMCS
```

This distinction is normative for the first executable package.

## 2. Two preflight layers

Compatibility has two owners.

### Layer A - generic caller preflight

Owner:

```text
OrbitFabric generic caller, CLI, CI, or Studio orchestration
```

Checks before Adapter execution:

```text
Integration Package manifest kind/version
requested operation exists
operation capability declarations are consistent
Core Integration Input Set version
required Core surface role/kind/format versions
Projection Profile generic envelope version
Profile integration.id matches package integration.id
Profile integration.schema_version has a published package schema
published Profile schema digest matches exact schema bytes
Integration Result default version
execution protocol = orbitfabric.adapter_cli.v0
```

Layer A must not know OpenOBSW SRDB IDs, PUS messages, HK layout, target APIDs, OpenSVF runtime APIs, or YAMCS.

A Layer A failure occurs before Adapter execution, so an Adapter-produced `integration_result.json` is not expected.

### Layer B - target-specific Adapter preflight

Owner:

```text
OpenOBSW/OpenSVF Integration Package / Adapter
```

Runs after Adapter process invocation and before artifact generation.

Checks:

```text
input integrity defensively revalidated by Adapter
Core source resolution
integration-specific Profile semantics
tested target baseline selection
obsw-srdb schema/codegen compatibility
Core-to-target representation fidelity
PUS message compatibility
target allocation and target-name collision freedom
existing telecommand tuple compatibility
TM layout compatibility
contribution-bundle generation compatibility
```

Failures are machine-readable Integration Result diagnostics whenever a Result can be produced reliably.

## 3. First operation scope

The first executable package is planned to advertise one operation:

```text
project
```

with generic capabilities:

```text
profile_validation
projection
artifact_generation
traceability
```

It does not advertise:

```text
runtime_discovery
runtime_orchestration
verification_execution
evidence_discovery
live_telemetry
commanding
```

The preflight is therefore operation-scoped.

Runtime-only compatibility and target-application automation must not block `project`.

## 4. Projection target baseline

The first Profile selects:

```text
openobsw-0.7.0-obsw-srdb-0.1.0-reference
```

The tested projection baseline is pinned to:

```text
OpenOBSW 0.7.0
commit b3b7c3fa9c6edd2a52eef356d113c1eae1b03fec

obsw-srdb 0.1.0
same audited OpenOBSW commit
```

OpenSVF 1.0.0 at commit:

```text
667d3eadcb0bbd7814ac324b99946c4ed2f11f23
```

remains useful audited runtime context, but is not a required static `project` baseline gate because the first `project` operation does not call an OpenSVF runtime API.

## 5. Why the baseline is package-owned

`orbitfabric.adapter_cli.v0` accepts only:

```text
run
--operation
--input-set-manifest
--profile
--output-dir
```

There is no generic target-repository path argument.

The Adapter must not compensate through hidden discovery such as:

```text
search current working directory
search sibling repositories
search $HOME
scan PATH and infer package identity
read undocumented environment variables
network-clone OpenOBSW or OpenSVF
parse repository main at execution time
```

The package therefore contains version-controlled tested baseline knowledge for each explicitly supported projection baseline.

This knowledge does not replace upstream authority. It records audited upstream facts with exact source provenance.

A new OpenOBSW or obsw-srdb version requires a separately reviewed/tested baseline resource. There is no nearest-version or latest-version fallback.

## 6. Authority classes

Every compatibility fact belongs to one of these classes.

### upstream_machine_authority

A machine-readable or compile-time target authority exists.

Examples:

```text
OpenOBSW CMake version
obsw-srdb package version
OpenOBSW PUS TM secondary-header constant
obsw-srdb typed data model and loader
obsw-srdb target allocation files
OpenOBSW runtime service implementations
```

### tested_baseline_fact

The exact audited baseline establishes a fact but does not expose a dedicated runtime capability descriptor.

Example:

```text
exact PUS messages implemented by the pinned source baseline
```

The package may use the fact only for that exact supported baseline. It must not present it as live target discovery.

### profile_authored

The mission/integration author selects a target choice.

Examples:

```text
target baseline ID
TM APID
TC representation APID
obsw-srdb parameter ID
flight-contract command ID
obsw-srdb event ID
obsw-srdb HK SID
HK packing field order
Core-to-obsw-srdb severity projection policy
```

### adapter_derived

The Adapter deterministically derives a target representation from Core semantics under reviewed rules.

Examples:

```text
target parameter name from Core ID
obsw-srdb type/PTC/PFC from supported Core scalar type
target description and unit from Core
obsw-srdb event severity from Core severity plus Profile severity map
PUS event subtype from resolved obsw-srdb severity
```

### unavailable

No supported authority can establish a required fact.

A required unavailable fact blocks `project`.

An unavailable capability outside `project` scope is `not_applicable`, not a project failure.

## 7. Real SRDB target boundary

The durable target data model is `obsw-srdb 0.1.0`, audited in OpenOBSW.

It defines a complete database through:

```text
spacecraft.yaml
parameters.yaml
telecommands.yaml
hk_sets.yaml
events.yaml
```

and typed models for:

```text
Spacecraft
Parameter
Telecommand
HKSet
Event
```

Its loader validates a complete database as a unit and its code generator owns C constants and XTCE generation from that complete database.

OrbitFabric must therefore generate records compatible with this target model and must not productize the legacy `poc_srdb.yaml` or the old PoC-local XTCE patching path.

## 8. Projection artifact versus target application

The audited `obsw-srdb 0.1.0` loader consumes a complete data directory and does not currently expose a supported external extension/overlay merge interface.

That is a limitation for automated target application, but it is not a blocker for the `project` operation.

The first Integration Package owns projection and artifact generation. It does not own target repository mutation.

The correct first boundary is:

```text
Core Integration Input Set
        +
Projection Profile
        +
pinned target baseline facts
        |
        v
Integration Adapter project
        |
        +-> flight contract artifact
        |
        +-> obsw-srdb contribution records
        |
        +-> Integration Result
```

The generated SRDB-facing artifact is explicitly an:

```text
obsw-srdb contribution bundle
```

not a complete SRDB data directory.

The contribution bundle contains target-model records intended to be incorporated into a compatible complete SRDB by an explicit integration/application step outside the first `project` operation.

This is valid under the generic Integration Result contract because artifact kinds are integration-owned and artifact generation does not imply target application.

The Adapter must never label the contribution bundle as:

```text
complete SRDB
applied SRDB
validated complete OpenOBSW database
OpenOBSW build input already installed
```

unless a later operation actually establishes those facts.

## 9. Contribution bundle contract

The first project bundle may contain:

```text
srdb/parameters.yaml
srdb/hk_sets.yaml
srdb/events.yaml
srdb/telecommands.yaml
```

These files use the same record vocabulary as `obsw-srdb 0.1.0`, but each file contains only records contributed by this integration run.

They are not passed directly to `SRDBLoader.load()` as though they were a complete target database.

The semantic manifest for the bundle remains `integration_result.json`; no second competing preflight/result manifest is introduced.

Required first-slice records are:

```text
new parameter record for eps.obc.bus_voltage_mv
new HK set record for obc_hk
new event record for eps.voltage_out_of_bounds
```

The canonical `obc.ping` command resolves to the existing target telecommand `are_you_alive`, so no duplicate telecommand contribution is generated for that binding.

If a future projected command requires a new target telecommand and the exact runtime message capability is supported, a new telecommand contribution record may be generated after collision checks. That still does not mean it was applied to OpenOBSW.

## 10. What project validates for contribution records

Before generating the contribution bundle, the Adapter validates:

```text
Core source resolution
Profile schema and package semantic invariants
target type representability
target ID ranges and Profile-local uniqueness
collision freedom against the pinned baseline registry
target-name collision freedom against the pinned baseline registry
HK field membership and explicit order
cross-reference consistency among generated contribution records
existing target TC tuple compatibility
exact required PUS message support
TM header/codegen layout compatibility
```

This is compatibility validation, not target merge implementation.

The Adapter does not silently apply precedence, replacement, override or merge rules to baseline target records.

## 11. Core source resolution

The Adapter consumes only the Core Integration Input Set.

Every Profile source uses Core identity:

```text
{domain,id}
```

and resolves through the consumed Core surfaces.

No raw Mission Model YAML fallback is permitted.

For the first slice the Adapter additionally resolves packet membership from the Core Mission Snapshot because Core packet membership is semantic mission data.

## 12. Core packet semantics versus HK wire layout

Core v0.1 packet membership is a logical grouping. Core does not define a real packet protocol or wire packing order.

Therefore:

```text
Core packet.telemetry list
!= target wire order authority
```

The packet Profile binding explicitly authors target HK field order:

```text
obsw_srdb.hk_set.fields
```

Every field is still a Core telemetry reference.

Preflight requires:

```text
field resolves as Core telemetry
field belongs to the referenced Core packet
field has a projected telemetry binding
field appears at most once in the HK target layout
field type is representable by obsw-srdb
```

The Adapter must not infer additional fields or reorder them.

## 13. obsw-srdb parameter projection

The target `Parameter` record requires:

```text
id
name
description
type
ptc
pfc
```

and optionally supports:

```text
subsystem
unit
enumeration
conversion
limits
```

The first Adapter derives a deterministic target parameter name from the Core telemetry ID using a documented snake_case transformation.

For example:

```text
eps.obc.bus_voltage_mv
    -> eps_obc_bus_voltage_mv
```

The first supported Core scalar mapping is exactly:

```text
Core uint8    -> target uint8,   PTC 1, PFC 8
Core uint16   -> target uint16,  PTC 1, PFC 16
Core uint32   -> target uint32,  PTC 1, PFC 32
Core int8     -> target int8,    PTC 2, PFC 8
Core int16    -> target int16,   PTC 2, PFC 16
Core int32    -> target int32,   PTC 2, PFC 32
Core float32  -> target float32, PTC 5, PFC 1
```

The first package does not guess mappings for:

```text
bool
float64
enum
string
```

Those require separately reviewed target representation rules.

Core unit and description are Core-owned and may be copied into the generated target record as derived representation.

Where representable, Core telemetry limits map deterministically:

```text
warning_low   -> soft_low
warning_high  -> soft_high
critical_low  -> hard_low
critical_high -> hard_high
```

A semantic mismatch or unsupported type blocks that telemetry projection before artifact generation.

## 14. obsw-srdb parameter allocation

`obsw_srdb.parameter_id` is a target database allocation.

It is not a field identifier carried inside `TM(3,25)`.

Preflight checks:

```text
1..65535 range already enforced by Profile schema
no duplicate parameter ID inside Profile
no collision with selected baseline parameter registry
derived target name does not collide with a different baseline parameter
```

The canonical Profile uses `0x6001` because `0x4001` is already occupied by baseline `obc_mode`.

Numeric equality with an ID from a different target namespace is not a collision.

## 15. HK set projection

The target HK set contribution record is derived from:

```text
Profile SID
Core packet identity/description
Profile ordered field references
resolved target parameter names
```

The deterministic target name for the reference packet is:

```text
obc_hk
```

The first package resolves:

```text
default_interval_ticks = 0
```

as an Adapter default.

This is deliberately not derived from Core packet period. It avoids creating OpenOBSW scheduling behavior from a Core logical packet timing field.

`spid` remains absent unless a real target requirement establishes an authored allocation policy.

Preflight checks:

```text
HK SID does not collide with baseline
HK target name does not collide with another baseline HK set
all field target parameter names resolve uniquely
field order is explicit and stable
```

## 16. Command projection and existing target reuse

The first Core command maps to:

```text
Core command: obc.ping
flight-contract command ID: 0x1701
PUS target tuple: APID 0x010, service 17, subtype 1
```

The selected target baseline already contains:

```text
are_you_alive
APID 0x010
service 17
subservice 1
parameters []
```

The correct target action is therefore:

```text
reuse_existing
```

not:

```text
contribute_duplicate
```

Preflight resolves the effective TC APID from a binding override or `settings.pus.tc_apid`.

Then it compares the target tuple with baseline telecommands.

If an exact tuple exists:

```text
Core argument shape compatible
    -> reuse existing target record

Core argument shape incompatible
    -> ERROR, target tuple collision with incompatible contract
```

If no tuple exists:

```text
exact target/runtime capability supported
+ tuple/name collision-free
+ command arguments representable
    -> generate new telecommand contribution record

otherwise
    -> ERROR
```

The flight-contract `command_id` remains a distinct ABI namespace and is never compared with SRDB parameter/event/HK IDs.

## 17. TC APID acceptance nuance

The ground/target telecommand database uses APID `0x010` for `TC(17,1)`.

The audited OpenOBSW OrbitFabric contract adapter resolves `OF_CMD_PING` with wildcard route APID `0xFFFF`.

Therefore:

```text
target TC representation APID
!=
mandatory fixed runtime route APID
```

Preflight validates target database tuple compatibility and, where runtime-route compatibility is part of the selected static baseline, confirms that the route policy can accept the target APID.

It must not require TC APID to equal TM APID.

## 18. Event projection

Core owns event severity.

The Profile owns the vocabulary projection:

```text
Core severity -> obsw-srdb Severity
```

The first canonical mapping is:

```text
info     -> INFO
warning  -> MEDIUM
error    -> HIGH
critical -> HIGH
```

`obsw-srdb` then owns:

```text
INFO   -> TM(5,1)
LOW    -> TM(5,2)
MEDIUM -> TM(5,3)
HIGH   -> TM(5,4)
```

For the reference event:

```text
Core warning
    -> MEDIUM
    -> TM(5,3)
```

The target event contribution derives name and description from Core and uses Profile `event_id = 0x5001`.

### safe_trigger

The first package resolves:

```text
safe_trigger = false
```

and records this as Adapter-resolved target behavior metadata.

The Adapter must not automatically convert Core fault recovery into `safe_trigger = true` because `obsw-srdb.safe_trigger` changes OpenOBSW runtime behavior. PR #30 established that OpenOBSW developers own runtime behavior and the Integration Package does not generate it.

Fault/recovery projection is outside the first schema scope.

## 19. Exact PUS message compatibility

A broad service list is insufficient.

Preflight reasons over exact messages:

```text
direction + service + subtype
```

The reference slice requires at least:

```text
TC(17,1)
TM(1,1)
TM(1,7)
TM(17,2)
TM(3,25)
TM(5,3)
```

The selected tested baseline establishes these through pinned OpenOBSW runtime source and pinned `obsw-srdb` codegen behavior.

For command `expected_responses`, every exact response tuple must be supported by the selected baseline.

An unknown or unsupported exact message is an incompatibility even if another subtype of the same PUS service exists.

## 20. TM secondary-header compatibility

OpenOBSW declares:

```text
OBSW_PUS_TM_SEC_HDR_LEN = 11 bytes
```

The audited `obsw-srdb 0.1.0` codegen places application data at:

```text
bit 136
```

which corresponds to:

```text
48-bit CCSDS primary header
+ 88-bit PUS TM secondary header
```

The preflight verifies the relationship between these two external target authorities.

The Adapter does not own the value `11` and does not compute alternative XTCE offsets.

If the target declaration and tested codegen layout diverge, `project` fails before artifact generation.

## 21. Target name collision checks

Target IDs are not the only collision namespace.

Preflight also checks deterministic target names for:

```text
parameters
HK sets
events
new telecommand contribution records
```

Rules:

```text
same target name + same intended target entity
    -> may resolve as reuse if the complete contract is compatible

same target name + different target entity or incompatible definition
    -> ERROR
```

Name collision checks are separate from numeric ID collision checks.

## 22. Deterministic preflight sequence

The target preflight order is:

### P0 - bootstrap integrity

```text
load explicit Core Integration Input manifest
verify required surface records and digests defensively
load exactly the supplied Profile
compute exact Profile SHA-256
strict YAML parse
validate package-local Profile schema
verify Adapter expects the same schema identity/digest
```

### P1 - Core source resolution

```text
resolve every binding {domain,id}
resolve packet membership
resolve telemetry type/unit/limits/description needed by target projection
resolve command arguments
resolve event severity
```

Failures use `source_resolution`.

### P2 - integration-specific Profile semantics

```text
binding uniqueness
C symbol uniqueness
typed allocation uniqueness
TC tuple uniqueness within Profile
HK field legality and uniqueness
severity map monotonicity
domain-specific field legality
```

Failures use `projection_validation` unless schema already owns them.

### P3 - target baseline selection

Resolve:

```text
settings.compatibility.target_baseline
```

to exactly one package-owned baseline resource.

No nearest-version or latest-version selection is allowed.

### P4 - target model compatibility

Verify:

```text
OpenOBSW version supported
obsw-srdb version supported
obsw-srdb schema/model behavior supported
Core telemetry target types representable
TM APID compatible with target baseline
```

### P5 - exact PUS message compatibility

Verify every exact command/response/HK/event message required by the resolved projection.

### P6 - target allocation and name compatibility

Verify independently:

```text
parameter IDs and names
event IDs and names
HK SIDs and names
flight-contract command IDs and C symbols
```

### P7 - telecommand resolution

For each projected command:

```text
resolve effective APID/service/subtype
check existing target tuple
compare target argument contract
choose reuse_existing or contribute_new
```

### P8 - TM layout compatibility

Verify OpenOBSW declared secondary-header layout against the tested `obsw-srdb` codegen layout.

### P9 - contribution consistency

Before writing artifacts verify the complete planned contribution set:

```text
all generated target names unique
all generated target IDs unique within their namespaces
all HK fields resolve to generated or intentionally reused target parameters
all new TC records have free target tuples
no record claims to replace a baseline record
```

### P10 - decision

Only if all required checks pass may target artifact generation start.

Invariant:

```text
required incompatibility or unavailable authority
    -> no target artifact generation
```

Absence of a native target merge API is not a required incompatibility for `project` because target application is outside this operation.

## 23. Check states

Each compatibility check has one of:

```text
compatible
incompatible
unavailable
not_applicable
```

`compatible` means authority exists and satisfies the requirement.

`incompatible` means authority exists and contradicts the requirement.

`unavailable` means the requested operation requires a fact or target capability that cannot be established through a supported boundary.

`not_applicable` means the fact is not required by this operation.

`not_applicable` must not be converted to `compatible` merely to produce a green summary.

For the first `project` operation, native SRDB merge/application capability is `not_applicable`.

## 24. Current canonical outcome

With the current audited upstream baseline, the canonical Profile is expected to pass:

```text
Core/Profile validation
target type representation
TM APID compatibility
exact PUS message compatibility
parameter/event/HK allocation collision checks
command tuple reuse compatibility
TM secondary-header compatibility
contribution consistency
```

Therefore the current design expectation is:

```text
semantic_target_preflight = compatible
srdb_contribution_generation = compatible
native_target_application = not_applicable
required_preflight = passed
artifact_generation_allowed = true
```

The first executable Adapter may therefore be implemented without requiring an OpenOBSW change, provided it keeps contribution generation and target application explicitly separate.

## 25. Diagnostic catalog

Package-owned candidate codes:

### Baseline

```text
OFI-COMP-BASELINE-001
    target baseline missing or unknown

OFI-COMP-BASELINE-002
    package baseline resource invalid or unsupported
```

### Target representation

```text
OFI-PROJ-TYPE-001
    Core telemetry type has no supported obsw-srdb representation

OFI-PROJ-HK-001
    HK field is not a member of the referenced Core packet

OFI-PROJ-HK-002
    HK field has no projected telemetry target representation

OFI-PROJ-SEVERITY-001
    Core event severity cannot be projected through configured target map
```

### PUS and layout

```text
OFI-COMP-PUS-001
    TM APID incompatible with selected baseline

OFI-COMP-PUS-002
    exact required PUS message unsupported

OFI-COMP-PUS-003
    target TC APID/route policy incompatible

OFI-COMP-PUS-004
    OpenOBSW TM secondary-header declaration and tested SRDB codegen layout disagree
```

### Target allocation

```text
OFI-COMP-ALLOC-001
    obsw-srdb parameter ID collision

OFI-COMP-ALLOC-002
    obsw-srdb event ID collision

OFI-COMP-ALLOC-003
    obsw-srdb HK SID collision

OFI-COMP-NAME-001
    deterministic target name collision
```

### Command resolution

```text
OFI-COMP-TC-001
    existing target telecommand tuple has incompatible argument contract

OFI-COMP-TC-002
    projected new telecommand has no compatible target runtime/message capability
```

### SRDB boundary

```text
OFI-COMP-SRDB-001
    obsw-srdb package/model baseline incompatible

OFI-PROJ-SRDB-001
    generated contribution record set is internally inconsistent
```

### Authority

```text
OFI-COMP-AUTH-001
    required compatibility fact cannot be established safely
```

Compatibility failures use:

```text
owner: integration
producer: orbitfabric-openobsw-opensvf
phase: input_compatibility
severity: ERROR
```

unless an earlier generic phase such as `profile_schema`, `source_resolution`, `projection_validation`, or `artifact_generation` is more precise.

## 26. Integration Result behavior

The Integration Result is the only semantic operation result.

No parallel preflight result file becomes a competing authority.

### Failed preflight

When technically possible:

```text
result = failed
Core/Profile provenance retained if established
integration-owned ERROR diagnostics emitted
no target artifacts generated
coverage reflects reliably resolved sources
```

If Core source resolution succeeded, affected entities may use coverage state `blocked` and reference the blocking diagnostic.

If Core entity resolution failed, coverage is `unavailable` or `partial` according to what can be established reliably.

### Successful project

Important resolved choices are recorded through Result `resolutions[]`, including:

```text
target baseline ID
TM APID
TC representation APID
obsw-srdb parameter ID
obsw-srdb event ID
obsw-srdb HK SID
HK field order
event severity projection
resolved event PUS subtype
telecommand action = reuse_existing or contribute_new
TM secondary-header compatibility facts
SRDB handoff mode = contribution_bundle
```

Required artifact kinds for the first slice include:

```text
openobsw_contract_header
obsw_srdb_parameter_contribution
obsw_srdb_hk_set_contribution
obsw_srdb_event_contribution
```

A telecommand contribution artifact is optional when all projected commands resolve by reuse of compatible baseline records.

Every contribution artifact must be labelled so generic or Studio consumers cannot mistake it for a complete/applied target database.

## 27. Projection coverage is not runtime evidence

Static `project` coverage answers what the Adapter projected into target contract/database contribution representations.

It does not answer whether OpenOBSW runtime code currently consumes every generated symbol or whether the contribution records have been applied to a target checkout.

Therefore:

```text
projected
!= applied
!= built
!= runtime materialized
!= verified end-to-end
```

Runtime materialization absence does not by itself downgrade static projection coverage.

Core semantics that the target representation intentionally does not carry may make an entity `partially_projected`.

Examples include operational policy facets such as persistence, downlink priority, command allowed modes, or runtime recovery behavior when those are outside the target artifact scope.

## 28. Runtime-only compatibility

These are not `project` blockers in the first package:

```text
wire protocol v3 machine-readable marker
OBCEmulatorAdapter API version
YamcsBridge API/lifecycle
YAMCS runtime version
OpenSVF campaign execution
live telemetry
commanding
```

They become required only for operations that advertise corresponding runtime or verification capabilities.

The package must not parse log banners, private Python attributes, or README text to fabricate these authorities.

## 29. Optional future obsw-srdb composition boundary

A native `obsw-srdb` composition/extension API would be useful for future automation, but is not required by first `project`.

A suitable future target-owned capability could provide semantics equivalent to:

```text
base complete SRDB
+ one or more validated additive contributions
    -> target-owned collision/reference validation
    -> deterministic complete SRDB
```

Possible future uses include:

```text
automated target application
CI assembly of a complete target database
OpenOBSW build orchestration
runtime/verification operations that require an assembled database
```

The requirement is documented separately in:

```text
docs/design/obsw_srdb_composition_boundary_proposal.md
```

OrbitFabric should consume such a boundary if OpenOBSW adopts one, but must not make Stage 7.2 Adapter delivery depend on it.

## 30. Design validation assets

The machine-readable design resources are:

```text
docs/design/stage7_2_reference_target_baseline.example.json
docs/design/stage7_2_preflight_cases.json
```

They are validated by:

```text
tools/validate_stage7_2_preflight_design.py
```

The validator checks at least:

```text
JSON syntax and design identities
baseline allocation uniqueness
baseline TC tuple uniqueness
exact PUS capability tuple uniqueness
canonical project outcome
project/application separation
case ID uniqueness
diagnostic-code references
absence of the retired native-merge blocker
```

Expected marker:

```text
Stage 7.2 compatibility preflight design validation: PASS
```

## 31. Design acceptance criteria

Stage 7.2 preflight design is ready when:

```text
generic and target-specific preflight are separated
project compatibility is operation-scoped
no raw YAML fallback exists
target baseline selection is explicit and exact
obsw-srdb is the native target data model
Core packet grouping is not mistaken for wire packing order
HK target order is Profile-authored
parameter/event/HK namespaces remain independent
command tuple reuse is distinct from collision
event subtype is derived from target severity projection
exact PUS messages are checked
secondary-header compatibility compares target authorities
runtime-only compatibility does not block project
SRDB contribution generation is distinct from target application
no native target merge API is required for project
preflight failure starts no artifact generation
Integration Result remains the semantic result authority
machine-readable design validation passes
```

## 32. Implementation gate

Do not start the executable Stage 7.2 Adapter until:

```text
Stage 7.1 review state is understood
PR #31 review state is understood
Stage 7.2 design validator passes
```

A native `obsw-srdb` extension/merge API is deliberately not an implementation prerequisite for the first Adapter.

After that gate, Stage 7.2 can introduce coherently:

```text
integration_package.json
exact Profile schema digest
package baseline resource
orbitfabric.adapter_cli.v0 project
Core Integration Input Set consumption
compatibility preflight
mission_contract.h generation
obsw-srdb contribution artifacts
minimum valid integration_result.json
```

No XTCE generation, target checkout mutation, OpenOBSW build, OpenSVF execution, or YAMCS behavior is added to OrbitFabric.
