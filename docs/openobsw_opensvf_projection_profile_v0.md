# OpenOBSW/OpenSVF Projection Profile v0 — Field Audit and Candidate Schema

Status: reference-adapter extraction candidate; OpenOBSW/OpenSVF boundary review pending  
Generic Profile contract: `FAROTECH/orbitfabric` `docs/reference/projection-profile-contract.md`  
Extraction plan: `docs/reference_adapter_extraction_plan.md`  
PoC review gate: `lipofefeyt/OrbitFabric-OpenOBSW-PoC#30`

---

## 1. Purpose

This document defines the first integration-specific Projection Profile candidate for the OpenOBSW/OpenSVF reference adapter.

It is derived from the current PoC `orbitfabric_models/poc_slice.yaml`, but it is intentionally **not** a field-for-field copy.

The extraction rule is:

```text
Core-derived semantics
    stay in OrbitFabric Core

Profile-authored target decisions
    stay in the Projection Profile

adapter-derived deterministic representation
    stays in adapter logic and is reported in Integration Result provenance

runtime / verification behavior
    stays with OpenOBSW / OpenSVF / YAMCS unless explicit integration configuration is required
```

The candidate must preserve the generic authority rule:

```text
Mission Model
    = semantic authority

Projection Profile
    = authored target intent

Integration Adapter
    = projection/materialization logic

Integration Result
    = resolved truth + provenance
```

---

## 2. Source material audited

The design was checked against:

- `orbitfabric_models/poc_slice.yaml`;
- `orbitfabric_models/mission/telemetry.yaml`;
- `orbitfabric_models/mission/commands.yaml`;
- `orbitfabric_models/mission/events.yaml`;
- `orbitfabric_models/mission/faults.yaml`;
- `orbitfabric_models/mission/packets.yaml`;
- `tools/generate_poc_artifacts.py`;
- Core Projection Profile Contract `0.1-candidate`;
- Core Projection Profile Schema Publication contract.

The PoC currently mixes target allocation, duplicated Core semantics, naming overrides, generated representation choices and verification expectations in one file. The v0 candidate separates them.

---

## 3. Important corrections discovered by the audit

### 3.1 Core command identity is `obc.ping`

The Mission Model command is:

```text
commands / obc.ping
```

The PoC value:

```text
dhs.obc.ping
```

is an SRDB/target name and must not be used as Core identity.

Therefore the candidate binding source is:

```yaml
sources:
  - domain: commands
    id: obc.ping
```

and `dhs.obc.ping` is an optional target-name override.

### 3.2 Housekeeping is already a Core packet entity

The Mission Model already owns:

```text
packets / obc_hk
period = 1s
telemetry = [eps.obc.bus_voltage_mv]
```

The production Profile must not reconstruct this packet from a target-side `parameters` list.

The housekeeping projection is anchored to:

```yaml
sources:
  - domain: packets
    id: obc_hk
```

The adapter obtains membership and semantic period from Core.

### 3.3 PUS TM[3,25] belongs to packet materialization

The PoC stores PUS service/subtype on the telemetry parameter. That was useful for the thin slice, but it conflates parameter semantics with report-packet materialization.

For v0:

```text
telemetry parameter binding
    owns target parameter allocation / optional naming representation

housekeeping packet binding
    owns SID + PUS service/subservice for the report packet
```

The adapter can propagate packet context to member parameters when producing OpenSVF-native artifacts.

### 3.4 Event trigger semantics remain in Core

The Mission Model already owns the fault condition:

```text
eps.voltage_out_of_bounds_fault
    telemetry = eps.obc.bus_voltage_mv
    operator = >
    value = 3500
    debounce_samples = 3
    emits = eps.voltage_out_of_bounds
```

Therefore the Profile must not repeat:

```text
parameter
condition
threshold
severity
```

The event binding only describes target event materialization, for example numeric event allocation and PUS S5 mapping.

### 3.5 Stable APID allocations must not remain hidden adapter state

The PoC generator currently hard-codes target APID allocations such as:

```text
EPS -> 0x100
AOCS -> 0x101
TTC -> 0x102
OBDH -> 0x103
THERMAL -> 0x104
```

The source-domain-to-target-domain naming convention may be a deterministic adapter default.

An APID used as persistent external allocation is different: when relied upon by the integration, it belongs in version-controlled Profile state.

The v0 candidate therefore allows target-wide OpenSVF APID allocations under `settings.opensvf.domain_apids`.

---

## 4. Field-by-field disposition of `poc_slice.yaml`

