# Stage 7 - Reference Integration Package Extraction

Status: **in progress**

Baseline:

```text
OrbitFabric Core v1.2.0
PoC Stage 6.20 final integration evidence
PR #30 Integration Responsibility Matrix and Systematic PoC Asset Inventory
OpenOBSW/OpenSVF ownership review approved by Goncalo
```

## 1. Purpose

Stage 7 transitions the repository from progressive PoC runtime probing to extraction of the durable OrbitFabric OpenOBSW/OpenSVF reference integration.

Stage 7 does not add another Stage 6.x runtime experiment by default.

The proven PoC is now treated as engineering evidence and regression material. Production-oriented work is organized around the OrbitFabric v1.2 integration contracts:

```text
Core Integration Input Set
    -> Projection Profile
    -> Integration Package / Adapter
    -> Integration Result
    -> OpenOBSW / OpenSVF / YAMCS native execution
```

The extension contracts remain independently versioned `0.1-candidate`. OrbitFabric Core v1.2.0 stabilizes the Core Integration Input boundary, not the external Integration Package, Projection Profile or Integration Result contracts.

## 2. Stage 6 closure baseline

The PoC runtime phase has already proven representative continuity for all three selected directions:

```text
Telemetry
  eps.obc.bus_voltage_mv
  -> OpenOBSW TM(3,25)
  -> OpenSVF YamcsBridge
  -> YAMCS archive / MDB classification

Command
  YAMCS TC(17,1)
  -> OpenSVF YamcsBridge
  -> OBCEmulatorAdapter
  -> OpenOBSW
  -> TM(1,1), TM(17,2), TM(1,7)
  -> YAMCS

Event
  eps.voltage_out_of_bounds
  -> OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001
  -> OpenOBSW TM(5,3)
  -> OpenSVF YamcsBridge
  -> YAMCS archive / MDB classification
```

Stage 6 evidence proves representative integration continuity. It does not claim a production mission runtime, flight-target deployment, hardware validation, complete FDIR implementation or operational ground deployment.

## 3. Frozen ownership decisions

The PR #30 review established the production ownership boundary used by Stage 7:

1. The OrbitFabric integration generates OpenSVF-compatible SRDB. OpenSVF owns XTCE generation.
2. Generated OpenOBSW-facing output remains contract-only. OpenOBSW owns C11 runtime behavior, packet framing, dispatch, HK scheduling and event materialization.
3. Long-term OpenSVF integration should use supported public APIs rather than PoC monkey-patching or private injection.
4. `YamcsBridge` remains the OpenSVF/YAMCS integration boundary.
5. The adapter compatibility contract should carry explicit OpenOBSW/OpenSVF/SRDB compatibility markers.
6. OpenSVF campaign JSON remains canonical verification evidence. Integration Result references evidence rather than implementing another verifier.

One additional implementation constraint from the review is critical for SRDB generation:

```text
TM parameter offsets must use the OpenOBSW-declared PUS TM secondary-header length.
The adapter must not infer or duplicate that packet-layout fact privately.
```

## 4. Stage 7.0 - Extraction baseline

Status: **in progress in this branch**

Goals:

```text
stop treating poc_slice.yaml as the future production schema
introduce a Projection Profile extraction candidate following the generic envelope
anchor every semantic source through Core {domain,id} identity
remove duplicated Core semantics from the extracted Profile
retain the legacy PoC mapping unchanged as historical evidence
establish a contract-coherent implementation sequence for the real Integration Package
```

First extracted Profile candidate:

```text
projection_profiles/poc_openobsw_opensvf.yaml
```

Contract status of this file:

```text
generic Projection Profile envelope: followed
Core source identities: explicitly anchored by {domain,id}
OpenOBSW/OpenSVF config vocabulary: extraction candidate only
integration-specific JSON Schema: not frozen until Stage 7.1
production adapter input claim: not made yet
```

The Profile intentionally removes values that belong to Core semantic authority:

