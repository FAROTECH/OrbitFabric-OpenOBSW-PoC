# Integration Responsibility Matrix

Status: **reviewed reference baseline**
Scope: OrbitFabric Core <-> OpenOBSW/obsw-srdb/OpenSVF/YAMCS Reference Integration

Related architecture work:

- OrbitFabric Core #227: https://github.com/FAROTECH/orbitfabric/issues/227
- OrbitFabric Core #213: https://github.com/FAROTECH/orbitfabric/issues/213
- PoC mapping boundary #1
- PoC runtime materialization discussion #26

---

## 1. Purpose

The PoC and Stage 7 extraction have now demonstrated and implemented the first durable Reference Integration boundary.

This document records the resulting primary ownership of each durable integration responsibility and explicitly separates:

```text
OrbitFabric Core semantics
Projection Profile configuration
integration adapter logic
obsw-srdb target composition
OpenOBSW runtime behavior
OpenSVF verification/runtime behavior
YAMCS ground runtime behavior
PoC-only scaffolding
```

The goal is to prevent PoC implementation details from accidentally becoming product architecture.

---

## 2. Ownership classes

Every relevant responsibility is classified into one primary ownership class:

```text
CORE
PROFILE
ADAPTER
OBSW-SRDB
OPENOBSW
OPENSVF
YAMCS
POC-ONLY
```

### CORE

OrbitFabric Mission Data Contract semantics and Core-owned structured surfaces.

### PROFILE

Version-controlled ecosystem-specific projection data/configuration.

### ADAPTER

Producer-to-downstream transformation, compatibility, traceability, provenance, and integration-owned metadata/artifacts.

### OBSW-SRDB

Target SRDB model, complete-target composition, collision rules, and target code-generation semantics.

### OPENOBSW

Flight/runtime behavior and OpenOBSW-native implementation.

### OPENSVF

Simulation, campaign, bridge and verification behavior owned by OpenSVF.

### YAMCS

YAMCS-native runtime, MDB, commanding, link and archive behavior.


### POC-ONLY

Experimental probes, stage-specific harnesses, duplicated scaffolding or temporary material that should not define the production architecture.

Secondary consumers may exist, but each semantic responsibility must have one clear primary owner.

---

## 3. Responsibility matrix

