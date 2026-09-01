# Development Workflow

This document defines the recommended development workflow for the OrbitFabric <-> OpenOBSW/OpenSVF PoC and Reference Integration repository.

## Repository Layout

Use side-by-side repositories.

Do not create a monorepo.

Recommended local workspace:

```text
~/Dev/orbitfabric-openobsw-workspace/
  orbitfabric/
  orbitfabric-reference-mission/
  opensvf/
  openobsw/
  orbitfabric-openobsw-poc/
```

Repository roles:

```text
orbitfabric/                    Public OrbitFabric Core repository
orbitfabric-reference-mission/  Private reference mission, not copied into the PoC
opensvf/                        Public OpenSVF repository
openobsw/                       Public OpenOBSW repository
orbitfabric-openobsw-poc/       Shared PoC repository
```

## Core Rule

OrbitFabric Core remains backend-agnostic.

The PoC repository may contain adapter/profile logic for OpenOBSW/OpenSVF.

OrbitFabric Core must not become directly dependent on:

* OpenOBSW;
* OpenSVF;
* YAMCS;
* XTCE;
* PUS-specific runtime implementation details.

## Reference Mission Rule

The private OrbitFabric Reference Mission may be used as an internal design reference.

It must not be copied into the public PoC unless explicitly reviewed and intentionally sanitized.

The PoC must remain small, public, and self-contained.

## Branching Model

Use branch-based development.

Do not push directly to `main`.

For a fork/upstream setup:

```bash
git fetch --all --prune
git switch main
git pull --ff-only upstream main
git push origin main
git switch -c <branch-name>
```

Then commit and open a PR.

Recommended branch naming:

```text
docs/<short-description>
adapter/<short-description>
generated/<short-description>
execution/<short-description>
```

Examples:

```text
docs/align-poc-documentation-after-core-slice
adapter/generate-contract-and-srdb
execution/validate-s17-ping-loop
```

## Collaborator Workflow

A common local configuration is:

```text
origin
    personal or organization fork

upstream
    canonical lipofefeyt/OrbitFabric-OpenOBSW-PoC
```

Push the feature branch to `origin`, then open a pull request against canonical `main`.

Collaborators who use the canonical repository directly may use a different remote layout, but the same rule applies: branch-based changes and pull-request review, not direct pushes to canonical `main`.

## Pull Request Rules

Each PR should be small and reviewable.

Prefer one concern per PR.

For current Reference Integration work, prefer one concern per PR, for example:

1. contract/schema or compatibility changes;
2. Adapter implementation changes;
3. target composition or downstream integration changes;
4. verification/evidence changes;
5. documentation or baseline updates.

Avoid mixing:

* documentation changes;
* generated artifacts;
* adapter implementation;
* OpenOBSW runtime changes;
* OpenSVF ingestion changes.

## Generated Artifact Policy

Generated files may be committed when they are part of the PoC evidence.

When generated artifacts are committed, they must be:

* deterministic;
* reproducible;
* clearly marked as generated;
* associated with the generator command;
* reviewed as interface artifacts, not as hand-written source.

## Validation Commands

For changes that touch the legacy PoC Mission Model, keep the Core lint check:

```bash
orbitfabric lint orbitfabric_models/mission/
```

For Reference Adapter changes, run the Integration Package unit suite:

```bash
python -m unittest discover \
  -s integration_package/tests \
  -p "test_*.py" \
  -v
```

For verification-projection contract changes:

```bash
python tools/validate_stage7_10c_projection_plan_contract.py
```

Changes that affect native downstream build/runtime behavior should run the appropriate Stage 7 native acceptance validator against the pinned sibling repositories.

Documentation-only changes do not require rerunning expensive native runtime acceptance.

Keep implementation and generic contract versions distinct:

```text
Adapter implementation
    0.1.0

Projection Profile / Integration Package / Integration Result generic contracts
    0.1-candidate
```

## What Not to Do

Do not:

* push directly to `main`;
* turn the workspace into a monorepo;
* copy private Reference Mission content into the PoC;
* make OrbitFabric Core depend on OpenOBSW/OpenSVF;
* put runtime logic inside generated `mission_contract.h`;
* treat Stage-numbered PoC harnesses or Docker sidecars as the public Adapter API;
* treat generated C structs as implicit wire-format contracts;
* make the Adapter a second SRDB implementation or a second verifier.
