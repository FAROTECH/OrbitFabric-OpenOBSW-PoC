# Stage 7.1 - OpenOBSW/OpenSVF Projection Profile Schema

Status: implementation candidate on stacked branch `stage7.1/profile-schema`.

Depends on:

```text
Stage 7.0 extraction baseline
PR #31
OrbitFabric Core v1.2.0
Projection Profile Contract 0.1-candidate
PR #30 OpenOBSW/OpenSVF ownership review
```

## 1. Purpose

Stage 7.1 defines the first package-owned structural vocabulary for the OpenOBSW/OpenSVF reference Projection Profile.

The schema validates authored target choices without duplicating OrbitFabric Mission Model semantics and without making the Profile a second OpenOBSW, OpenSVF, SRDB or YAMCS model.

The validation boundary is:

```text
Projection Profile YAML
    -> strict YAML parse
    -> generic Projection Profile envelope
    -> package-local JSON Schema
    -> package semantic invariants
    -> Stage 7.2 Core source resolution and target compatibility preflight
```

## 2. Correct SRDB handoff model

The post-PoC drill-down established that the durable target database boundary must align with the real `obsw-srdb` data model, currently package version `0.1.0` in the OpenOBSW repository.

That model contains typed records for:

```text
spacecraft
parameters
telecommands
hk_sets
events
```

and its code generator derives XTCE containers from those records.

OrbitFabric therefore generates SRDB-compatible target data. OrbitFabric does not generate XTCE.

This corrects an important PoC artifact distinction:

```text
legacy poc_srdb.yaml OpenSVF-only experiment
!=
production obsw-srdb handoff
```

The old PoC artifact remains evidence and migration input only.

## 3. Contract identities

Schema:

```text
integration_package/schemas/profile-0.1.schema.json
```

Dialect:

```text
JSON Schema Draft 2020-12
```

Schema identity:

```text
urn:orbitfabric:integration:openobsw-opensvf:profile-schema:0.1-candidate
```

Runtime interpretation remains keyed by:

```text
integration.id = orbitfabric-openobsw-opensvf
integration.schema_version = 0.1-candidate
```

The canonical reference Profile is now:

```text
profile.id = poc-openobsw-opensvf
profile.version = 0.3.0
```

The Profile revision changed because the target model itself was corrected, not because of a cosmetic edit.

## 4. First-slice support boundary

The first package schema supports the four Core domains exercised by the vertical slice:

```text
telemetry
commands
events
packets
```

The generic Projection Profile contract permits multiple Core sources in one binding. The first OpenOBSW/OpenSVF package schema intentionally supports one Core source per binding.

Target-specific HK field layout may contain multiple explicit Core telemetry references because packing order is a target concern, not a generic binding-source relationship.

## 5. Target-wide settings

The canonical settings are:

```yaml
settings:
  compatibility:
    target_baseline: openobsw-0.7.0-obsw-srdb-0.1.0-reference
  flight_contract:
    c_prefix: OF_
  pus:
    tm_apid: 0x103
    tc_apid: 0x010
  obsw_srdb:
    event_severity_map:
      info: INFO
      warning: MEDIUM
      error: HIGH
      critical: HIGH
```

### Compatibility baseline

`target_baseline` selects one exact tested package-owned compatibility baseline. The Adapter must reject an unknown baseline rather than select a nearby or latest version.

### APIDs

`tm_apid` and `tc_apid` remain distinct target choices.

The current TM APID `0x103` matches the OpenOBSW reference mission TM source APID.

The current TC APID `0x010` matches the reference telecommand database and Stage 6.19 ground representation. OpenOBSW contract routes may still use wildcard APID acceptance, so Stage 7.2 must distinguish ground representation from runtime acceptance policy.

### Event severity projection

Core event severity remains Core-owned.

`event_severity_map` is not a copy of event severity. It is an authored projection policy from the Core severity vocabulary to the `obsw-srdb` severity vocabulary.

The package validator requires the mapping to be non-decreasing:

```text
Core:        info < warning < error < critical
Target:      INFO < LOW < MEDIUM < HIGH
```

The canonical map preserves the proven PoC behavior where the Core `warning` event is projected as OpenOBSW `MEDIUM`, which produces `TM(5,3)`.

