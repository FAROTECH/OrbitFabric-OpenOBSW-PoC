# OpenOBSW/OpenSVF Reference Adapter Extraction Plan

Status: architecture extraction plan

Baseline PoC upstream commit: `5400fc0b81b378e028da3a1a681c8fae82e53874`

Related:

- `docs/integration_responsibility_matrix.md`
- `docs/poc_asset_inventory.md`
- `lipofefeyt/OrbitFabric-OpenOBSW-PoC#30`
- `FAROTECH/orbitfabric#227`
- `FAROTECH/orbitfabric#228`
- `FAROTECH/orbitfabric#231`
- `FAROTECH/orbitfabric#233`
- `FAROTECH/orbitfabric#235`
- `FAROTECH/orbitfabric-studio#325`

---

## 1. Purpose

This document defines the extraction plan for the first production-oriented OrbitFabric Integration Package derived from the OrbitFabric ↔ OpenOBSW/OpenSVF/YAMCS PoC.

The objective is **not** to promote the current PoC repository structure into production unchanged.

The objective is to extract the durable concepts already demonstrated by the PoC into an integration package that conforms to the generic OrbitFabric Integration Framework contracts now defined in Core:

```text
Core Integration Input Contract
        +
Projection Profile Contract
        +
Integration Result Contract
        +
Integration Package / Adapter Execution Contract
        ↓
OpenOBSW/OpenSVF reference Integration Package
```

This package will be the first substantial reference implementation of the generic integration architecture. It must therefore validate the architecture rather than introduce OpenOBSW/OpenSVF assumptions back into Core.

---

## 2. Architectural target

The intended production boundary is:

```text
OrbitFabric Core
    owns Mission Model semantics
    emits Core Integration Input Set

Projection Profile
    owns authored OpenOBSW/OpenSVF projection choices

OpenOBSW/OpenSVF Integration Package
    owns target-specific validation, mapping, generation,
    traceability, compatibility, provenance and orchestration

OpenOBSW
    owns flight/runtime/PUS behavior

OpenSVF
    owns verification/runtime integration and its native artifacts

YAMCS
    owns MDB/runtime/commanding/archive behavior

OrbitFabric Studio
    consumes generic package/profile/result contracts
    and may add ecosystem-specific UI contributions
```

The reference package must not create a second Mission Model and must not require OrbitFabric Core to load third-party adapter code in-process.

---

## 3. Current PoC evidence to preserve

The extraction is justified by the PoC already demonstrating a coherent vertical slice across the integration chain.

Representative evidence includes:

```text
OrbitFabric Mission Model
    ↓
PoC mapping/allocation slice
    ↓
generated C flight contract
    + generated OpenSVF-compatible SRDB
    ↓
OpenOBSW / OpenSVF
    ↓
XTCE / YAMCS MDB
    ↓
live telemetry
    + live event telemetry
    + YAMCS-originated telecommand closed loop
```

The current Stage 6 evidence establishes at least:

- generated flight and ground artifacts from one semantic source;
- OpenOBSW-compatible contract materialization;
- OpenSVF SRDB/XTCE/YAMCS flow;
- live HK telemetry reaching YAMCS;
- live event telemetry reaching YAMCS;
- YAMCS-originated TC reaching OpenOBSW and producing visible responses;
- campaign/evidence generation sufficient to prove the thin vertical slice.

These capabilities are the evidence base for extraction. They are not a claim that the existing scripts, Docker layouts or stage numbering are production architecture.

---

## 4. Extraction principles

### 4.1 Extract concepts, not folders

A PoC asset is promoted only when its responsibility survives the Integration Framework ownership model.

The extraction unit is therefore a **responsibility/capability**, not a current file or directory.

### 4.2 Consume Core-owned surfaces only

The production adapter must not reconstruct OrbitFabric semantics from raw Mission YAML when the Core Integration Input Set provides the required information.

Target:

```text
integration_input_manifest.json
        ↓
Core-owned structured surfaces
        ↓
adapter
```

Not:

```text
mission/*.yaml
        ↓
adapter-specific parser
        ↓
reconstructed Mission Model semantics
```

### 4.3 Projection Profile is authored target intent

