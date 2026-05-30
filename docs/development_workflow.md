# Development Workflow

This document defines the recommended development workflow for the OrbitFabric ↔ OpenOBSW/OpenSVF PoC.

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

For every change:

```bash
git checkout main
git pull --ff-only origin main
git checkout -b <branch-name>
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

For collaborators with write access to the shared PoC repository:

```text
origin = git@github.com:lipofefeyt/OrbitFabric-OpenOBSW-PoC.git
```

A personal fork can be kept as backup, but the normal workflow should be:

```text
origin/main
  -> feature branch
  -> PR into origin/main
```

Example:

```bash
git fetch --all --prune
git checkout main
git pull --ff-only origin main
git checkout -b docs/align-poc-documentation-after-core-slice
```

Push:

```bash
git push -u origin docs/align-poc-documentation-after-core-slice
```

Open PR:

```bash
gh pr create --base main --head docs/align-poc-documentation-after-core-slice
```

## Pull Request Rules

Each PR should be small and reviewable.

Prefer one concern per PR.

Recommended sequence:

1. documentation alignment;
2. adapter prototype;
3. generated artifact shape;
4. SRDB/XTCE ingestion;
5. OpenOBSW integration;
6. execution/validation evidence.

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

Before opening PRs that touch the OrbitFabric Mission Model:

```bash
orbitfabric lint orbitfabric_models/mission/
```

Before adapter PRs:

```bash
orbitfabric lint orbitfabric_models/mission/
python tools/generate_poc_artifacts.py
```

Additional commands will be added as the PoC grows.

## What Not to Do

Do not:

* push directly to `main`;
* turn the workspace into a monorepo;
* copy private Reference Mission content into the PoC;
* make OrbitFabric Core depend on OpenOBSW/OpenSVF;
* put runtime logic inside generated `mission_contract.h`;
* introduce Docker before the basic adapter and execution chain are clear.