## 6. Telemetry parameter binding

A projected telemetry binding uses:

```yaml
config:
  flight_contract:
    c_symbol: OF_TM_OBC_BUS_VOLTAGE_MV
  obsw_srdb:
    parameter_id: 0x6001
```

`parameter_id` is the 16-bit `obsw-srdb` parameter allocation.

It is not a field identifier carried inside `TM(3,25)`.

OpenOBSW Service 3 serializes the HK SID followed by the values of the registered set in order. Therefore telemetry placement in an HK packet belongs to the packet binding, not to a telemetry-level PUS mapping.

The previous Stage 7.1 representation `pus.parameter_id` was removed because it incorrectly suggested a wire-level TM(3,25) identity.

The current `0x6001` value remains useful because `obsw-srdb` itself requires unique parameter IDs and the audited baseline already occupies `0x4001`.

## 7. Housekeeping packet binding and packing order

A projected packet binding uses:

```yaml
config:
  flight_contract:
    c_symbol: OF_HK_SET_OBC
  obsw_srdb:
    hk_set:
      sid: 0x05
      fields:
        - domain: telemetry
          id: eps.obc.bus_voltage_mv
```

This is a critical ownership correction.

OrbitFabric Core packet membership is semantic grouping. Core v0.1 explicitly does not define a real packet protocol or wire packing order.

Therefore the Adapter must not infer wire order from incidental YAML list order.

The ordered `hk_set.fields` list is target-specific Profile configuration. Every field is still identified through Core `{domain,id}` identity.

Stage 7.2 must verify that each field:

```text
resolves in the Core Entity Index
is a member of the referenced Core packet
has a projected telemetry binding
can be represented by obsw-srdb 0.1.0
```

The package does not author `default_interval_ticks` in the first Profile schema. If a valid SRDB record requires it, Stage 7.2 uses a non-behavioral Adapter default of `0` and records that resolution. OrbitFabric does not derive OpenOBSW scheduling behavior from Core packet period.

## 8. Command binding

A projected command uses:

```yaml
config:
  flight_contract:
    c_symbol: OF_CMD_PING
    command_id: 0x1701
  pus:
    service: 17
    subtype: 1
```

`command_id` is the flight-contract ABI allocation used by the generated contract boundary.

The PUS tuple identifies the target telecommand representation.

The current target baseline already contains telecommand `(APID 0x010, service 17, subtype 1)` as `are_you_alive`. Stage 7.2 must resolve the Core command to that existing target when the argument shape is compatible. It must not generate a duplicate SRDB telecommand record merely because the target name differs.

A per-command APID override remains allowed. Otherwise `settings.pus.tc_apid` is used.

## 9. Event binding

A projected event uses:

```yaml
config:
  flight_contract:
    c_symbol: OF_EVENT_VOLTAGE_OUT_OF_BOUNDS
  obsw_srdb:
    event_id: 0x5001
```

The event ID is an `obsw-srdb` event allocation.

Service 5 subtype is derived from:

```text
Core event severity
    -> Profile event_severity_map
    -> obsw-srdb Severity
    -> obsw-srdb severity.pus_subservice
```

The Profile therefore does not duplicate `service: 5`, `subtype: 3` on each event binding.

This preserves Core severity authority while keeping the target vocabulary mapping explicit.

## 10. Flight-contract symbol continuity

Every projected first-slice binding requires an explicit `flight_contract.c_symbol`.

The canonical Profile preserves:

```text
OF_TM_OBC_BUS_VOLTAGE_MV
OF_HK_SET_OBC
OF_CMD_PING
OF_EVENT_VOLTAGE_OUT_OF_BOUNDS
```

Current OpenOBSW PoC integration directly consumes `OF_CMD_PING` and `OF_EVENT_VOLTAGE_OUT_OF_BOUNDS`. These symbols are target ABI choices, not Core identities.

For telemetry, event and HK records, the generated contract numeric value may be resolved from the corresponding typed SRDB allocation. Commands retain a separate `flight_contract.command_id` because `obsw-srdb` telecommands are keyed by APID/service/subservice rather than by a standalone command ID.

## 11. Verification-facing command expectations

