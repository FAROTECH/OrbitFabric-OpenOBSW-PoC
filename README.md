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
5. Execute the contracted behavior in OpenOBSW.
6. Validate command, telemetry, and event visibility through OpenSVF/YAMCS.

The first slice focuses on:

* one telemetry parameter;
* one command;
* one event/fault path;
* one housekeeping packet.

For the engineering mapping details, see [Mapping Concept & Vertical Slice Definition](docs/mapping_concept.md).

For the longer-term architectural direction, see [Integration Vision](docs/integration_vision.md).

For the staged execution plan, see [Roadmap](docs/roadmap.md).

## Repository Structure & Data Flow

The repository separates the OrbitFabric source model, PoC-specific mapping/allocation data, generated artifacts, and execution evidence.

```text
orbitfabric_models/
  mission/              OrbitFabric Core-compatible Mission Model
  poc_slice.yaml         PoC mapping/allocation layer

generated_artifacts/
  flight_software/       Generated OpenOBSW-facing C contract artifacts
  ground_segment/        Generated OpenSVF/YAMCS-facing artifacts

execution/               Future execution scripts, validation runners, and campaign material

docs/                    Architecture, mapping, roadmap, and workflow documentation
```

### Source Model vs Mapping Layer

`orbitfabric_models/mission/` is the OrbitFabric Core-compatible source model.

It is the semantic Mission Model and should validate with:

```bash
orbitfabric lint orbitfabric_models/mission/
```

`orbitfabric_models/poc_slice.yaml` is not the OrbitFabric Core Mission Model.

It is a PoC mapping/allocation layer used to associate the semantic mission model with integration-specific details such as:

* C identifiers;
* numeric allocation values;
* PUS service/subservice mapping;
* SRDB canonical names;
* housekeeping set/SID details.

This distinction is intentional:

```text
OrbitFabric Core Mission Model
+ PoC mapping/allocation layer
-> generated mission_contract.h
-> generated OpenSVF-compatible SRDB YAML
```

## Current Status

* [x] Define high-level mapping concepts.
* [x] Define the minimal OrbitFabric Core-compatible Mission Model.
* [x] Validate the Mission Model with OrbitFabric Core 1.0.0.
* [ ] Align the PoC adapter mapping.
* [ ] Generate `mission_contract.h`.
* [ ] Generate OpenSVF-compatible SRDB YAML.
* [ ] Generate XTCE/YAMCS MDB via OpenSVF.
* [ ] Execute the validation campaign.

## Development Workflow

This PoC is developed through branch-based collaboration.

Use branches and pull requests.

Do not push directly to `main`.

For local setup and collaborator workflow, see [Development Workflow](docs/development_workflow.md).