```text
telemetry unit
telemetry sample timing
command arguments
event severity
event/fault trigger semantics
packet-to-telemetry membership
```

It retains target-specific projection choices such as:

```text
explicit PoC numeric allocations carried forward for review
PUS service/subtype mapping
HK SID allocation
explicit target naming override where the PoC target name differs from Core identity
verification-facing expected protocol responses
```

The carried numeric IDs and SID are not promoted to a generic OrbitFabric ABI or Core-owned identifier range by this extraction. Their long-term allocation and stability policy remains an integration-specific Stage 7.1 decision.

For example, the Core command identity is:

```text
commands / obc.ping
```

while the existing PoC uses:

```text
dhs.obc.ping
```

as an SRDB-facing target name. Stage 7 keeps `obc.ping` as the semantic source identity and records `dhs.obc.ping` only as target-specific configuration.

Likewise, Core packet `obc_hk` already records its telemetry membership. The extracted Profile therefore anchors the HK target allocation to the packet and does not repeat the packet-to-telemetry relationship.

The old file remains:

```text
orbitfabric_models/poc_slice.yaml
```

It is PoC evidence and migration input, not the production Profile contract.

No `integration_package.json` is added in Stage 7.0. Advertising an executable package before the adapter command exists would create a false package declaration.

## 5. Stage 7.1 - Integration-specific Profile schema

Next milestone.

Goal:

Freeze and validate the OpenOBSW/OpenSVF-specific vocabulary used under generic Profile `settings` and `bindings[].config` before implementing the executable package.

Planned deliverables:

```text
integration_package/schemas/profile-0.1.schema.json
Profile migration/validation fixtures
schema validation tests
```

The schema will use JSON Schema Draft 2020-12 and resolve locally/offline.

The Stage 7.0 config keys are review inputs, not automatically frozen API. Stage 7.1 must explicitly decide at least:

```text
numeric allocation vocabulary and stability policy
target naming override vocabulary
PUS service/subtype representation
HK SID/grouping representation
verification-facing expected-response representation
deterministic target naming/type defaults versus authored overrides
```

Core-owned values remain forbidden as target-profile duplicates where the adapter can consume them from the Core Integration Input Set.

## 6. Stage 7.2 - First coherent executable Integration Package

Goal:

Materialize the first package that is internally truthful and executable according to the candidate OrbitFabric package/execution contracts.

This milestone introduces together:

```text
integration_package/integration_package.json
package-local Profile schema digest declaration
executable adapter entry point
orbitfabric.adapter_cli.v0 project operation
minimum valid integration_result.json
contract-only OpenOBSW-facing generated artifact
OpenSVF-compatible SRDB generated artifact
```

Required invocation:

```text
orbitfabric-openobsw-opensvf run
    --operation project
    --input-set-manifest <path/to/integration_input_manifest.json>
    --profile <path/to/projection-profile.yaml>
    --output-dir <directory>
```

Required behavior:

```text
consume the explicit Core Integration Input Manifest
validate required Core surface roles/kinds/versions
never fall back to raw Mission Model YAML
validate the Projection Profile against the package-published schema
resolve Profile sources through Core Entity Index identity
consume semantics from Core-owned surfaces
resolve and validate every external compatibility fact that affects generated artifacts
fail explicitly when a required compatibility fact is unavailable or incompatible
produce target artifacts inside the requested output bundle
write integration_result.json last when possible
keep stdout/stderr non-semantic
```

Compatibility preflight is required before the first SRDB generation. In particular:

```text
pus_tm_secondary_header_len
    -> must come from the OpenOBSW compatibility boundary
    -> must be checked before deriving TM parameter offsets
    -> must not be replaced by a private duplicated adapter constant

supported PUS services
    -> must be checked before accepting Profile PUS mappings

obsw-srdb compatibility
    -> must be checked before claiming the generated SRDB is compatible
```

Other reviewed markers remain part of the integration compatibility model and must be checked by any operation whose behavior materially depends on them.