| PoC field | Classification | v0 disposition | Rationale |
|---|---|---|---|
| `contract.name` | authored Profile lifecycle | `profile.id` | Profile instance identity, not target artifact semantics |
| `contract.version` | authored Profile lifecycle | `profile.version` | Human/version-control lifecycle revision |
| `contract.c_prefix` | authored target-wide representation | `settings.flight_contract.c_symbol_prefix` | Target naming policy |
| telemetry `name` | PoC lookup convenience | remove | Core source is `{domain,id}` |
| telemetry `of_id` | adapter-derived by default | omit; optional `c_symbol` override | Deterministic from Core ID + prefix where possible |
| telemetry `of_id_value` | authored stable allocation | `config.numeric_id` | Persistent target parameter allocation |
| telemetry `srdb_name` | adapter-derived unless override | optional `config.srdb_name` | Core ID is preferred default |
| telemetry `c_type` | adapter-derived | remove; optional future representation override | Derive from Core type; no duplicate semantic type |
| telemetry `unit` | Core-derived | remove | Core owns unit |
| telemetry `pus_service` | wrong PoC ownership level | move to packet binding | PUS HK report is packet materialization |
| telemetry `pus_subtype` | wrong PoC ownership level | move to packet binding | Same as above |
| telemetry `hk_set` | Core-derived relationship | remove | Core packet already owns membership |
| telemetry `sample_rate_hz` | Core-derived | remove | Core telemetry sampling is authoritative |
| HK `name` | PoC lookup convenience | Core packet source `packets/obc_hk` | Packet identity already exists |
| HK `of_id` | adapter-derived by default | optional `c_symbol` override | Deterministic representation |
| HK `sid` | authored stable allocation | `config.sid` | Target packet/SID allocation |
| HK `collection_interval_s` | Core-derived | remove | `packets/obc_hk.period` is authoritative |
| HK `parameters[]` | Core-derived | remove | packet telemetry membership is Core-owned |
| command `name` | PoC leaf-ID lookup | remove | Core source is `commands/obc.ping` |
| command `of_id` | adapter-derived by default | optional `c_symbol` override | Deterministic representation |
| command `of_id_value` | authored stable allocation | `config.numeric_id` | Persistent target command allocation |
| command `srdb_name` | target naming override | optional `config.srdb_name` | Needed for current `dhs.obc.ping` name |
| command `pus_service` | authored protocol projection | `config.pus.service` | Target protocol choice |
| command `pus_subtype` | authored protocol projection | `config.pus.subservice` | Target protocol choice |
| command `arguments` | Core-derived | remove | Core command signature authority |
| command `expected_responses[]` | verification/integration config | structured `config.verification.expected_telemetry[]` | Protocol-facing verification expectation, not command semantics |
| event `name` | PoC leaf-ID lookup | remove | Core source is `events/eps.voltage_out_of_bounds` |
| event `of_id` | adapter-derived by default | optional `c_symbol` override | Deterministic representation |
| event `of_id_value` | authored stable allocation | `config.numeric_id` | Persistent event allocation |
| event `srdb_name` | target naming override | optional `config.srdb_name` | Current target name differs from Core ID |
| event `pus_service` | authored protocol projection | `config.pus.service` | Target PUS event materialization |
| event `pus_subtype` | authored protocol projection | `config.pus.subservice` | Target PUS event materialization |
| event `severity` | Core-derived | remove | Core event severity is authoritative |
| event `trigger.parameter` | Core/fault-derived | remove | Fault semantics belong to Core |
| event `trigger.condition` | Core/fault-derived | remove | Fault semantics belong to Core |
| event `trigger.threshold_mv` | Core/fault-derived | remove | Threshold already belongs to Core fault/telemetry semantics |

---

## 5. Candidate full Profile shape

The candidate Profile follows the frozen generic envelope exactly:

```yaml
kind: orbitfabric.projection_profile
profile_version: 0.1-candidate

profile:
  id: poc-openobsw-opensvf
  version: 0.1.0

integration:
  id: orbitfabric-openobsw-opensvf
  schema_version: 0.1-candidate

settings:
  flight_contract:
    c_symbol_prefix: OF_
  opensvf:
    domain_apids:
      EPS: 0x100

bindings:
  ...
```

Target-specific fields exist only under:

```text
settings
bindings[].config
```

---

## 6. Integration-specific binding kinds

The initial reference schema intentionally supports only the durable projection kinds demonstrated by the PoC.

### `telemetry_parameter`

Source requirement:

```text
exactly one Core source
source.domain = telemetry
```

Candidate config:

```yaml
kind: telemetry_parameter
numeric_id: 0x4001
srdb_name: optional.target.name
c_symbol: OPTIONAL_EXPLICIT_SYMBOL
```

`numeric_id` is required in the first reference adapter because the PoC demonstrates a stable parameter ID used by flight/ground artifacts.

`srdb_name` and `c_symbol` are overrides; absence means adapter deterministic defaults.

### `housekeeping_packet`

Source requirement:

```text
exactly one Core source
source.domain = packets
```

Candidate config:

```yaml
kind: housekeeping_packet
sid: 0x01
pus:
  service: 3
  subservice: 25
c_symbol: OPTIONAL_EXPLICIT_SYMBOL
```

The adapter derives:

```text
packet membership
packet semantic timing
member Core types/units
```

from Core.

Optional target ordering, if ever needed, must be represented explicitly in target config; incidental `sources[]` or Core-file order must not acquire hidden target semantics.

### `command`

Source requirement:

```text
exactly one Core source
source.domain = commands
```

Candidate config:

