# OpenOBSW/OpenSVF Reference Adapter — Compatibility and Upstream Prerequisites

Status: production-readiness checkpoint

Related:

- `docs/reference_adapter_upstream_boundary_decisions.md`
- `docs/reference_adapter_extraction_plan.md`
- `lipofefeyt/OrbitFabric-OpenOBSW-PoC#30`
- `FAROTECH/orbitfabric#227`

This note separates **external compatibility facts** from **Projection Profile authored state** and identifies the upstream API work that must exist before the PoC runtime techniques can become production adapter dependencies.

---

## 1. Compatibility is not Projection Profile state

The Projection Profile owns authored target-projection choices.

External tool/build facts are different.

For example:

```text
Profile-authored
    numeric allocation
    PUS service/subservice choice
    HK SID
    target naming override
    target APID allocation where authored by mission/integration policy

External compatibility fact
    OpenOBSW release/version
    pipe wire protocol version
    TM secondary-header length
    supported PUS-service capability set
    obsw-srdb schema/package version
    OpenSVF adapter API version
```

The adapter MUST NOT copy external compatibility facts into the Projection Profile merely because they influence artifact generation.

---

## 2. Required OpenOBSW compatibility surface

The reference adapter needs a versioned, machine-readable way to resolve the OpenOBSW facts that affect generated artifacts and runtime compatibility.

Minimum required facts:

```text
openobsw_version
wire_protocol_version
pus_tm_secondary_header_len
supported_pus_services
obsw_srdb_version
```

The exact upstream representation remains OpenOBSW-owned.

Acceptable implementation directions include a generated build manifest, exported constants plus a machine-readable query tool, or another versioned OpenOBSW-owned compatibility artifact.

The OrbitFabric integration MUST consume an authoritative declaration rather than scraping implementation files when a supported machine-readable surface exists.

---

## 3. TM secondary-header length is a hard projection gate

The current reviewed value is:

```text
pus_tm_secondary_header_len = 11 bytes
```

for the current PUS-C OpenOBSW layout.

This value affects the bit position of telemetry parameters materialized into SRDB/XTCE.

A stale value can therefore produce a dangerous failure mode:

```text
Profile valid
SRDB syntactically valid
XTCE syntactically valid
YAMCS MDB loads
BUT parameter offsets are wrong
```

The production adapter must fail closed.

Conceptually:

```text
OpenOBSW compatibility declaration
    ↓
pus_tm_secondary_header_len
    ↓
SRDB layout derivation
    ↓
artifact provenance
```

If the value is unavailable or incompatible:

```text
SRDB generation = blocked
Integration diagnostic = error
coverage for affected projection = blocked
Integration Result = failed or partial according to operation semantics
```

The adapter MUST NOT fall back to the PoC's historical 11-byte value as an unverified magic constant.

---

## 4. Supported PUS services are a semantic Profile-validation gate

A structurally valid Projection Profile can still request a PUS service/subservice that the selected OpenOBSW build does not provide.

Validation therefore occurs in two layers:

```text
JSON Schema
    validates shape/ranges

adapter semantic validation
    validates requested service/subservice against
    the selected OpenOBSW compatibility declaration
```

Example:

```text
Profile requests PUS S17
OpenOBSW build declares S17 unsupported
    ↓
profile semantic validation error
    ↓
projection blocked for the affected binding
```

This is an integration diagnostic, not a Core diagnostic.

---

## 5. OpenSVF runtime API prerequisite A — TM observation

### PoC mechanism

The PoC used private `_parse_tm` monkey-patching to observe telemetry at the required point in the runtime path.

### Production position

This MUST NOT become a permanent reference-adapter dependency.

OpenSVF should expose a first-class public TM observation mechanism, such as a callback/hook/subscription API associated with `OBCEmulatorAdapter`.

The exact API is OpenSVF-owned.

The required capability is:

```text
register observer
    ↓
receive decoded/observable TM event
    ↓
no replacement of private methods
    ↓
normal OpenSVF processing continues
```

### Gate

Runtime extraction that requires TM observation remains **blocked for production** until a supported public API exists or the maintainer explicitly identifies another existing public surface.

Static projection and artifact-generation work does not depend on this gate.

---

## 6. OpenSVF runtime API prerequisite B — explicit TM sink wiring

### PoC mechanism

The PoC injected a private `_yamcs_bridge` attribute into runtime objects to route telemetry toward YAMCS.

### Production position

This MUST NOT become a stable integration contract.

OpenSVF should expose an explicit public mechanism equivalent in responsibility to:

```text
set_tm_sink(...)
```

or another maintainer-owned connection API.

The API should allow the supported `YamcsBridge` to be connected without external mutation of private attributes.

### Gate

Production runtime/YAMCS orchestration remains gated on a supported public sink/wiring mechanism.

Again, this does not block static Projection Profile validation or artifact generation.

---

## 7. YamcsBridge remains the runtime transport authority

Once the explicit public wiring API exists, the reference integration should orchestrate the existing OpenSVF `YamcsBridge` rather than replacing it.

The package may need to declare/check a compatible YamcsBridge/OpenSVF API version, but it MUST NOT own a second YAMCS protocol implementation.

---

## 8. Compatibility data in Integration Result provenance

The Integration Result should capture the compatibility facts actually exercised by an operation.

Candidate external provenance records include:

```text
openobsw_version
wire_protocol_version
pus_tm_secondary_header_len
supported_pus_services digest/list identifier
obsw_srdb_version
opensvf_version
obc_emulator_adapter_api_version
yamcs_bridge_api/version where available
yamcs_version where materially relevant
```

These are historical operation provenance, not mutable Profile state.

A later Studio consumer can use them to explain why an old Integration Result is incompatible with the currently selected runtime ecosystem.

---

## 9. Production prerequisite matrix

| Prerequisite | Owner | Blocks static Profile validation | Blocks artifact generation | Blocks runtime/verification extraction |
| --- | --- | ---: | ---: | ---: |
| OpenOBSW version declaration | OpenOBSW | no | conditional | yes |
| wire protocol version | OpenOBSW/OpenSVF | no | no | yes |
| `pus_tm_secondary_header_len` declaration | OpenOBSW | no | **yes for SRDB** | yes |
| supported PUS services declaration | OpenOBSW | **yes for semantic validation** | yes for affected bindings | yes |
| `obsw-srdb` version | OpenOBSW | no | **yes for compatible SRDB** | yes |
| OBCEmulatorAdapter API version | OpenSVF | no | no | yes |
| public TM observation API | OpenSVF | no | no | **yes where observation required** |
| public TM sink/wiring API | OpenSVF | no | no | **yes for production YAMCS forwarding orchestration** |
| YamcsBridge supported lifecycle | OpenSVF | no | no | yes |

---

## 10. Immediate implementation sequence

The upstream prerequisites do not justify pausing the reference-adapter extraction.

The correct sequence is:

```text
NOW
    package/profile loader
    JSON Schema validation
    Core source resolution
    integration semantic validation
    allocation collision checks

THEN
    compatibility-input abstraction
    OpenOBSW declared constants/capabilities
    contract + SRDB generation
    static equivalence against Stage 6.20 baseline

LATER / gated by OpenSVF public APIs
    runtime observation
    YamcsBridge wiring/orchestration
    verification execution
    live regression
```

This keeps upstream API cleanup off the critical path for the static production adapter while ensuring PoC-only private hooks never become accidental permanent architecture.