The current `orbitfabric_models/poc_slice.yaml` is treated as a precursor of the OpenOBSW/OpenSVF Projection Profile, not as a production schema.

It must be decomposed into:

```text
Core-derived semantics
Profile-authored decisions
adapter-derived defaults/materialization
```

Only Profile-authored decisions remain in the Profile instance.

### 4.4 Native ecosystem ownership remains intact

The adapter must produce or orchestrate native OpenOBSW/OpenSVF/YAMCS artifacts and flows without absorbing their runtime responsibilities.

### 4.5 PoC evidence becomes capability-oriented regression evidence

Stage numbers are historical PoC organization.

Production regression names should describe durable capabilities, for example:

```text
live_hk_tm_to_yamcs
live_event_tm_to_yamcs
yamcs_tc_to_openobsw_closed_loop
```

---

## 5. Proposed package identity

Working integration identity:

```text
orbitfabric-openobsw-opensvf
```

This is a working identifier, not yet a repository-name decision.

The package must expose at minimum:

```text
integration_package.json
schemas/
adapter executable
```

and produce, per execution:

```text
integration_result.json
native artifacts
optional integration-owned evidence
```

The exact repository/distribution layout remains a separate implementation decision.

---

## 6. First package capability set

The first extraction should be intentionally narrower than the full long-term Studio vision.

### 6.1 Required initial capabilities

The first reference package should support:

```text
profile_validation
projection
artifact_generation
traceability
```

These are sufficient to prove the production semantic projection boundary.

### 6.2 Capabilities validated in a following increment

After the static projection path is stable, add where the existing PoC evidence supports them:

```text
runtime_discovery
runtime_orchestration
verification_execution
evidence_discovery
```

### 6.3 Live operational capabilities

The following are already demonstrated by the PoC but should enter the package only after the static and verification boundaries are cleanly separated:

```text
live_telemetry
commanding
```

The reference adapter should not turn YAMCS/OpenSVF runtime connectivity into a hidden requirement for basic projection/artifact generation.

---

## 7. Proposed operation model

Operation identifiers remain integration-defined and opaque to generic OrbitFabric consumers.

A candidate first operation is:

```text
project
```

with capabilities:

```text
profile_validation
projection
artifact_generation
traceability
```

A later operation may cover verification/runtime preparation, but its exact identity must follow the OpenSVF boundary review rather than being frozen here.

The generic invocation remains the Core-defined boundary:

```text
<adapter argv...> run
    --operation <operation-id>
    --input-set-manifest <integration_input_manifest.json>
    --profile <projection-profile.yaml>
    --output-dir <directory>
```

---

## 8. Projection Profile extraction from `poc_slice.yaml`

The current PoC slice mixes multiple ownership classes. Extraction should follow the table below.

| Current concept | Production owner | Extraction direction |
| --- | --- | --- |
| contract name/version | Profile | retain as authored integration identity/configuration where required |
| C prefix | Profile | retain as target naming/configuration |
| OrbitFabric entity reference | Profile or adapter-derived | replace ad-hoc string coupling with explicit Core `{domain,id}` references |
| numeric ID allocation | Profile | retain as authored target allocation |
| SRDB name | Profile or deterministic adapter default | allow explicit override, otherwise derive deterministically |
| C type | adapter-derived by default | derive from Core semantics unless target override is required |
| unit | Core-derived | remove duplication from Profile |
| PUS service/subservice | Profile | retain as ecosystem projection decision |
| HK set / SID mapping | Profile | retain where target-specific |
| sample rate | Core-derived unless genuinely target-specific | avoid duplicate Mission semantics |
| collection interval | Core or Profile depending semantic ownership | decide field-by-field rather than duplicate blindly |
| command arguments | Core-derived | do not author again in Profile |
| expected responses | integration/verification mapping | model in integration-specific schema only where needed |
| event severity | Core-derived unless physical target representation differs | prefer Core semantic authority |
| event trigger condition/threshold | Core-derived | do not duplicate in Profile |

The OpenOBSW/OpenSVF Profile schema must be published by the package as local JSON Schema Draft 2020-12, according to the Core Profile schema publication contract.

---

## 9. Adapter decomposition

The current `tools/generate_poc_artifacts.py` proves the concept but combines too many responsibilities.

The production package should separate at least the following internal components:

