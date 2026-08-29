# Optional obsw-srdb Composition Boundary Proposal

Status: internal engineering proposal supporting Stage 7.2 design.

This document is not an upstream change request and is not a prerequisite for the first OrbitFabric OpenOBSW/OpenSVF Adapter.

Its purpose is to define the smallest useful target-owned composition capability that could later automate application of externally generated SRDB contributions without moving SRDB semantics into OrbitFabric.

## 1. Context

The audited OpenOBSW baseline is:

```text
OpenOBSW 0.7.0
commit b3b7c3fa9c6edd2a52eef356d113c1eae1b03fec

obsw-srdb 0.1.0
```

`obsw-srdb 0.1.0` defines typed models for:

```text
Spacecraft
Parameter
Telecommand
HKSet
Event
```

and validates a complete SRDB data directory containing:

```text
spacecraft.yaml
parameters.yaml
telecommands.yaml
hk_sets.yaml
events.yaml
```

Its current `SRDBLoader.load(data_dir)` contract expects the complete database.

The current OpenOBSW CMake integration also binds code generation directly to:

```text
srdb/data
```

No supported external additive composition boundary was found in the audited baseline.

## 2. Why this is not a Stage 7.2 blocker

The first OrbitFabric operation is `project`, not target application.

It can correctly produce:

```text
mission_contract.h
+
obsw-srdb contribution records
+
integration_result.json
```

without mutating an OpenOBSW checkout or pretending that the generated records are already a complete SRDB.

Therefore:

```text
native composition API absent
    -> no Stage 7.2 project blocker
```

The first Adapter can be implemented against the contribution handoff defined by the Stage 7.2 design.

A native composition API becomes useful only when a later workflow wants to automate:

```text
apply contribution to a complete target SRDB
assemble a complete SRDB in CI
build OpenOBSW from an assembled SRDB
run downstream XTCE/runtime/verification workflows from the assembled result
```

## 3. Desired ownership

If composition is added, it should be owned by `obsw-srdb`.

The target ownership chain should remain:

```text
external producer
    -> contributes target-model records

obsw-srdb
    -> owns composition semantics
    -> owns duplicate/collision policy
    -> owns cross-reference validation
    -> returns a complete validated SRDB

obsw-srdb codegen
    -> owns C header / XTCE generation
```

OrbitFabric should consume this boundary rather than reimplement it.

## 4. Required property: generic, not OrbitFabric-specific

A useful composition API must not know about:

```text
OrbitFabric Core
Projection Profiles
Integration Results
Studio
```

It should be useful to any external SRDB producer.

The conceptual input is simply:

```text
base complete SRDB
+
one or more additive SRDB contributions
```

## 5. Recommended first composition semantics

The safest initial semantics are additive-only.

An extension may contribute:

```text
parameters
telecommands
hk_sets
events
```

The base `spacecraft` record remains authoritative in the first version.

Extensions must not silently replace or override base records.

The composition rule should be:

```text
new identity
    -> add

existing identity with a second contributed record
    -> error
```

If later use cases need explicit replacement semantics, they should be introduced as a separately versioned feature rather than hidden precedence.

## 6. Identity and collision rules

Composition should preserve the current target namespaces.

### Parameters

Require uniqueness of:

```text
Parameter.id
Parameter.name
```

### Events

Require uniqueness of:

```text
Event.id
Event.name
```

### HK sets

Require uniqueness of:

```text
HKSet.id
HKSet.name
```

### Telecommands

At minimum require uniqueness of:

```text
Telecommand (apid, service, subservice)
```

A duplicate target name with a different tuple should also be rejected or explicitly specified by target policy.

The important property is that collision semantics remain target-owned and deterministic.

## 7. Cross-reference validation

After composition, the same complete-database invariants must apply as for a native SRDB load.

For example:

```text
every HKSet.parameters name resolves to exactly one Parameter
all entity IDs remain in their model-defined ranges
all PTC/PFC/type constraints remain valid
telecommand argument types remain supported
Event safe_trigger constraints remain valid
```

Composition must not produce an intermediate object that bypasses existing model validation.

Preferred invariant:

```text
compose(base, contributions)
    -> complete SRDB object
    -> same validation guarantees as SRDBLoader.load(complete_data_dir)
```

## 8. Determinism

Composition should be deterministic.

Given identical:

```text
base content
ordered contribution inputs
composition implementation version
```

it should produce the same logical SRDB.

No filesystem scan order, environment-dependent ordering, current working directory, or network lookup should affect the result.

## 9. Provenance