| Responsibility / concept | Primary owner | Production position | Engineering rule |
|---|---|---|---|
| Mission Model semantics | CORE | OrbitFabric Core | Source of truth; never duplicated by Profile or Adapter. |
| Mission loading / structural validation | CORE | OrbitFabric Core | Adapter consumes Core-owned structured output rather than rebuilding the Mission Model from YAML. |
| Semantic lint findings | CORE | OrbitFabric Core | Must remain distinguishable from integration diagnostics. |
| Entity identity | CORE | Core structured surfaces | Integration mappings anchor to Core semantic entity IDs. |
| Admitted Core relationships | CORE | `relationship_manifest.json` | Integration-specific mappings remain separate unless Core deliberately admits a future relationship family. |
| Complete loaded Mission Model inspection | CORE | Candidate `mission_snapshot.json` | Candidate adapter input; compatibility decision remains governed by Core #224/#227. |
| Ecosystem-specific numeric allocations | PROFILE | Projection Profile | Example: `0x4001`, `0x1701`, `0x5001`; not Core mission truth. |
| Ecosystem-specific C identifiers | PROFILE | Projection Profile | Example: `OF_TM_*`, `OF_CMD_*`, `OF_EVENT_*`, unless a future adapter rule derives them deterministically. |
| PUS service/subservice projection | PROFILE | Projection Profile | Physical ecosystem projection choice. |
| HK set/SID projection metadata | PROFILE | Projection Profile | Must remain distinct from Core packet semantics. |
| SRDB/YAMCS naming choices | PROFILE | Projection Profile | Ecosystem-facing naming/configuration. |
| Target-specific type override | PROFILE | Projection Profile, only where necessary | Default should be deterministic derivation from Core type; explicit override only when justified. |
| Semantic entity → projected target mapping | ADAPTER | Integration Result / traceability | Must be explicit and machine-readable; consumers must not infer it from names/files. |
| Profile-specific validation | ADAPTER | Integration package | Produces integration-owned diagnostics. |
| Core surface compatibility checks | ADAPTER | Integration package | Adapter declares and checks supported input-surface versions. |
| C11 contract artifact generation | ADAPTER | Integration package | Produces extension-owned OpenOBSW-facing artifact. |
| SRDB contribution generation | ADAPTER | Integration package | Produces the integration-owned target contribution; complete-target composition remains downstream-owned. |
| Complete target SRDB composition | OBSW-SRDB | `obsw-srdb` / target tooling | Owns composition, collision rules, and complete-target validity. |
| Target SRDB code generation | OBSW-SRDB | `obsw-srdb` / target tooling | Downstream-owned code-generation semantics. |
| Integration artifact manifest | ADAPTER | Integration Result | Classifies artifact kind, ownership, path/digest and provenance. |
| Projection coverage | ADAPTER | Integration Result | Integration coverage, distinct from Core `coverage_summary.json`. |
| Integration provenance / fingerprints | ADAPTER | Integration Result | Enables reproducibility and staleness decisions. |
| Integration capabilities | ADAPTER | Integration manifest/result | Declares supported Adapter operations/capabilities; native runtime and verification semantics remain downstream-owned. |
| XTCE generation from SRDB | OPENSVF | OpenSVF tooling | Keep current ownership unless OpenSVF deliberately changes it. |
| PUS packet framing / encoding | OPENOBSW | OpenOBSW | Generated contract remains protocol/runtime-logic-free. |
| TC dispatch / command execution | OPENOBSW | OpenOBSW | Adapter maps semantics; OpenOBSW executes behavior. |
| HK production / scheduling | OPENOBSW | OpenOBSW | Not generated by OrbitFabric. |
| Event materialization / PUS S5 reporting | OPENOBSW | OpenOBSW | Profile/adapter provide mapping; runtime event emission stays OpenOBSW-owned. |
| OpenSVF spacecraft loading | OPENSVF | OpenSVF | Integration may provide descriptors/configuration, not a second loader implementation. |
| OpenSVF pipe-mode execution | OPENSVF | OpenSVF | PoC wrappers configure/use it; semantics remain OpenSVF-owned. |
| `YamcsBridge` behavior | OPENSVF | OpenSVF | Future integration reuses supported bridge interfaces rather than duplicating them. |
| Verification campaign execution | OPENSVF | OpenSVF | OrbitFabric integration must not become a second verification engine. |
| Campaign/procedure descriptor instances | ADAPTER | OpenSVF-native artifacts | Integration may generate, assist, discover or reference instances; OpenSVF owns their semantics. |
| YAMCS MDB import | YAMCS | YAMCS | Adapter/OpenSVF provide input; YAMCS owns runtime interpretation. |
| YAMCS TM/TC link behavior | YAMCS | YAMCS | External runtime responsibility. |
| YAMCS command release | YAMCS | YAMCS | Integration tooling may invoke it through supported interfaces; semantics stay YAMCS-owned. |
| YAMCS archive / MDB classification | YAMCS | YAMCS | Integration consumes evidence/results; does not reimplement archive semantics. |
| Verification evidence references | ADAPTER | Integration Result | References native evidence without replacing OpenSVF/YAMCS semantics. |
| Evidence provenance normalization | ADAPTER | Integration Result | Records which inputs/profile/adapter/runtime produced the evidence. |
| Representative packet producers/probes | POC-ONLY | Test/evidence harness | Useful for PoC evidence, not product architecture. |
| Stage-numbered validation wrappers | POC-ONLY | Regression-test source material | Mine for production acceptance tests; do not expose Stage 6.x as product API. |
| Stage-specific Docker sidecars / timeout overrides | POC-ONLY unless separately justified | Integration-test harness | Extract topology/capability knowledge rather than automatically productizing scaffolding. |

---

## 4. Durable production chain

The validated Reference Integration can be reduced architecturally to:

```text
CORE-owned Mission Model / Integration Input Set
        |
        v
PROFILE-owned target projection configuration
        |
        v
ADAPTER-owned mapping + validation + contribution generation
        |
        +-> OpenOBSW-facing contract
        +-> SRDB contribution
        +-> Integration Result
        |
        v
OBSW-SRDB target-owned composition / collision / codegen semantics
        |
        v
OPENOBSW native runtime
        |
        v
OPENSVF native simulation / campaign / bridge / verification
        |
        v
YAMCS native ground runtime
```