```text
Core Input reader / compatibility gate
Projection Profile loader
Projection Profile structural validation
integration-specific semantic validation
mapping/resolution layer
flight artifact generator
OpenSVF ground artifact generator
traceability builder
coverage builder
diagnostic collector
provenance/fingerprint collector
Integration Result writer
```

This decomposition is internal to the package. Core and Studio consume only the frozen external contracts.

---

## 10. Flight artifact boundary

The current generated:

```text
generated_artifacts/flight_software/mission_contract.h
```

is the primary flight-side extraction candidate.

The preferred long-term boundary remains **contract-only**:

```text
OrbitFabric/OpenOBSW adapter
    -> generated mission contract artifacts

OpenOBSW
    -> owns PUS framing
    -> owns packet encoding/runtime behavior
    -> owns TC dispatch/execution
    -> owns HK production/scheduling
    -> owns event materialization/runtime
```

The adapter must not become a parallel OpenOBSW runtime implementation.

The exact accepted generated interface is subject to Gonçalo's review in PoC PR #30.

---

## 11. Ground/verification artifact boundary

The current:

```text
generated_artifacts/ground_segment/poc_srdb.yaml
```

is the primary ground-side extraction candidate.

Preferred boundary pending review:

```text
OrbitFabric/OpenOBSW/OpenSVF adapter
    -> OpenSVF-native SRDB input

OpenSVF
    -> owns SRDB interpretation
    -> owns XTCE generation
    -> owns spacecraft/runtime descriptors
    -> owns verification campaign execution

YAMCS
    -> owns MDB import/runtime links/archive/command release
```

The adapter should not generate XTCE directly unless OpenSVF maintainership evidence shows that SRDB is not the appropriate supported long-term boundary.

---

## 12. Traceability model

The package must emit explicit mappings through the generic Integration Result contract.

Core identity remains:

```json
{
  "domain": "...",
  "id": "..."
}
```

Target identities are namespaced and opaque to generic consumers, for example:

```json
{
  "namespace": "openobsw",
  "kind": "command",
  "id": "..."
}
```

or:

```json
{
  "namespace": "yamcs",
  "kind": "parameter",
  "id": "..."
}
```

The exact namespace/kind vocabulary is reference-integration-owned and must be frozen during adapter design.

Mappings must support:

```text
one Core entity -> one target
one Core entity -> many targets
many Core entities -> one target
intentional non-projection
unsupported projection
```

No Studio-side name matching is allowed as a substitute for explicit mappings.

---

## 13. Projection coverage

The package must emit explicit entity-level projection coverage for the Core domains it declares in scope.

Use the generic states:

```text
projected
partially_projected
intentionally_not_projected
not_projected
unsupported
blocked
not_applicable
```

The first production slice must include enough Mission Model variety to demonstrate that these states are meaningful and not merely theoretical.

---

## 14. Integration diagnostics

The package owns only integration diagnostics.

Preserve:

```text
Core diagnostic
!=
integration diagnostic
!=
OpenOBSW/OpenSVF/YAMCS runtime or verification diagnostic
```

The adapter may reference external diagnostics/evidence but must not copy them into a new false semantic authority.

Initial diagnostic classes should cover at least:

```text
incompatible Core input
invalid Profile
unresolved target allocation
unsupported type/materialization
conflicting target IDs/names
artifact generation failure
missing required external capability/tool
```

---

## 15. Provenance and staleness

The package must record the frozen generic provenance axes:

```text
Core Integration Input Set digest
Projection Profile digest
adapter identity/version
integration schema version
native artifact paths + SHA-256
external tool identity/version where relevant
evidence producer/location where relevant
```

Staleness remains derived from fingerprints.

The package must not infer freshness from file timestamps.

---

## 16. Package manifest

The reference package must provide a static:

```text
integration_package.json
```

that can be inspected without executing the adapter.

It should advertise at least:

```text
integration identity
adapter identity/version
Core input compatibility
Projection Profile compatibility
Integration Result compatibility
advertised capabilities
operations
Profile schemas
orbitfabric.adapter_cli.v0 execution prefix
```

It must not contain Mission Model instance semantics or Projection Profile instance state.

---

## 17. External compatibility declarations

