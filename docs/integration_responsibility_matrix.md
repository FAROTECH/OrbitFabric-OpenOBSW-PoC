# Integration Responsibility Matrix

Status: Architecture extraction draft for review  
Scope: OrbitFabric ↔ OpenOBSW/OpenSVF/YAMCS PoC to production-integration transition

Related architecture work:

- OrbitFabric Core #227: https://github.com/FAROTECH/orbitfabric/issues/227
- OrbitFabric Core #213: https://github.com/FAROTECH/orbitfabric/issues/213
- OrbitFabric Studio #325: https://github.com/FAROTECH/orbitfabric-studio/issues/325
- PoC mapping boundary #1
- PoC runtime materialization discussion #26

---

## 1. Purpose

The PoC has now demonstrated enough of the end-to-end continuity chain that the next engineering task is no longer to broaden the thin vertical slice by default.

The next task is to extract the durable production architecture from the proven PoC.

This document assigns one primary semantic owner to each durable integration responsibility and explicitly separates:

```text
OrbitFabric Core semantics
Projection Profile configuration
integration adapter logic
OpenOBSW runtime behavior
OpenSVF verification/runtime behavior
YAMCS ground runtime behavior
Studio visualization/orchestration
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
OPENOBSW
OPENSVF
YAMCS
STUDIO
POC-ONLY
```

### CORE

OrbitFabric Mission Data Contract semantics and Core-owned structured surfaces.

### PROFILE

Version-controlled ecosystem-specific projection data/configuration.

### ADAPTER

OrbitFabric-to-ecosystem transformation/orchestration logic and extension-owned metadata/artifacts.

### OPENOBSW

Flight/runtime behavior and OpenOBSW-native implementation.

### OPENSVF

Simulation, campaign, bridge and verification behavior owned by OpenSVF.

### YAMCS

YAMCS-native runtime, MDB, commanding, link and archive behavior.

### STUDIO

UI, navigation, visualization and orchestration surfaces only.

### POC-ONLY

Experimental probes, stage-specific harnesses, duplicated scaffolding or temporary material that should not define the production architecture.

Secondary consumers may exist, but each semantic responsibility must have one clear primary owner.

---

## 3. Responsibility matrix

| Responsibility / concept | Primary owner | Production position | Engineering rule |
|---|---|---|---|
| Mission Model semantics | CORE | OrbitFabric Core | Source of truth; never duplicated by profile, adapter or Studio. |
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
| Semantic entity → projected target mapping | ADAPTER | Integration Result / traceability | Must be explicit and machine-readable; Studio must not infer it from names/files. |
| Profile-specific validation | ADAPTER | Integration package | Produces integration-owned diagnostics. |
| Core surface compatibility checks | ADAPTER | Integration package | Adapter declares and checks supported input-surface versions. |
| C11 contract artifact generation | ADAPTER | Integration package | Produces extension-owned OpenOBSW-facing artifact. |
| OpenSVF-compatible SRDB generation | ADAPTER | Integration package | Produces extension-owned OpenSVF-facing artifact. |
| Integration artifact manifest | ADAPTER | Integration Result | Classifies artifact kind, ownership, path/digest and provenance. |
| Projection coverage | ADAPTER | Integration Result | Integration coverage, distinct from Core `coverage_summary.json`. |
| Integration provenance / fingerprints | ADAPTER | Integration Result | Enables reproducibility and staleness decisions. |
| Integration capabilities | ADAPTER | Integration manifest/result | Projection, validation, runtime discovery, verification, evidence, live TM, commanding, etc. |
| XTCE generation from SRDB | OPENSVF | OpenSVF tooling | Keep current ownership unless OpenSVF deliberately changes it. |
| PUS packet framing / encoding | OPENOBSW | OpenOBSW | Generated contract remains protocol/runtime-logic-free. |
| TC dispatch / command execution | OPENOBSW | OpenOBSW | Adapter maps semantics; OpenOBSW executes behavior. |
| HK production / scheduling | OPENOBSW | OpenOBSW | Not generated by OrbitFabric. |
| Event materialization / PUS S5 reporting | OPENOBSW | OpenOBSW | Profile/adapter provide mapping; runtime event emission stays OpenOBSW-owned. |
| OpenSVF spacecraft loading | OPENSVF | OpenSVF | Integration may provide descriptors/configuration, not a second loader implementation. |
| OpenSVF pipe-mode execution | OPENSVF | OpenSVF | PoC wrappers configure/use it; semantics remain OpenSVF-owned. |
| `YamcsBridge` behavior | OPENSVF | OpenSVF | Future integration reuses supported bridge interfaces rather than duplicating them. |
| Verification campaign execution | OPENSVF | OpenSVF | OrbitFabric integration must not become a second verification engine. |
| Campaign/procedure descriptor instances | ADAPTER / integration test assets | OpenSVF-native artifacts | Integration may generate, assist, discover or reference them; OpenSVF owns their semantics. |
| YAMCS MDB import | YAMCS | YAMCS | Adapter/OpenSVF provide input; YAMCS owns runtime interpretation. |
| YAMCS TM/TC link behavior | YAMCS | YAMCS | External runtime responsibility. |
| YAMCS command release | YAMCS | YAMCS | Studio/integration may invoke it through supported interfaces; semantics stay YAMCS-owned. |
| YAMCS archive / MDB classification | YAMCS | YAMCS | Integration consumes evidence/results; does not reimplement archive semantics. |
| Verification evidence references | ADAPTER | Integration Result | References native evidence without replacing OpenSVF/YAMCS semantics. |
| Evidence provenance normalization | ADAPTER | Integration Result | Records which inputs/profile/adapter/runtime produced the evidence. |
| Integration visualization | STUDIO | Studio plugin | Reads generic integration contracts. |
| Contract continuity graph rendering | STUDIO | Studio plugin | Uses explicit adapter traceability. |
| Mapping editor UI | STUDIO | Studio plugin | Edits/validates Profile-owned state; never creates hidden Studio-only integration semantics. |
| Runtime controls exposed in UI | STUDIO + external adapters | Studio plugin | Studio orchestrates; external systems own runtime semantics. |
| Projection coverage dashboard | STUDIO | Studio plugin | Renders adapter-owned coverage; does not compute private coverage semantics. |
| Staleness indicators | STUDIO | Studio plugin | Renders adapter-result provenance/fingerprint status; does not guess from timestamps. |
| Representative packet producers/probes | POC-ONLY | Test/evidence harness | Useful for PoC evidence, not product architecture. |
| Stage-numbered validation wrappers | POC-ONLY | Regression-test source material | Mine for production acceptance tests; do not expose Stage 6.x as product API. |
| Stage-specific Docker sidecars / timeout overrides | POC-ONLY unless separately justified | Integration-test harness | Extract topology/capability knowledge rather than automatically productizing scaffolding. |

