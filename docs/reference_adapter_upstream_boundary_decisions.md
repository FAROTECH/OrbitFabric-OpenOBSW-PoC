# OpenOBSW/OpenSVF Reference Adapter — Approved Upstream Boundary Decisions

Status: reviewed architecture baseline

Upstream review source:

- `lipofefeyt/OrbitFabric-OpenOBSW-PoC#30`
- review by OpenOBSW/OpenSVF maintainer Gonçalo Figueiredo
- review state: **APPROVED**
- merged upstream: 2026-08-27

This document records the six OpenOBSW/OpenSVF boundary decisions reviewed in PR #30 and turns them into explicit constraints for the production-oriented OrbitFabric reference integration package.

These decisions refine the OpenOBSW/OpenSVF reference adapter. They do **not** require changes to the generic OrbitFabric Integration Framework contracts already defined in Core.

---

## 1. SRDB → XTCE ownership

### Decision

The OrbitFabric OpenOBSW/OpenSVF integration package produces an **OpenSVF-native SRDB**.

OpenSVF remains the owner of **XTCE generation**.

```text
OrbitFabric Core
    ↓
Projection Profile
    ↓
OpenOBSW/OpenSVF Integration Adapter
    ↓
OpenSVF-native SRDB
    ↓
OpenSVF
    ↓
XTCE
    ↓
YAMCS MDB/runtime
```

### Rationale

The PoC direct-XTCE path duplicated knowledge of the OpenOBSW telemetry packet layout. The observed 88 → 136 bit offset correction demonstrated the failure mode: a second generator can silently drift from the live packet structure.

The production adapter therefore MUST NOT introduce a second independent XTCE representation when OpenSVF already owns that transformation.

### Consequence

The reference adapter may validate that the generated SRDB is consumable by supported OpenSVF versions, but XTCE generation remains an OpenSVF capability and artifact.

---

## 2. OpenOBSW generated flight-contract boundary

### Decision

The `mission_contract.h`-style **contract-only** boundary is accepted as the permanent direction.

The adapter may generate:

```text
numeric IDs
symbolic names
type mappings
contract declarations
```

The adapter MUST NOT generate OpenOBSW flight behavior such as:

```text
PUS handlers
TC dispatch logic
HK scheduling/runtime logic
event-materialization behavior
FDIR behavior
transport behavior
```

### Rationale

OpenOBSW owns real-time C11 behavior. The PoC demonstrated that the numeric/symbolic contract is sufficient for integrating human-written OpenOBSW code with generated mission data.

### Ownership rule

```text
Integration Adapter
    owns generated contract artifacts

OpenOBSW
    owns the runtime meaning and behavior associated with those contracts
```

---

## 3. OpenSVF supported integration surfaces

### Accepted current public surfaces

The following `OBCEmulatorAdapter` lifecycle/API surfaces are considered appropriate long-term integration points based on the PoC:

```text
constructor
initialise()
do_step()
receive_tc()
get_tm_queue()
teardown()
```

The following `YamcsBridge` lifecycle surfaces are also accepted:

```text
constructor
start() / open()
stop() / close()
```

### PoC-only patterns explicitly rejected for production

The following mechanisms MUST NOT become production adapter dependencies:

```text
_parse_tm monkey-patching
_yamcs_bridge private-attribute injection
```

They were valid PoC techniques for proving the path but are not stable integration APIs.

### Required upstream API direction

Before production runtime extraction depends on those paths, OpenSVF should expose explicit public mechanisms equivalent in responsibility to:

```text
TM observation callback / hook
explicit TM sink registration (e.g. set_tm_sink() or equivalent)
```

Exact API names remain OpenSVF-owned.

The OrbitFabric adapter MUST NOT solve the absence of those APIs by creating a permanent private monkey-patch layer.

---

## 4. YAMCS connectivity ownership

### Decision

OpenSVF `YamcsBridge` remains the supported integration boundary for YAMCS connectivity.

The OrbitFabric integration package MUST NOT implement a parallel OrbitFabric-specific YAMCS transport/link stack.

### Proven topology

The PoC has already validated the current bridge topology for the representative slice:

