# Systematic PoC Asset Inventory

Status: Architecture extraction draft for review  
Inventory baseline: upstream `lipofefeyt/OrbitFabric-OpenOBSW-PoC` `main` at `5400fc0b81b378e028da3a1a681c8fae82e53874` (Stage 6.19 merged)

Related document:

- `docs/integration_responsibility_matrix.md`

Related architecture issue:

- OrbitFabric Core #227: https://github.com/FAROTECH/orbitfabric/issues/227

---

## 1. Purpose

This inventory classifies the current PoC by **engineering asset family and production fate**.

It is not merely a file listing. The repository tree already provides that.

The purpose is to answer:

```text
What does each current PoC asset prove?
Who should own the corresponding responsibility in production?
Should the asset be reused, rewritten, retained only as a test/evidence fixture, or retired?
```

Production-fate classes used below:

```text
REFERENCE   keep as architectural/history/reference material
EXTRACT     preserve the concept/behavior in the production integration
REWRITE     preserve intent but redesign implementation around the production contract
TEST-ONLY   retain as regression/evidence material, not product API
RETIRE      legacy/empty/temporary scaffolding that should not drive architecture
```

---

# 2. Repository-level inventory

## `README.md`

**Role:** public PoC overview, source-model vs mapping-layer distinction, current baseline and workflow.

**Evidence provided:** establishes that the PoC is a continuity chain, not a flight framework; records the split between `orbitfabric_models/mission/` and `poc_slice.yaml`.

**Production fate:** `REFERENCE`.

Long-term production documentation should live with the Core integration contract and the future integration package, but the PoC README should remain as the historical entry point.

---

# 3. Mission and projection inputs

## `orbitfabric_models/mission/`

**Role:** Core-compatible Mission Model used as the semantic source of truth for the PoC.

Current mission files include the normal Core mission domains used by the generator, including:

```text
spacecraft.yaml
subsystems.yaml
modes.yaml
telemetry.yaml
commands.yaml
events.yaml
faults.yaml
packets.yaml
policies.yaml
```

**Current PoC implementation behavior:** `tools/generate_poc_artifacts.py` reads these YAML files directly and merges them into a local dictionary.

**Production ownership:** `CORE`.

**Production fate:**

```text
REFERENCE as a test/reference mission
REWRITE the adapter input path
```

The production adapter must consume Core-owned structured surfaces rather than reconstructing Mission Model semantics from YAML.

---

## `orbitfabric_models/poc_slice.yaml`

**Role:** current PoC mapping/allocation layer.

Current concerns mixed in this single file include:

```text
profile identity/version
C prefix and identifiers
numeric target allocations
SRDB names
C types
PUS service/subservice mapping
HK set/SID mapping
sample/collection timing
command expected responses
event severity
trigger parameter/condition/threshold placeholder
```

**Production ownership:** primarily `PROFILE`, with some fields that should instead be Core-derived, adapter-derived or test-only.

**Production fate:** `REWRITE` into the real Projection Profile contract.

**Key extraction requirement:** perform a field-by-field classification before freezing the schema. The responsibility matrix contains the initial classification.

---

# 4. Artifact generation

## `tools/generate_poc_artifacts.py`

**Role:** monolithic PoC adapter prototype.

Consumes:

```text
orbitfabric_models/mission/
orbitfabric_models/poc_slice.yaml
```

Produces:

```text
generated_artifacts/flight_software/mission_contract.h
generated_artifacts/ground_segment/poc_srdb.yaml
```

Current responsibilities inside the script include:

```text
raw YAML loading
narrow model/mapping consistency checks
leaf-ID lookup
OpenSVF domain mapping
APID mapping
Mission type → OpenSVF type mapping
valid-range mapping
C header rendering
SRDB rendering
file output
```

The implementation contains deliberate first-slice assumptions, including support centered on `uint16` telemetry and a small fixed domain/APID map.

**Production ownership:** `ADAPTER` prototype.

**Production fate:** `REWRITE` / decompose.

Candidate production components:

```text
Core surface reader / compatibility gate
Projection Profile loader
Projection Profile validator
semantic-to-target mapping engine
flight artifact generator
ground artifact generator
traceability builder
integration diagnostic collector
provenance / Integration Result writer
```

The script is valuable as executable evidence but should not become the production adapter API unchanged.

---

## `generated_artifacts/flight_software/mission_contract.h`

**Role:** generated contract-only C11 artifact consumed at the OpenOBSW boundary.

**Proven property:** no runtime logic, PUS framing, transport, scheduling or dynamic allocation is generated into the header.

**Production ownership:** adapter-generated extension artifact; consumer is `OPENOBSW`.

