# Stage 7 v0 Package-Boundary Convergence Probe

Status: **Architecture Lab experiment — non-normative**

This branch is intentionally based on the exact Stage 7.10 reference head:

```text
56b11ebcf79c3360a3b27748bf502c434478b66e
```

It does **not** add operation-specific inputs or propose a new adapter protocol.

## Question

Can the current Stage 7.x adapter implementation be exposed through the canonical, Studio-consumable `orbitfabric.adapter_cli.v0` package boundary without changing current target/Profile/project or verification semantics?

## Scope

The probe may change only generic packaging/boundary material needed to demonstrate:

```text
installable adapter package
canonical v0 Integration Package manifest
portable console entry point
existing project operation through exact adapter_cli.v0 argv
existing v0 Integration Result
Studio v0 execution acceptance
```

## Explicitly unchanged

The probe must not redesign:

```text
Stage 7 Profile semantics
project resolution semantics
verification projector
Verification Projection Plan
OpenSVF materializer
native Stage 7.10 campaign semantics
OrbitFabric Core
OpenOBSW
OpenSVF
```

## Authority split

Current Stage 7.x code remains authoritative for target/profile/projection/runtime behavior.

Historical B.4 reference-adapter work is used only as evidence for the canonical generic package boundary and installable console-entry-point pattern.

This probe is therefore a **forward-port of the generic boundary**, not a backward-port of old target semantics.

## Acceptance

The experiment is accepted only when all of the following pass from an installed package:

```text
canonical manifest inspection
pinned Core v1.2.0 IISS export
installed console entry point discovery
project through exact v0 argv
valid v0 Integration Result
existing Stage 7 project tests
Studio Rust v0 external-adapter acceptance
```

The Studio consumer also establishes one package-boundary requirement that was not explicit in the older Stage 7 line: package-owned Projection Profile schemas must compile and validate under Studio's strict AJV configuration. The convergence correction makes the existing schema strict-compatible without changing the accepted Profile semantics.

Failure of any item is evidence to be classified before operation-input vNext work begins.