```yaml
kind: command
numeric_id: 0x1701
srdb_name: dhs.obc.ping
pus:
  service: 17
  subservice: 1
verification:
  expected_telemetry:
    - role: acceptance
      service: 1
      subservice: 1
    - role: execution_complete
      service: 1
      subservice: 7
    - role: command_response
      service: 17
      subservice: 2
```

The verification block is optional. It captures external protocol/campaign expectations and does not redefine Core command semantics.

### `event`

Source requirement:

```text
exactly one Core source
source.domain = events
```

Candidate config:

```yaml
kind: event
numeric_id: 0x5001
srdb_name: eps.obc.voltage_out_of_bounds
pus:
  service: 5
  subservice: 3
```

No trigger or severity duplication is permitted.

---

## 7. Target-wide settings

### `settings.flight_contract.c_symbol_prefix`

Authored naming policy for generated C contract symbols.

The adapter should derive symbols deterministically from:

```text
prefix + target kind + normalized Core ID
```

unless a binding explicitly supplies `config.c_symbol`.

### `settings.opensvf.domain_apids`

Version-controlled target APID allocations.

Example:

```yaml
opensvf:
  domain_apids:
    EPS: 0x100
```

The candidate does not require allocations for unused domains.

The adapter must report a diagnostic if a projected OpenSVF domain requires an APID and no deterministic/allowed allocation policy can resolve it.

No hidden mutable allocator is permitted for externally significant IDs.

---

## 8. What the Profile deliberately does not contain

The first candidate rejects duplication of:

```text
telemetry unit
telemetry semantic type
telemetry limits
telemetry sampling
packet period
packet member list
command arguments
command allowed modes
command timeout/risk/effects
event semantic severity
fault threshold/operator/debounce
fault recovery
Core relationships
```

It also does not contain generated truth such as:

```text
resolved C type
resolved C symbol when defaulted
resolved SRDB name when defaulted
resolved OpenSVF dtype
resolved valid range
artifact paths/digests
coverage state
traceability target nodes
```

Those values belong in the Integration Result when useful for provenance/explanation.

---

## 9. JSON Schema responsibility vs adapter semantic validation

The accompanying JSON Schema validates structural rules such as:

```text
generic envelope shape
integration identity/version constants
settings shape
binding intent shape
binding source cardinality/domain for supported projection kinds
required target allocations
PUS integer ranges
verification response record structure
no unexpected target-specific keys
```

The adapter must still perform semantic validation that JSON Schema cannot reliably own, including:

```text
Core source resolution against Entity Index
numeric ID collisions across bindings
SID collisions
APID collisions where policy forbids reuse
compatibility with Core Input Set/surface versions
packet membership and target materialization support
whether Core semantic type can be represented by the target
whether a referenced source domain is supported by the selected target kind
whether command verification expectations are supported by OpenSVF
whether target names are legal/unique in actual OpenSVF/SRDB context
OpenOBSW/OpenSVF/YAMCS version compatibility
```

Schema diagnostics and projection diagnostics remain separate.

---

## 10. `do_not_project`

The generic Profile distinction is preserved:

```text
binding absent
!=
intentional do_not_project
```

A `do_not_project` binding:

```yaml
- id: example.intentional-exclusion
  intent: do_not_project
  sources:
    - domain: telemetry
      id: some.core.id
  reason: Explicit project decision
  config: {}
```

may reference a Core domain outside the four initially projectable kinds because it records authored exclusion rather than claiming adapter support for projection.

---

## 11. Candidate PoC migration

The current thin slice becomes conceptually:

```text
Core telemetry eps.obc.bus_voltage_mv
    + Profile numeric parameter allocation 0x4001

Core packet obc_hk
    + Profile SID 0x01
    + Profile PUS TM[3,25]

Core command obc.ping
    + Profile command allocation 0x1701
    + Profile SRDB name dhs.obc.ping
    + Profile PUS TC[17,1]
    + optional structured verification expectations

Core event eps.voltage_out_of_bounds
    + Profile event allocation 0x5001
    + Profile target name eps.obc.voltage_out_of_bounds
    + Profile PUS TM[5,3]

Core fault eps.voltage_out_of_bounds_fault
    remains Core-owned semantic trigger/recovery context
```

This is a strict reduction of duplicated authored state compared with `poc_slice.yaml`.

---

## 12. Pending review-dependent points

The following are intentionally not treated as final until PoC PR #30 receives OpenOBSW/OpenSVF review:

```text
whether SRDB name override remains the preferred OpenSVF-facing naming boundary
whether XTCE remains fully OpenSVF-owned downstream of SRDB
whether the flight contract should keep numeric IDs exactly as modeled here
whether OpenSVF domain/APID configuration should remain Profile-authored in this exact shape
which OpenSVF compatibility/version markers the package must expose
which command verification expectations belong in Profile versus OpenSVF campaign assets
```

The generic Core contracts do not depend on these choices.

---

## 13. Candidate artifacts

This design is accompanied by:

```text
schemas/openobsw_opensvf_projection_profile_v0.schema.json
orbitfabric_models/profiles/openobsw_opensvf_poc_v0.yaml
```

They are architecture/reference-adapter candidates, not yet production package API.

The schema is intended to become package-owned once the reference Integration Package repository/layout is chosen.
