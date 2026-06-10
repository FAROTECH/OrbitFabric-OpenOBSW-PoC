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

For the staged execution plan, see [Roadmap](docs/roadmap.md).

## Repository Structure & Data Flow

The repository separates the OrbitFabric source model, PoC-specific mapping/allocation data, generated artifacts, execution assets, validation tools, and local evidence.

```text
orbitfabric_models/
  mission/              OrbitFabric Core-compatible Mission Model
  poc_slice.yaml         PoC mapping/allocation layer

generated_artifacts/
  flight_software/       Generated OpenOBSW-facing C contract artifacts
  ground_segment/        Generated OpenSVF/YAMCS-facing artifacts

execution/
  opensvf/               PoC-side OpenSVF spacecraft descriptors
  campaigns/             OpenSVF campaign descriptors
  procedures/            OpenSVF campaign procedures
  generated/             Local generated runtime/MDB outputs, ignored by git
  evidence/              Local runtime evidence, ignored by git

tools/                   PoC generators and validators

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

## Current Baseline

The repository has moved beyond the initial modeling-only phase.

Completed baseline:

* [x] Define high-level mapping concepts.
* [x] Define the minimal OrbitFabric Core-compatible Mission Model.
* [x] Validate the Mission Model with OrbitFabric Core 1.0.0.
* [x] Align the PoC adapter mapping/allocation layer.
* [x] Generate `mission_contract.h`.
* [x] Generate OpenSVF-compatible SRDB YAML.
* [x] Validate local XTCE/YAMCS MDB generation through the PoC/OpenSVF wrapper.
* [x] Establish OpenSVF pipe-mode readiness without introducing a custom bridge process.
* [x] Execute the first OpenSVF runtime smoke against the OrbitFabric-enabled OpenOBSW host simulator.
* [x] Validate the PUS ping command path: `TC(17,1) -> TM(1,1), TM(17,2), TM(1,7)`.

Open items:

* [ ] YAMCS runtime execution.
* [ ] SRDB package/version-handshake cleanup for a clean runtime environment.
* [ ] Runtime validation of `TM(3,25)` housekeeping telemetry.
* [ ] Runtime validation of the `TM(5,3)` event/fault path.
* [ ] Broader reproducibility hardening, such as CI, clean-clone setup, or optional Docker/devcontainer support.

## Stage 6.3 Runtime Finding

The first campaign-based OpenSVF runtime smoke requires realtime simulation mode:

```yaml
simulation:
  realtime: true
```

Without realtime mode, the OpenSVF software tick source can complete the simulation before an operator-style campaign procedure observes telemetry in wall-clock time.

See [Stage 6.3 OpenSVF Runtime Smoke](docs/stage6_3_opensvf_runtime_smoke.md).

## Development Workflow

This PoC is developed through branch-based collaboration.

Use branches and pull requests.

Do not push directly to `main`.

For local setup and collaborator workflow, see [Development Workflow](docs/development_workflow.md).