```text
TM:
OpenSVF YamcsBridge TCP server :10015
    ← YAMCS TCP client

TC:
YAMCS UDP output
    → OpenSVF YamcsBridge UDP receiver :10025
```

Exact deployment ports remain environment/configuration concerns rather than generic OrbitFabric semantics.

### Production rule

The reference adapter may configure/orchestrate supported YamcsBridge lifecycle and reference its evidence, but ownership of YAMCS transport behavior remains OpenSVF/YAMCS.

---

## 5. Compatibility declarations

### Decision

The production integration must declare and validate external compatibility explicitly rather than relying on implicit PoC assumptions.

The upstream review identified the following compatibility markers:

| Marker | Authority/source | Purpose |
| --- | --- | --- |
| `openobsw_version` | OpenOBSW build/release metadata | reproducibility and supported-release gate |
| `wire_protocol_version` | OpenOBSW/OpenSVF wire contract | pipe-mode framing compatibility |
| `pus_tm_secondary_header_len` | OpenOBSW declared packet-layout constant | SRDB TM offset derivation |
| supported PUS services | OpenOBSW build/capability declaration | Projection Profile validation |
| `obsw-srdb` package version | OpenOBSW SRDB package | SRDB schema compatibility |
| `OBCEmulatorAdapter` API version | OpenSVF | runtime adapter compatibility |

### Critical marker

`pus_tm_secondary_header_len` is the most safety-critical compatibility value identified during review.

The current PoC value is:

```text
11 bytes for PUS-C
```

This value MUST be **declared by OpenOBSW or a versioned OpenOBSW-owned compatibility surface** and MUST NOT be inferred from magic offsets or duplicated as arbitrary authored Projection Profile state.

If the adapter cannot establish a compatible telemetry secondary-header layout, SRDB projection MUST be blocked rather than continuing with guessed offsets.

---

## 6. Verification evidence ownership

### Decision

The OrbitFabric integration package MUST NOT implement a parallel campaign verification engine.

The primary verification evidence remains OpenSVF-owned.

### Evidence hierarchy

The production integration should reference, where available:

1. **OpenSVF campaign report JSON** — canonical verification evidence, including requirement traceability and pass/fail rows;
2. **YAMCS archive/query results** — packet counts, classification/container observations and other target-runtime evidence;
3. **driver marker logs** — supplementary machine-readable claim markers such as `key: true/false`.

### Integration Result behavior

The OrbitFabric Integration Result should contain evidence references/provenance rather than duplicating or semantically rewriting the OpenSVF campaign report.

```text
Integration Result
    ↓ references
OpenSVF campaign report JSON
YAMCS query/archive evidence
driver marker evidence
```

---

## 7. Confirmed ownership summary

The PR #30 review confirms the responsibility split originally proposed by the architecture extraction:

```text
OrbitFabric Core
    mission semantics and structured integration surfaces

Projection Profile
    authored target-projection decisions

Integration Adapter
    target-specific validation, mapping, generation,
    traceability, compatibility and provenance

OpenOBSW
    flight runtime / PUS / scheduling / event behavior

OpenSVF
    simulation/verification runtime, SRDB→XTCE,
    YamcsBridge and campaign verification

YAMCS
    MDB/runtime/commanding/archive behavior

Studio
    visualization and orchestration over declared contracts
```

No generic Core contract needs to acquire OpenOBSW-, OpenSVF-, PUS- or YAMCS-specific semantics as a consequence of this review.

---

## 8. Effect on reference-adapter extraction phases

The approved review removes the former R0 architecture-review gate.

The extraction sequence can now proceed as:

```text
R0  boundary review
    ✅ COMPLETE / APPROVED

R1  static Integration Package skeleton
R2  Projection Profile validation + semantic resolution
R3  artifact generation + static equivalence
R4  OpenOBSW contract validation
R5  OpenSVF/YAMCS verification integration
R6  capability-oriented live regression
R7  Studio handoff
```

Runtime-facing R5/R6 work remains gated by the public OpenSVF observation/sink APIs documented separately in the compatibility/prerequisites note.