---

## 4. Durable production chain

The current PoC can be reduced architecturally to the following durable chain:

```text
CORE-owned Mission Model / structured surfaces
        ↓
PROFILE-owned projection configuration
        ↓
ADAPTER-owned mapping + validation + generation + traceability + provenance
        ↓
        ├── OpenOBSW-facing contract artifacts
        └── OpenSVF-facing ground/verification artifacts
                ↓
OPENOBSW / OPENSVF / YAMCS native execution
                ↓
ADAPTER-owned normalized integration result / evidence references
                ↓
STUDIO visualization and orchestration
```

This is the production architecture to refine under OrbitFabric Core #227.

The current PoC stage scripts are evidence and test assets; they are not the production API.

---

## 5. Projection Profile extraction from `poc_slice.yaml`

The existing `orbitfabric_models/poc_slice.yaml` is the strongest concrete precursor of a Projection Profile, but its fields must not be copied blindly into a production schema.

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

## 6. OpenOBSW/OpenSVF review points

The following boundaries should be reviewed with Gonçalo before the production contract is frozen:

1. **SRDB/XTCE boundary** — confirm the preferred production path remains integration-generated OpenSVF-compatible SRDB followed by OpenSVF-owned XTCE generation.
2. **OpenOBSW generated contract boundary** — confirm `mission_contract.h`-style outputs should remain contract-only while packet framing, dispatch, HK scheduling and event materialization remain OpenOBSW-owned.
3. **OpenSVF runtime descriptors** — identify which descriptor/campaign interfaces are appropriate long-term public integration points versus PoC conveniences.
4. **YamcsBridge reuse** — confirm the real bridge path should remain the reusable integration boundary rather than being duplicated on the OrbitFabric side.
5. **Evidence/campaign APIs** — identify which OpenSVF evidence interfaces should be referenced directly by an Integration Result.
6. **Compatibility declarations** — identify the OpenOBSW/OpenSVF/SRDB versions or compatibility markers the production adapter should declare.

No production OpenOBSW/OpenSVF change is requested by this document. The immediate goal is ownership agreement before implementation.

---

## 7. Acceptance criteria

This responsibility matrix is ready to feed the Core #227 contract design when:

```text
Every durable PoC responsibility has one primary semantic owner.
Projection Profile state is separated from Core-derived semantics.
Adapter responsibilities are separated from OpenOBSW/OpenSVF/YAMCS runtime behavior.
PoC scaffolding is explicitly separated from production architecture.
Studio is confirmed as consumer/orchestrator, not semantic owner.
OpenOBSW/OpenSVF ownership assumptions have been reviewed where they matter.
```

The next contract work can then define the concrete Projection Profile and Integration Result schemas without depending on Stage-numbered PoC implementation details.