The package manifest declares only capabilities that the same milestone can truthfully execute and materialize in its Result.

The initial target capability set remains:

```text
profile_validation
projection
artifact_generation
traceability
```

If `traceability` is not yet materially implemented when the executable package is introduced, it must not be advertised until the corresponding Result records exist.

Existing `tools/generate_poc_artifacts.py` remains reference evidence while this behavior is extracted. It must not become the production adapter API unchanged.

## 7. Stage 7.3 - Integration Result hardening, traceability and provenance

Goal:

Expand the minimum valid Result from Stage 7.2 into the durable reference-integration result surface required by CI and Studio.

Target result scope:

```text
operation/result state
Core Input Set provenance
Profile provenance
adapter identity/version
exercised capabilities
generated C11 contract artifact
generated OpenSVF-compatible SRDB artifact
Core entity -> target mapping records
resolved target values with authority provenance
integration diagnostics
projection coverage
external compatibility provenance
```

Core lint findings remain Core-owned and are not copied into integration diagnostics.

Stage 7.3 does not introduce compatibility checks that generation already depends on. Those checks are part of Stage 7.2 preflight. Stage 7.3 makes the resulting compatibility state durable and inspectable by recording the exact values, producers and versions in Integration Result provenance.

Compatibility provenance must preserve the PR #30 review findings, including:

```text
openobsw_version
wire_protocol_version = 3
pus_tm_secondary_header_len = 11 bytes at the reviewed baseline
supported PUS services
obsw-srdb package version
OBCEmulatorAdapter API version
```

The `pus_tm_secondary_header_len` value is external compatibility input used to derive SRDB offsets. It must not be guessed from a duplicated adapter constant.

OpenSVF campaign evidence remains external-owned and is referenced only when later verification/evidence capabilities are deliberately added.

## 8. Stage 7.4 - Capability-oriented regression migration

The Stage 6 validators remain valuable evidence but Stage numbering must not become the product test API.

Representative migration:

```text
Stage 6.17
    -> capability regression: live_hk_tm_to_yamcs

Stage 6.18
    -> capability regression: live_event_tm_to_yamcs

Stage 6.19
    -> capability regression: yamcs_tc_to_openobsw_closed_loop

Stage 6.20
    -> reference integration evidence matrix
```

Runtime regression remains separate from the initial projection package capabilities.

## 9. Runtime and verification capability boundary

The initial package does not claim runtime or verification capabilities merely because Stage 6 proved representative runtime paths.

Potential later capability IDs include:

```text
runtime_discovery
runtime_orchestration
verification_execution
evidence_discovery
live_telemetry
commanding
```

Each capability requires a deliberate operation contract and Result semantics before it is advertised.

OpenSVF remains the owner of campaign execution and `YamcsBridge`. YAMCS remains the owner of its runtime link, archive and MDB interpretation semantics.

## 10. Explicit non-goals for the first Stage 7 package

The first extracted package does not:

```text
modify OrbitFabric Core
make Core OpenOBSW/OpenSVF aware
make Core generate XTCE
generate OpenOBSW runtime logic
replace OpenSVF campaign execution
replace YamcsBridge
implement YAMCS runtime semantics
claim production flight runtime
claim hardware-target validation
claim runtime_discovery, verification_execution, evidence_discovery,
live_telemetry or commanding package capabilities before those operations exist
```

## 11. Stage 7 exit criteria

Stage 7 extraction is complete when the proven vertical slice can be reproduced through the explicit reference integration contracts:

```text
OrbitFabric Core v1.2 Integration Input Set
+
version-controlled Projection Profile
+
package-published local Profile schema
+
static Integration Package manifest
+
out-of-process adapter_cli.v0 project operation
    -> contract-only OpenOBSW-facing artifact
    -> OpenSVF-compatible SRDB artifact
    -> Integration Result with traceability/provenance
```

At that point the Stage 6 PoC remains as historical evidence and regression source material, while the Stage 7 package becomes the durable reference integration implementation.