**Production fate:** `EXTRACT` the boundary and generation intent.

The exact production header format may evolve, but the architectural contract should remain:

> generated artifact describes the mission/integration contract; OpenOBSW owns execution.

---

## `generated_artifacts/ground_segment/poc_srdb.yaml`

**Role:** generated OpenSVF-compatible SRDB input.

**Production ownership:** adapter-generated extension artifact; consumer is `OPENSVF`.

**Production fate:** `EXTRACT` where OpenSVF compatibility continues to require SRDB.

The production architecture should not make OrbitFabric Core emit XTCE merely because the PoC ultimately reaches YAMCS.

---

# 5. OpenSVF / XTCE handoff tools

## `tools/validate_opensvf_srdb_xtce.py`

**Role:** validates that the generated SRDB is consumable through the current OpenSVF path.

**Production fate:** `TEST-ONLY` plus extraction of compatibility requirements.

---

## `tools/generate_poc_xtce_mdb.py`

**Role:** PoC-side orchestration wrapper that uses OpenSVF tooling to produce the local XTCE/YAMCS MDB.

Typical local output:

```text
execution/generated/poc_xtce_mdb.xml
```

which is intentionally ignored/local.

**Production ownership:** thin orchestration may belong to `ADAPTER`; XTCE generation semantics belong to `OPENSVF`.

**Production fate:** `REWRITE` as a narrow supported integration boundary if still needed.

The production integration should call supported OpenSVF interfaces rather than reimplementing XTCE semantics.

---

# 6. OpenOBSW contract and runtime probes

## `tools/validate_openobsw_contract_adapter.py`

**Role:** validates the optional OpenOBSW OrbitFabric contract consumption boundary while preserving the default OpenOBSW build.

**Evidence provided:** the generated contract can be consumed without moving runtime behavior into the generated artifact.

**Production fate:** `TEST-ONLY`; reuse as a source for adapter compatibility/regression tests.

---

## `tools/validate_openobsw_ping_smoke.py`

**Role:** validates the first OpenOBSW host-sim command-side execution path.

Representative path:

```text
TC(17,1)
-> TM(1,1)
-> TM(17,2)
-> TM(1,7)
```

**Production fate:** `TEST-ONLY`; retain the semantic claim as a production integration acceptance test.

---

## PoC/OpenOBSW event materialization work

The PoC and related OpenOBSW discussion establish the runtime boundary for:

```text
OF_EVENT_VOLTAGE_OUT_OF_BOUNDS
-> OpenOBSW PUS Service 5 materialization
-> TM(5,3)
```

**Production ownership:** OpenOBSW owns the runtime materialization; Profile/Adapter own the semantic-to-physical mapping.

**Production fate:** `EXTRACT` the boundary and retain runtime regression evidence.

---

# 7. Unified/local validation and evidence

## `tools/validate_poc_pipeline.py`

**Role:** unifies multiple PoC generation/validation stages.

**Production fate:** `TEST-ONLY` / `REWRITE` into capability-oriented integration regression tests.

The production integration should not expose a Stage-oriented pipeline as its public API.

---

## `tools/generate_stage5_evidence_bundle.py`

**Role:** creates local machine-readable evidence with provenance/hashes for PoC assets.

**Important architectural value:** precursor of the future Integration Result `evidence` and `provenance` sections.

**Production fate:**

```text
EXTRACT the provenance/evidence concepts
TEST-ONLY for the current Stage 5 implementation
```

---

## `execution/evidence/`

**Role:** local generated runtime/campaign evidence; ignored by Git.

**Production ownership:** native evidence semantics remain with the systems that produce them; an integration result may normalize references and provenance.

**Production fate:** `EXTRACT` the evidence-reference model, not the local directory convention.

---

# 8. OpenSVF execution assets

## `execution/opensvf/`

Current tracked assets include:

```text
poc_runtime_inputs.yaml
poc_spacecraft.yaml
poc_spacecraft_runtime_smoke.yaml
```

**Role:** PoC instances of OpenSVF runtime descriptors/configuration.

**Production ownership:** descriptor semantics are `OPENSVF`; concrete generated/managed instances may be adapter-owned artifacts.

**Production fate:** `REWRITE` around supported OpenSVF interfaces and future profile/adapter outputs.

A generated OpenSVF descriptor may be an adapter artifact without becoming an OrbitFabric Core concept.

---

## `execution/campaigns/`

Tracked campaign assets currently include discovery, closed-loop ping, runtime discovery, HK smoke and ping planning/smoke descriptors.

Examples:

```text
poc_opensvf_pipe_mode_discovery.yaml
poc_ping_closed_loop.yaml
poc_runtime_discovery.yaml
poc_runtime_hk_smoke.yaml
poc_runtime_ping_plan.yaml
poc_runtime_ping_smoke.yaml
```