The current Stage-numbered PoC scripts remain evidence and regression assets; they are not the public Adapter API.

---

## 5. Historical Projection Profile extraction from `poc_slice.yaml`

The table below preserves the field-by-field extraction analysis that led from the legacy `orbitfabric_models/poc_slice.yaml` mapping layer to the current version-controlled Projection Profile. It is retained as design provenance rather than as a statement that Profile extraction is still pending.

Each field should be classified as one of:

```text
PROFILE-AUTHORED
CORE-DERIVED
ADAPTER-DERIVED
EXTERNAL-DERIVED
TEST-ONLY
REMOVE
```

Initial review:

| Current field | Initial classification | Rationale |
|---|---|---|
| `contract.name` / `contract.version` | PROFILE-AUTHORED | Integration/profile identity. |
| `c_prefix` | PROFILE-AUTHORED | Target generation convention. |
| `of_id` | PROFILE-AUTHORED or ADAPTER-DERIVED | Decide whether symbols are authored/stable or generated by a deterministic naming policy. |
| `of_id_value` | PROFILE-AUTHORED | Target allocation, not Core semantics. |
| `srdb_name` | PROFILE-AUTHORED or defaulted from Core ID | Avoid needless duplication where the Core semantic ID is already a valid target name. |
| `c_type` | ADAPTER-DERIVED unless override required | Prefer deterministic Core-type → C-type projection. |
| `unit` | CORE-DERIVED | Should normally come from Mission Model semantics. |
| `pus_service` / `pus_subtype` | PROFILE-AUTHORED | Physical ecosystem projection choice. |
| `hk_set` / `sid` | PROFILE-AUTHORED mapping tied to a Core packet identity | Preserve distinction between semantic packet identity and target allocation. |
| `sample_rate_hz` | CORE-DERIVED or explicit profile override only where target-specific | Must not silently duplicate semantic timing. |
| `collection_interval_s` | CORE-DERIVED / PROFILE projection depending Core semantics | Requires explicit contract decision. |
| command `arguments` | CORE-DERIVED | Command signature belongs to the Mission Model. |
| `expected_responses` | PROFILE / verification mapping | Physical protocol expectation, not generic Core command semantics. |
| event `severity` | CORE-DERIVED unless target physical mapping differs | Avoid duplicate semantic severity. |
| trigger parameter / condition / threshold | CORE-DERIVED | Trigger/fault semantics belong to the Mission Model; current PoC placeholder duplication should not survive blindly. |

This table is a review input, not a frozen schema.

---

## 6. OpenOBSW/OpenSVF review outcomes and maintenance points

The original review points have been exercised through Stage 7:

1. **SRDB/XTCE boundary** - the Adapter produces an SRDB contribution; complete target composition remains target-owned; OpenSVF retains XTCE-generation semantics on the downstream path.
2. **OpenOBSW generated contract boundary** - generated C artifacts remain contract-only; packet framing, dispatch, HK scheduling, serialization, and event materialization remain OpenOBSW-owned.
3. **OpenSVF runtime descriptors** - integration assets may materialize or reference OpenSVF-native descriptors, but their semantics remain OpenSVF-owned.
4. **YamcsBridge reuse** - the real OpenSVF bridge path was used in the runtime evidence rather than duplicated by the Adapter.
5. **Evidence/campaign APIs** - native OpenSVF campaign execution and `CampaignReport` evidence were exercised in Stage 7.9/7.10.
6. **Compatibility declarations** - the Reference Adapter validates producer, Profile, and pinned target-baseline compatibility before generation.

These outcomes are the current reference boundary. Future target versions may require compatibility-maintenance work without changing the ownership model.

---

## 7. Baseline acceptance

The responsibility matrix is considered satisfied for the current Reference Adapter baseline because:

```text
Every durable selected-slice responsibility has one primary owner.
Projection Profile state is separated from Core-derived semantics.
Adapter responsibilities are separated from obsw-srdb/OpenOBSW/OpenSVF/YAMCS semantics.
PoC scaffolding is explicitly separated from the public Adapter surface.
OpenOBSW/OpenSVF ownership assumptions have been validated where they matter.
```

Future generic contract evolution can build on this boundary without depending on Stage-numbered PoC implementation details.
