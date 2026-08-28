# OrbitFabric ↔ OpenOBSW : MBSE Vertical Slice PoC

## The Vision

This repository is a Proof of Concept (PoC) demonstrating a minimal, end-to-end Model-Based Systems Engineering (MBSE) continuity chain for spacecraft software validation.

It bridges:

* **[OrbitFabric Core](https://github.com/FAROTECH/orbitfabric):** the model-first Mission Data Contract framework and semantic source of truth.
* **[OpenOBSW](https://github.com/lipofefeyt/openobsw) & [OpenSVF](https://github.com/lipofefeyt/opensvf):** the flight software execution stack and simulation/ground validation environment.

The goal is not to turn OrbitFabric into flight software, nor to replace OpenOBSW, OpenSVF, XTCE, YAMCS, or PUS tooling.

The goal is to prove that a validated OrbitFabric Mission Model can be projected into concrete flight-side and ground-side artifacts, then exercised through an execution and validation loop.

## The Goal: The Thin Vertical Slice

The first PoC slice intentionally stays small:

1. Define a minimal OrbitFabric Core Mission Model.
2. Validate it with `orbitfabric lint`.
3. Use a PoC adapter/mapping layer to generate:
   * a flight-side `mission_contract.h`;
   * an OpenSVF-compatible SRDB YAML.
4. Let OpenSVF generate the XTCE/YAMCS mission database.
5. Execute the contracted behavior in OpenOBSW/OpenSVF runtime smoke tests.
6. Validate command, telemetry, and event visibility through OpenSVF/YAMCS.

The first slice focuses on:

* one telemetry parameter;
* one command;
* one event/fault path;
* one housekeeping packet.

For the engineering mapping details, see [Mapping Concept & Vertical Slice Definition](docs/mapping_concept.md).

For the longer-term architectural direction, see [Integration Vision](docs/integration_vision.md).

For the detailed PoC stage history, see [Roadmap](docs/roadmap.md).

For the current transition from PoC evidence to a durable reference integration, see [Stage 7 Reference Integration Package Extraction](docs/stage7_reference_integration_extraction.md).

## Repository Structure & Data Flow

The repository separates the OrbitFabric source model, PoC-specific mapping/allocation data, extracted Projection Profile work, generated artifacts, execution assets, validation tools, and local evidence.

```text
orbitfabric_models/
  mission/              OrbitFabric Core-compatible Mission Model
  poc_slice.yaml         Legacy PoC mapping/allocation layer

projection_profiles/     Stage 7 Projection Profile extraction candidates

generated_artifacts/
  flight_software/       Generated OpenOBSW-facing C contract artifacts
  ground_segment/        Generated OpenSVF-facing SRDB artifacts

execution/
  opensvf/               PoC-side OpenSVF spacecraft descriptors
  campaigns/             OpenSVF campaign descriptors
  procedures/            OpenSVF campaign procedures
  yamcs/                 PoC YAMCS runtime/evidence harnesses
  generated/             Local generated runtime/MDB outputs, ignored by git
  evidence/              Local runtime evidence, ignored by git

tools/                   PoC generators and validators

docs/                    Architecture, mapping, stage evidence, and workflow documentation
```

### Source Model vs Legacy Mapping Layer

`orbitfabric_models/mission/` is the OrbitFabric Core-compatible source model.

It is the semantic Mission Model and should validate with:

```bash
orbitfabric lint orbitfabric_models/mission/
```

`orbitfabric_models/poc_slice.yaml` is not the OrbitFabric Core Mission Model.

It is the original PoC mapping/allocation layer used to associate the semantic mission model with integration-specific details such as:

* C identifiers;
* numeric allocation values;
* PUS service/subservice mapping;
* SRDB target names;
* housekeeping set/SID details.

That file remains useful PoC evidence and migration input, but Stage 7 no longer treats it as the future production integration schema.

The production-oriented boundary now follows the OrbitFabric v1.2 integration architecture:

```text
OrbitFabric Mission Model
        ↓
OrbitFabric Core
        ↓
Core Integration Input Set
        ↓
Projection Profile
        ↓
OpenOBSW/OpenSVF Integration Package / Adapter
        ↓
Integration Result + target artifacts
```

Core remains the semantic authority. Target-specific projection choices belong to the Projection Profile and Integration Package.

## Current Baseline

The selected PoC vertical slice is now closed at the representative integration-evidence level.

Completed baseline:

* [x] Define high-level mapping concepts.
* [x] Define and lint the minimal OrbitFabric Core-compatible Mission Model.
* [x] Generate the contract-only OpenOBSW-facing `mission_contract.h`.
* [x] Generate OpenSVF-compatible SRDB YAML.
* [x] Validate local XTCE/YAMCS MDB generation through OpenSVF tooling.
* [x] Establish OpenSVF pipe-mode execution through `OBCEmulatorAdapter`.
* [x] Validate the representative ping command path.
* [x] Validate live OpenOBSW `TM(3,25)` housekeeping delivery through real OpenSVF `YamcsBridge` into YAMCS archive/MDB classification.
* [x] Validate live OpenOBSW `TM(5,3)` event delivery through real OpenSVF `YamcsBridge` into YAMCS archive/MDB classification.
* [x] Validate the opposite YAMCS-originated `TC(17,1)` direction through OpenSVF into live OpenOBSW and the response TM path back to YAMCS.
* [x] Consolidate the selected telemetry, command, and event paths in the Stage 6.20 final integration evidence matrix.
* [x] Review the durable ownership boundary and PoC asset disposition with the OpenOBSW/OpenSVF maintainer in PR #30.

Representative Stage 6 closure evidence:

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
  -> OpenOBSW TM(5,3)
  -> OpenSVF YamcsBridge
  -> YAMCS archive / MDB classification
```

This evidence is deliberately narrow. It does not claim production mission integration, hardware-target execution, production FDIR behavior, production commanding security/authorization, or operational deployment hardening.

## Stage 7: Reference Integration Extraction

The current engineering phase is no longer to broaden the PoC by default.

Stage 7 extracts the durable **OrbitFabric OpenOBSW/OpenSVF Reference Integration** from the proven PoC using the contracts published with OrbitFabric Core v1.2.0.

The intended durable chain is:

```text
Core Integration Input Set
+
version-controlled Projection Profile
        ↓
OpenOBSW/OpenSVF Integration Package
        ↓
out-of-process Adapter CLI
        ↓
contract-only OpenOBSW-facing artifact
OpenSVF-compatible SRDB artifact
Integration Result with traceability/provenance
```

The first extraction candidate is:

```text
projection_profiles/poc_openobsw_opensvf.yaml
```

It uses Core `{domain,id}` identity for semantic sources and keeps OpenOBSW/OpenSVF-specific PoC numeric allocations, PUS mapping, HK allocation, and target naming choices outside Core semantics. The long-term allocation/stability policy for those numeric values remains an integration-specific Stage 7 decision.

The legacy `poc_slice.yaml` remains unchanged as PoC evidence while this extraction proceeds.

See [Stage 7 Reference Integration Package Extraction](docs/stage7_reference_integration_extraction.md) for the implementation sequence and non-goals.

## Key Ownership Boundaries

The reviewed production direction is:

* OrbitFabric Core owns Mission Model semantics and the coherent Core Integration Input Set.
* The Projection Profile records authored target-specific projection choices.
* The OpenOBSW/OpenSVF Integration Package owns target-specific schema, validation, projection, generation, traceability, and compatibility checks.
* OpenOBSW owns C11 flight/runtime behavior, including packet framing, command dispatch, HK scheduling, and event materialization.
* OpenSVF owns SRDB consumption, XTCE generation, simulation/campaign behavior, and `YamcsBridge`.
* YAMCS owns MDB/runtime interpretation, TM/TC links, archive behavior, and command release semantics.
* OrbitFabric Studio may later visualize and orchestrate explicit integration contracts, but it is not a semantic owner or a second adapter.

## Development Workflow

This PoC and reference-integration extraction are developed through branch-based collaboration.

Use branches and pull requests.

Do not push directly to `main`.

For local setup and collaborator workflow, see [Development Workflow](docs/development_workflow.md).