**Role:** staged verification/runtime probes using OpenSVF campaign semantics.

**Production ownership:** campaign semantics are `OPENSVF`; integration may generate, assist, discover or reference campaign instances.

**Production fate:** `TEST-ONLY` as PoC instances; `EXTRACT` requirements for a future verification capability.

---

## `execution/procedures/`

**Role:** PoC OpenSVF procedure assets supporting campaign execution.

**Production ownership:** `OPENSVF` semantics.

**Production fate:** `TEST-ONLY` / reference inputs to a future verification-provider design.

The production integration must not become a second procedure or verification engine.

---

# 9. YAMCS runtime candidate and bridge/live-runtime assets

## `execution/yamcs/`

This directory contains the progressive Stage 6.9–6.19 YAMCS runtime candidate and sidecars.

Tracked asset families include:

```text
Dockerfile.candidate
Dockerfile.stage6_17.live-openobsw-hk
Dockerfile.stage6_18.live-openobsw-event
Dockerfile.stage6_19.yamcs-tc-direction

docker-compose.candidate.yml
docker-compose.stage6_14.bridge-producer.yml
docker-compose.stage6_15.archive-classification.yml
docker-compose.stage6_16.real-opensvf-yamcsbridge.yml
docker-compose.stage6_17.live-openobsw-hk.yml
... Stage 6.18 / 6.19 runtime overrides and drivers
```

The staged runtime work proves increasingly strong facts rather than introducing a desired product deployment layout.

### Durable knowledge proven by this family

```text
OpenSVF/YAMCS TM link topology
OpenSVF/YAMCS TC link topology
real YamcsBridge connectivity
YAMCS MDB import
YAMCS archive visibility
MDB packet classification
live OpenOBSW TM(3,25) → YAMCS
live OpenOBSW TM(5,3) → YAMCS
YAMCS-originated TC(17,1) → OpenSVF → OpenOBSW → response TM → YAMCS
```

**Production ownership:**

```text
YAMCS runtime semantics → YAMCS
YamcsBridge semantics → OPENSVF
OpenOBSW live execution → OPENOBSW
PoC Docker/sidecar scaffolding → POC-ONLY
```

**Production fate:**

```text
EXTRACT topology/capability/acceptance-test knowledge
TEST-ONLY for most stage-specific drivers/sidecars
REWRITE any orchestration selected for the future adapter
```

Do not productize Stage 6.14–6.19 file structure merely because it proved the path.

---

# 10. Stage 6 validator family

The `tools/validate_stage6_*` family progressively validates:

```text
OpenSVF runtime discovery and pipe mode
HK telemetry visibility
SRDB package/runtime environment
YAMCS runtime/MDB readiness
YAMCS Docker candidate
fault/event readiness
S5 MDB projection
packet visibility
ground-link topology
bridge-compatible TM production
archive/MDB classification
real OpenSVF YamcsBridge
live OpenOBSW HK telemetry
live OpenOBSW event telemetry
YAMCS-originated telecommand direction closure
```

**Production ownership:** `POC-ONLY` / integration regression evidence.

**Production fate:** `TEST-ONLY`, with deliberate migration into capability-oriented tests.

Recommended refactoring when the production integration package exists:

```text
Stage 6.17 test
    ↓
capability test: live_hk_tm_to_yamcs

Stage 6.18 test
    ↓
capability test: live_event_tm_to_yamcs

Stage 6.19 test
    ↓
capability test: yamcs_tc_to_openobsw_closed_loop
```

This preserves the evidence while removing stage numbering from the product/test architecture.

---

# 11. Architecture and evidence documentation

## `docs/mapping_concept.md`

**Role:** records the thin vertical slice mapping and original boundary decisions.

**Production fate:** `REFERENCE`; migrate durable decisions into the future Profile/Adapter contract documentation.

---

## `docs/integration_vision.md`

**Role:** records the long-term continuity chain, adapter ownership direction and Projection Profile concept.

**Production fate:** `REFERENCE`; normative decisions move to Core #227 and future ADR/reference documentation.

---

## `docs/openobsw_contract_adapter_integration.md`

**Role:** records the OpenOBSW generated-contract consumption boundary.

**Production fate:** `REFERENCE` plus extraction into adapter/OpenOBSW compatibility tests.

---

## `docs/opensvf_srdb_alignment.md`

**Role:** records OpenSVF SRDB alignment decisions.

**Production fate:** `REFERENCE` plus extraction into the future adapter compatibility contract.

---

## `docs/opensvf_wrapper_and_campaign_prep.md`