A command may declare exact expected TM messages:

```yaml
expected_responses:
  - service: 1
    subtype: 1
  - service: 17
    subtype: 2
  - service: 1
    subtype: 7
```

These are protocol expectations used by compatibility checks and future verification evidence. They are not Core command semantics and do not turn the Integration Package into a verification engine.

Stage 7.2 checks exact message tuples, not only a broad PUS service number.

## 12. Vocabulary deliberately not frozen

The first package schema rejects:

```text
numeric_id
srdb_name
c_type_override
unit
sample_rate_hz
collection_interval_s
command arguments copied from Core
event severity copied per binding
fault or trigger semantics
```

`srdb_name` is still unnecessary because the first package can derive deterministic snake_case target names from Core identity and can resolve existing target telecommands by their PUS tuple. A name override should be added only when a real supported target interface requires it.

`c_type_override` is not needed in the first slice. Target parameter type, PTC and PFC are derived from Core telemetry type according to package rules.

## 13. Stage 7.1 semantic invariants

JSON Schema validates structure, closed vocabulary and ranges.

The package validator additionally enforces:

```text
binding IDs unique
C symbols unique
obsw-srdb parameter IDs unique within Profile
flight-contract command IDs unique
obsw-srdb event IDs unique
obsw-srdb HK SIDs unique
PUS TC tuples unique within Profile
HK fields reference projected telemetry bindings
allocation fields appear only on their valid Core domains
event severity projection is non-decreasing
```

Numeric values may be equal across distinct namespaces. For example an event ID may numerically equal a parameter ID without creating a Profile-local collision.

External baseline collisions remain Stage 7.2-owned.

## 14. External compatibility remains Stage 7.2-owned

Stage 7.1 structural validity does not prove compatibility with an external baseline.

Stage 7.2 must establish at least:

```text
Core {domain,id} resolution
Core packet membership for HK fields
OpenOBSW version compatibility
obsw-srdb package/schema compatibility
TM secondary-header compatibility
exact required PUS message support
parameter/event/HK allocation collision freedom
existing telecommand tuple compatibility
target name collision freedom
```

Runtime-only capabilities such as wire protocol, `OBCEmulatorAdapter` API and `YamcsBridge` are not blockers for the static `project` operation.

## 15. Validation assets

```text
integration_package/schemas/profile-0.1.schema.json
integration_package/tests/profile_schema_cases.json
tools/validate_stage7_1_profile_schema.py
requirements-stage7.txt
```

The current test set covers the canonical Profile plus negative cases for target baseline selection, closed vocabulary, APID ranges, typed SRDB allocations, HK field references, domain legality, C symbol uniqueness, TC tuple uniqueness, severity mapping monotonicity, `do_not_project`, and duplicate identifiers.

Run:

```bash
python3 -m pip install -r requirements-stage7.txt
python3 tools/validate_stage7_1_profile_schema.py
```

Expected final marker:

```text
Stage 7.1 Projection Profile schema validation: PASS
```

The validator prints the exact schema SHA-256. The first executable package will publish that digest in `integration_package.json`.

## 16. Stage 7.1 acceptance criteria

Stage 7.1 is ready for upstream review when:

```text
Draft 2020-12 schema is valid
complete canonical Profile is valid
all schema refs are local/offline
Core semantic copies are rejected
obsw-srdb target namespaces are modeled explicitly
HK packing order is explicit Profile target configuration
no wire parameter ID is invented for TM(3,25)
PUS event subtype is derived through explicit severity projection
known PoC allocation collisions are not promoted blindly
C symbol continuity is explicit
Profile-local invariants are tested
external compatibility remains Stage 7.2-owned
no package manifest or executable Adapter is falsely advertised
```

## 17. Next step

Stage 7.2 turns these rules into executable compatibility preflight before any target artifact generation.

The first coherent executable package will eventually introduce together:

```text
integration_package.json
exact Profile schema digest
orbitfabric.adapter_cli.v0 project operation
Core Integration Input Set consumption
target compatibility preflight
mission_contract.h generation
obsw-srdb-compatible output
minimum valid integration_result.json
```

No raw Mission Model YAML fallback and no OrbitFabric XTCE generator are permitted.