The reference package should expose explicit compatibility markers for the external ecosystem rather than hiding them in scripts.

Candidate axes to freeze after maintainer review:

```text
OpenOBSW revision/release compatibility
OpenSVF revision/release compatibility
SRDB schema/version compatibility
YamcsBridge compatibility
YAMCS version assumptions where they materially affect the integration
```

Exact markers must be based on supported upstream interfaces, not arbitrary PoC commit pinning unless no better compatibility contract exists.

---

## 18. Evidence model

The production package should distinguish:

```text
integration-owned evidence
external OpenSVF/YAMCS evidence
```

Integration-owned evidence may include:

```text
projection report
traceability report
coverage report
artifact validation evidence
```

OpenSVF/YAMCS evidence should be referenced rather than duplicated when possible.

The current Stage 5/6 evidence assets remain valuable as regression evidence but should not define the production evidence schema by themselves.

---

## 19. Runtime and verification extraction

Runtime/verification should be extracted only after the static projection operation is stable.

The current PoC runtime assets include:

```text
OpenSVF spacecraft descriptors
OpenSVF campaigns/procedures
YamcsBridge configuration
YAMCS Docker/compose integration
runtime smoke scripts
Stage 6 validators
```

Their likely production treatment is:

```text
supported OpenSVF descriptor interfaces
    -> EXTRACT/REWRITE

campaign semantic requirements
    -> EXTRACT

specific PoC campaigns
    -> TEST-ONLY unless generalized

YamcsBridge integration knowledge
    -> EXTRACT

Docker topology
    -> TEST-ONLY by default

Stage-number validators
    -> REWRITE as capability-oriented regression tests
```

---

## 20. Reference package test matrix

Before declaring the adapter architecture representative, the extracted package should validate at least:

```text
telemetry scalar
unit/scaling/limits
enum telemetry
command arguments
event
fault -> event/recovery trace where supported
multi-parameter housekeeping
multiple HK sets
mode/state mapping where projected
array/structured values if supported
intentionally non-wire entity
one-to-many mapping
many-to-one mapping
unsupported target projection diagnostic
```

The current PoC mission slice is not assumed to cover all of these. Additional representative fixture entities may be required.

---

## 21. Migration of current PoC assets

### 21.1 REFERENCE

Keep as architectural/evidence reference:

```text
README integration narrative
docs mapping/integration vision
current PoC stage evidence summaries
```

### 21.2 EXTRACT

Concepts to move into the reference package architecture:

```text
C flight contract boundary
OpenSVF-compatible SRDB boundary
event materialization expectations
traceability concepts
provenance/evidence concepts
YamcsBridge integration knowledge
```

### 21.3 REWRITE

Do not copy directly:

```text
poc_slice.yaml
raw Mission YAML loading in generator
generate_poc_artifacts.py monolith
OpenSVF descriptor assumptions
runtime pipeline orchestration
```

### 21.4 TEST-ONLY

Retain as regression evidence where useful:

```text
OpenOBSW validators
SRDB/XTCE validators
Stage 5 evidence scripts
Stage 6 runtime validators
current campaigns/procedures
current Docker compositions
```

### 21.5 RETIRE

Do not carry forward without a new justification:

```text
empty execution/docker_compose.yml
empty execution/runner.sh
stage-specific scaffolding with no durable responsibility
```

---

## 22. Proposed extraction phases

### Phase R0 — Boundary review gate

Wait for/resolve PoC PR #30 feedback on:

```text
SRDB -> XTCE ownership
OpenOBSW generated contract boundary
supported OpenSVF integration surfaces
YamcsBridge ownership
compatibility/version declarations
verification evidence ownership
```

Generic framework design does not wait on this gate; ecosystem-specific implementation decisions do.

### Phase R1 — Static reference package skeleton

Create the package skeleton with:

```text
integration_package.json
Profile JSON Schema
adapter CLI entry point
Core Input compatibility gate
Profile validation
failed/success Integration Result writer
```

No OpenOBSW/OpenSVF runtime required yet.

### Phase R2 — Projection and artifact generation

Implement:

```text
Core surface reader
mapping/resolution
C contract generation
OpenSVF SRDB generation
traceability
coverage
diagnostics
provenance
```

Replace raw OrbitFabric YAML parsing.