**Role:** records PoC-side wrapper/campaign preparation without changing OpenSVF proper.

**Production fate:** `REFERENCE`; use to distinguish reusable OpenSVF interfaces from temporary wrapper code.

---

## `docs/poc_pipeline_validation.md`

**Role:** records the local pipeline validation boundary.

**Production fate:** `TEST-ONLY` / historical reference.

---

## `docs/stage5_*`

**Role:** campaign-plan and evidence-bundle evolution.

**Production fate:** `REFERENCE` / `TEST-ONLY`; provenance/evidence concepts are candidates for extraction.

---

## `docs/stage6_*`

**Role:** detailed engineering evidence trail for each progressive runtime probe, including explicit non-claims.

**Production fate:** `REFERENCE` / `TEST-ONLY`.

These documents should be preserved. Their explicit non-claims are important evidence against over-generalizing the PoC.

The production architecture should consume the facts they proved, not their stage organization.

---

## `docs/roadmap.md`

**Role:** staged PoC execution history and status.

**Production fate:** `REFERENCE`.

Once architecture extraction begins, production work should be tracked separately rather than extending the PoC roadmap indefinitely.

---

## `docs/development_workflow.md`

**Role:** shared PoC collaboration workflow.

**Production fate:** `REFERENCE`; the future integration package will need its own contributor/release workflow.

---

# 12. Empty / legacy placeholders

## `execution/docker_compose.yml`

Current file size is zero.

**Production fate:** `RETIRE` or leave only as historical placeholder; it must not influence architecture.

---

## `execution/runner.sh`

Current file size is zero.

**Production fate:** `RETIRE` or leave only as historical placeholder.

Only exercised assets and documented boundaries should drive production design.

---

# 13. Extraction summary by production fate

## EXTRACT

Durable concepts to preserve:

```text
Mission Model as semantic authority
separate Projection Profile state
contract-only flight artifact boundary
OpenSVF-compatible ground projection
explicit semantic-to-target traceability
profile-specific diagnostics
integration coverage
artifact/evidence provenance
fingerprint-based staleness
capability declarations
OpenOBSW runtime ownership
OpenSVF verification/bridge ownership
YAMCS runtime ownership
live bidirectional path acceptance criteria
```

## REWRITE

PoC implementations whose intent survives but whose structure should change:

```text
poc_slice.yaml → Projection Profile schema
monolithic generate_poc_artifacts.py → production adapter components
raw YAML input → Core structured-surface input
PoC XTCE wrapper → supported OpenSVF integration boundary
stage-specific runtime orchestration → capability-oriented adapter/runtime layer where needed
```

## TEST-ONLY

Keep as regression/evidence corpus:

```text
OpenOBSW adapter build/smoke validators
Stage 5 evidence implementation
Stage 6 readiness/runtime validators
representative packet probes
Docker sidecars/drivers
campaign/procedure instances
```

## REFERENCE

Preserve engineering history/rationale:

```text
mapping_concept.md
integration_vision.md
roadmap.md
stage documentation
OpenOBSW/OpenSVF boundary notes
README/development workflow
```

## RETIRE

Do not allow unused placeholders to influence the production design:

```text
empty execution/docker_compose.yml
empty execution/runner.sh
other future-discovered unused scaffolding
```

---

# 14. Review questions for Gonçalo

The inventory suggests a small number of ownership questions that are best reviewed from the OpenOBSW/OpenSVF side before Core #227 freezes the integration contract:

1. Is **SRDB → OpenSVF-owned XTCE generation** still the preferred stable handoff?
2. Is the current **contract-only generated C header** the right long-term OpenOBSW consumption boundary?
3. Which OpenSVF spacecraft/campaign interfaces should be treated as supported long-term integration points?
4. Should the integration continue to reuse the existing real **`YamcsBridge`** as the ground bridge boundary?
5. Which OpenSVF/OpenOBSW version or SRDB-package compatibility markers should a future adapter expose?
6. Which evidence/campaign outputs are stable enough to be referenced directly instead of normalized beyond provenance metadata?

The aim of review is not to request new OpenOBSW/OpenSVF functionality. It is to avoid assigning OrbitFabric ownership to responsibilities that already have a proper home in those projects.

---

# 15. Exit criterion for PoC architecture extraction

This inventory has served its purpose when the future production integration can be designed without relying on the PoC's stage numbering or internal script layout.

The production design should be expressible as:

```text
Core input contract
+ Projection Profile
+ Integration Adapter contract
+ Integration Result contract
+ OpenOBSW/OpenSVF/YAMCS compatibility boundaries
+ capability-oriented regression tests
```

At that point the PoC remains a valuable reference/evidence repository, while production integration work can move to its deliberately chosen package/repository boundary.