A composition API does not need to understand OrbitFabric provenance, but it would be useful if callers can retain or query:

```text
base source identity/digest
contribution source identity/digest
composition implementation version
```

This can be caller-owned metadata if the core SRDB model should remain minimal.

The target model itself does not need OrbitFabric-specific provenance fields.

## 10. Possible Python API shapes

The exact API is OpenOBSW/obsw-srdb-owned. The following are illustrative only.

### Option A - dedicated composer

```python
base = SRDBLoader.load(base_dir)
contribution = SRDBContributionLoader.load(contribution_dir)
complete = SRDBComposer.compose(base, [contribution])
```

### Option B - loader composition

```python
complete = SRDBLoader.load_composed(
    base_dir=base_dir,
    extension_dirs=[extension_dir],
)
```

### Option C - in-memory target records

```python
complete = SRDBComposer.compose_records(
    base=base,
    parameters=[...],
    telecommands=[...],
    hk_sets=[...],
    events=[...],
)
```

Option C is attractive for tool integrations because it avoids inventing an extension-file format solely for transport.

However the target project should choose the API based on its broader SRDB roadmap.

## 11. Possible CLI shape

If a CLI is useful, a generic shape could be:

```text
obsw-srdb-compose
    --base-dir <complete-srdb-dir>
    --extension-dir <contribution-dir>
    --output-dir <assembled-srdb-dir>
```

or a validation-only mode:

```text
obsw-srdb-compose
    --base-dir <complete-srdb-dir>
    --extension-dir <contribution-dir>
    --check
```

The CLI should use the same composition implementation as the Python API, not duplicate rules.

## 12. Materialized output

A composition boundary can return an in-memory complete `SRDB` object without necessarily writing YAML.

If materialization is supported, the output should be a normal complete SRDB data directory that existing tools can consume.

The output must not depend on comments or formatting from the original YAML files for semantic correctness.

## 13. OpenOBSW build integration as a separate concern

Current OpenOBSW CMake sets:

```text
SRDB_DATA_DIR = ${CMAKE_CURRENT_SOURCE_DIR}/data
```

A future automated assembled-SRDB workflow may also benefit from making the data directory a cache/configuration input, conceptually:

```text
SRDB_DATA_DIR=<external assembled directory>
```

This is separate from composition semantics.

The two concerns should not be conflated:

```text
composition
    -> how a complete valid SRDB is formed

build path selection
    -> which complete SRDB directory OpenOBSW codegen consumes
```

The first Stage 7.2 `project` operation requires neither change.

## 14. Failure model

A composition failure should be explicit and deterministic.

Useful categories include:

```text
invalid base SRDB
invalid contribution record
parameter ID collision
parameter name collision
event ID collision
event name collision
HK SID collision
HK name collision
unknown HK parameter reference
telecommand tuple collision
unsupported target record shape
```

The API should not resolve collisions through hidden precedence.

## 15. Non-goals

A first composition boundary should not:

```text
generate OpenOBSW runtime behavior
interpret OrbitFabric semantics
perform PUS runtime discovery
generate verification campaigns
call YAMCS
change XTCE ownership
perform network access
silently patch an arbitrary repository checkout
support record replacement without an explicit versioned policy
```

## 16. Why not implement composition inside the OrbitFabric Adapter

The Adapter can and should perform projection-specific collision preflight against a pinned baseline.

It should not become the canonical implementation of general SRDB composition because that would create two target semantics:

```text
obsw-srdb native complete-database validation
+
OrbitFabric-private merge semantics
```

Those implementations could drift independently.

The contribution-handoff model avoids this problem today.

If target-owned composition becomes available later, the Adapter can call it for a future application/assembly operation without changing Core semantics or the Profile model.

## 17. Recommendation

For the current reference integration:

```text
Stage 7.2 project
    -> proceed without OpenOBSW changes
    -> generate explicit obsw-srdb contribution artifacts
    -> validate them against the pinned target baseline
    -> do not apply them
```

For future automation:

```text
consider a generic obsw-srdb additive composition boundary upstream
```

This is an enhancement request, not a prerequisite.

## 18. Question to take upstream later

After the Stage 7.0/7.1 architecture is reviewed, the useful question for Goncalo is narrowly:

```text
Would a generic additive composition surface in obsw-srdb fit the project roadmap,
so external tools can contribute typed Parameter/Telecommand/HKSet/Event records
without owning target merge semantics?
```

No specific API shape needs to be imposed unless OpenOBSW maintainers want to discuss implementation options.