### Phase R3 — Static equivalence against PoC

For the representative PoC mission:

```text
new adapter outputs
    vs
existing proven PoC outputs
```

Validate semantic equivalence where expected.

Byte-for-byte equality is not required unless the artifact contract explicitly requires it.

### Phase R4 — OpenOBSW integration validation

Confirm the extracted flight contract works with the supported OpenOBSW boundary without moving runtime ownership into the adapter.

### Phase R5 — OpenSVF/YAMCS verification integration

Rebuild the proven ground chain through supported OpenSVF/YAMCS integration surfaces.

### Phase R6 — Capability-oriented live regression

Re-establish:

```text
live_hk_tm_to_yamcs
live_event_tm_to_yamcs
yamcs_tc_to_openobsw_closed_loop
```

through the extracted package.

### Phase R7 — Studio handoff

Only after the Integration Package produces real manifests, schemas and Results should Studio #325 freeze its first concrete integration-provider implementation against them.

---

## 23. Repository placement decision

The final production package should **not automatically remain inside this PoC repository**.

This repository is the evidence/extraction workspace.

Before R1 implementation begins, decide whether the reference integration lives as:

```text
A. dedicated repository
B. dedicated package in a broader OrbitFabric integrations repository
C. another explicitly versioned adjacent distribution unit
```

Selection criteria:

```text
independent release cadence
clear OpenOBSW/OpenSVF ownership boundary
package discoverability
CI isolation
external dependency management
ability to serve as reference implementation
avoid coupling Core release cadence to ecosystem adapter changes
```

A dedicated repository/package is currently the preferred architectural direction, but this document does not freeze the final repository name.

---

## 24. Studio handoff contract

Studio must not depend on PoC internals.

The only production inputs Studio should need are:

```text
integration_package.json
Projection Profile + published JSON Schema
adapter_cli.v0
integration_result.json
```

An OpenOBSW/OpenSVF Studio plugin may provide richer views for:

```text
mapping editor
artifact explorer
continuity graph
coverage dashboard
runtime controls
verification campaign explorer
live telemetry reverse navigation
command flow
```

but it must use the same package and adapter contracts as CLI/CI.

---

## 25. Exit criteria for extraction planning

This planning phase is complete when all of the following are resolved:

- [ ] PoC PR #30 boundary feedback is incorporated or explicitly dispositioned;
- [ ] final package/repository placement is selected;
- [ ] first package identity is frozen;
- [ ] first Profile schema surface is defined;
- [ ] first operation/capability set is frozen;
- [ ] OpenOBSW flight artifact boundary is accepted;
- [ ] OpenSVF ground artifact boundary is accepted;
- [ ] target namespace/kind vocabulary for traceability is defined;
- [ ] external compatibility markers are defined;
- [ ] representative projection test matrix is agreed;
- [ ] R1-R7 implementation sequence is accepted;
- [ ] no PoC-only scaffolding is accidentally classified as production architecture.

---

## 26. Immediate next actions

Until PoC PR #30 receives maintainer feedback, work can proceed on items that do not depend on upstream OpenOBSW/OpenSVF ownership decisions:

1. draft the reference package directory/repository options;
2. draft the OpenOBSW/OpenSVF Profile JSON Schema from the ownership matrix;
3. define candidate package capabilities and initial `project` operation;
4. define target namespace/kind vocabulary for traceability;
5. build the representative projection test matrix;
6. map every current PoC generator input/output to the new framework contracts;
7. prepare the static-equivalence strategy for R3.

Do **not** yet freeze:

```text
SRDB -> XTCE responsibility
supported OpenSVF runtime descriptor APIs
YamcsBridge long-term boundary
OpenSVF campaign/evidence API choices
external compatibility markers that require maintainer guidance
```

---

## 27. Final architectural invariant

The extracted reference integration is successful only if this remains true:

```text
OrbitFabric Core
    remains ecosystem-agnostic

OpenOBSW/OpenSVF Integration Package
    owns ecosystem projection logic

OpenOBSW/OpenSVF/YAMCS
    retain native runtime ownership

Studio
    consumes declared integration contracts
    rather than rebuilding integration semantics
```

The PoC exists to prove the chain. The reference adapter exists to productize the boundary.