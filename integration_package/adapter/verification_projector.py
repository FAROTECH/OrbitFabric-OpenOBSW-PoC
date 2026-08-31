from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .baseline import load_target_baseline
from .core_input import CoreInputSet, load_core_input_set
from .io import sha256_file
from .model import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    INTEGRATION_ID,
    AdapterFailure,
)
from .profile import ProjectionProfile, load_projection_profile
from .projection import resolve_core_bindings, resolve_projection
from .verification_plan import validate_verification_projection_provenance


PLAN_VERSION = "0.1-candidate"

KNOWN_EXPECT_KEYS = {
    "command_status",
    "payload_lifecycle",
    "data_flow",
    "scenario_status",
}

NOT_PROJECTED_REASONS = {
    "initial_mode": (
        "Stage 7.10 v0 does not project Core scenario initial mode into "
        "target runtime initialization."
    ),
    "initial_telemetry": (
        "Stage 7.10 v0 does not project Core scenario initial telemetry into "
        "target runtime initialization."
    ),
    "telemetry_injection": (
        "Stage 7.10 v0 has no explicit Core telemetry injection to target "
        "injection mapping."
    ),
    "expect_mode": (
        "Stage 7.10 v0 has no explicit Core mode to target observation mapping."
    ),
    "expect_event": (
        "Stage 7.10 v0 does not identify Core events from target PUS subtype "
        "alone."
    ),
    "expect_command": (
        "Stage 7.10 v0 does not map Core host-side command dispatch history "
        "to target runtime evidence."
    ),
    "expect_command_status": (
        "Core host-side command_status semantics are not equivalent to PUS "
        "acceptance telemetry."
    ),
    "expect_telemetry": (
        "Stage 7.10 v0 has no explicit Core telemetry to target observation "
        "mapping."
    ),
    "expect_payload_lifecycle": (
        "Stage 7.10 v0 has no target payload lifecycle observation contract."
    ),
    "expect_data_flow": (
        "OrbitFabric data-flow expectation semantics remain host-side Mission "
        "Data Contract evidence."
    ),
    "expect_scenario_status": (
        "OrbitFabric scenario_status is an aggregate Core host-side result, "
        "not target runtime evidence."
    ),
}


@dataclass
class _PlanBuilder:
    atoms: list[dict[str, Any]] = field(default_factory=list)
    operations: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def add_atom(
        self,
        *,
        kind: str,
        role: str,
        step_index: int | None,
        scenario_t: int | float | None,
        disposition: str,
        source: dict[str, str] | None,
        binding_id: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        atom = {
            "id": f"atom-{len(self.atoms) + 1:04d}",
            "kind": kind,
            "role": role,
            "step_index": step_index,
            "scenario_t": scenario_t,
            "disposition": disposition,
            "source": source,
            "binding_id": binding_id,
            "operation_ids": [],
            "reason": reason,
        }
        self.atoms.append(atom)
        return atom

    def add_operation(
        self,
        atom: dict[str, Any],
        *,
        operation: str,
        binding_id: str,
        origin: str,
        resolved: dict[str, Any],
    ) -> dict[str, Any]:
        record = {
            "id": f"op-{len(self.operations) + 1:04d}",
            "order": len(self.operations),
            "operation": operation,
            "source_atom_id": atom["id"],
            "binding_id": binding_id,
            "origin": origin,
            "resolved": resolved,
        }
        self.operations.append(record)
        atom["operation_ids"].append(record["id"])
        return record

    def add_blocking_diagnostic(self, code: str, message: str) -> None:
        self.diagnostics.append(
            {
                "id": f"diag-{len(self.diagnostics) + 1:03d}",
                "owner": "integration",
                "producer": INTEGRATION_ID,
                "phase": "verification_projection",
                "severity": "ERROR",
                "code": code,
                "message": message,
            }
        )


def project_verification_scenario(
    scenario_path: Path,
    input_set_manifest: Path,
    profile_path: Path,
) -> dict[str, Any]:
    """Validate an OrbitFabric scenario and project the Stage 7.10 v0 subset."""

    core = load_core_input_set(input_set_manifest)
    profile = load_projection_profile(profile_path)
    loaded, orbitfabric_version = _load_orbitfabric_scenario(scenario_path)

    _validate_core_runtime_and_mission_identity(
        loaded=loaded,
        orbitfabric_version=orbitfabric_version,
        core=core,
    )
    _validate_target_profile_compatibility(core, profile)

    return project_loaded_scenario(
        loaded,
        scenario_path=scenario_path,
        core=core,
        profile=profile,
        orbitfabric_version=orbitfabric_version,
    )


def project_loaded_scenario(
    loaded: Any,
    *,
    scenario_path: Path,
    core: CoreInputSet,
    profile: ProjectionProfile,
    orbitfabric_version: str,
) -> dict[str, Any]:
    """Project an already Core-validated LoadedScenario into a v0 plan."""

    scenario_path = scenario_path.resolve()
    _validate_core_runtime_and_mission_identity(
        loaded=loaded,
        orbitfabric_version=orbitfabric_version,
        core=core,
    )

    scenario = loaded.scenario
    builder = _PlanBuilder()

    builder.add_atom(
        kind="scenario_metadata",
        role="metadata",
        step_index=None,
        scenario_t=None,
        disposition="projected",
        source=None,
    )

    initial_mode = scenario.initial_state.mode
    builder.add_atom(
        kind="initial_mode",
        role="initial_state",
        step_index=None,
        scenario_t=None,
        disposition="not_projected",
        source=_core_source(core, "modes", initial_mode),
        reason=NOT_PROJECTED_REASONS["initial_mode"],
    )

    for telemetry_id in sorted(scenario.initial_state.telemetry):
        builder.add_atom(
            kind="initial_telemetry",
            role="initial_state",
            step_index=None,
            scenario_t=None,
            disposition="not_projected",
            source=_core_source(core, "telemetry", telemetry_id),
            reason=NOT_PROJECTED_REASONS["initial_telemetry"],
        )

    for step_index, step in enumerate(scenario.steps):
        _project_step(
            step=step,
            step_index=step_index,
            core=core,
            profile=profile,
            builder=builder,
        )

    accounting = _build_accounting(builder.atoms, builder.operations)
    status = "blocked" if accounting["blocked_atoms"] > 0 else "executable_subset"

    payload = {
        "kind": "orbitfabric.verification_projection_plan",
        "plan_version": PLAN_VERSION,
        "status": status,
        "source": {
            "scenario_id": scenario.scenario.id,
            "scenario_name": scenario.scenario.name,
            "scenario_description": scenario.scenario.description,
            "scenario_sha256": sha256_file(scenario_path),
            "orbitfabric_version": core.manifest["orbitfabric_version"],
        },
        "core_input": {
            "kind": core.manifest["kind"],
            "input_set_version": core.manifest["input_set_version"],
            "input_set_sha256": core.sha256,
            "mission_id": core.mission["id"],
            "model_version": core.mission["model_version"],
        },
        "profile": {
            "kind": profile.document["kind"],
            "profile_version": profile.document["profile_version"],
            "id": profile.id,
            "version": profile.version,
            "sha256": profile.sha256,
        },
        "integration": {
            "id": INTEGRATION_ID,
            "schema_version": profile.schema_version,
            "adapter": {
                "id": ADAPTER_ID,
                "version": ADAPTER_VERSION,
            },
        },
        "accounting": accounting,
        "atoms": builder.atoms,
        "operations": builder.operations,
        "diagnostics": builder.diagnostics,
    }

    validate_verification_projection_provenance(
        payload,
        scenario_path=scenario_path,
        core=core,
        profile=profile,
    )
    return payload


def _load_orbitfabric_scenario(scenario_path: Path) -> tuple[Any, str]:
    try:
        import orbitfabric
        from orbitfabric.model.errors import MissionModelError
        from orbitfabric.model.scenario_loader import ScenarioLoader
    except ImportError as exc:
        raise AdapterFailure(
            "OFI-VPROJ-SCENARIO-001",
            "verification_projection",
            "OrbitFabric Core runtime is required to validate scenario input",
        ) from exc

    try:
        loaded = ScenarioLoader().load(scenario_path.resolve())
    except MissionModelError as exc:
        details = "; ".join(
            f"{item.code}: {item.message}" for item in exc.diagnostics[:3]
        )
        raise AdapterFailure(
            "OFI-VPROJ-SCENARIO-001",
            "verification_projection",
            f"OrbitFabric scenario validation failed: {details}",
        ) from exc

    return loaded, orbitfabric.__version__


def _validate_core_runtime_and_mission_identity(
    *,
    loaded: Any,
    orbitfabric_version: str,
    core: CoreInputSet,
) -> None:
    expected_version = core.manifest.get("orbitfabric_version")
    if orbitfabric_version != expected_version:
        raise AdapterFailure(
            "OFI-VPROJ-PROVENANCE-001",
            "verification_projection",
            "OrbitFabric scenario validator version does not match the consumed "
            f"Core Integration Input Set producer: runtime={orbitfabric_version!r}, "
            f"input_set={expected_version!r}",
        )

    spacecraft = loaded.mission_model.spacecraft
    actual_identity = (spacecraft.id, spacecraft.model_version)
    expected_identity = (core.mission["id"], core.mission["model_version"])
    if actual_identity != expected_identity:
        raise AdapterFailure(
            "OFI-VPROJ-PROVENANCE-001",
            "verification_projection",
            "Scenario Mission Model identity does not match the consumed Core "
            f"Integration Input Set: scenario={actual_identity!r}, "
            f"input_set={expected_identity!r}",
        )


def _validate_target_profile_compatibility(
    core: CoreInputSet,
    profile: ProjectionProfile,
) -> None:
    """Reuse the established adapter projection preflight without artifacts."""

    resolved = resolve_core_bindings(core, profile)
    baseline_id = profile.document["settings"]["compatibility"]["target_baseline"]
    baseline = load_target_baseline(baseline_id)
    resolve_projection(core, profile, baseline, resolved)


def _project_step(
    *,
    step: Any,
    step_index: int,
    core: CoreInputSet,
    profile: ProjectionProfile,
    builder: _PlanBuilder,
) -> None:
    if step.command is not None:
        _project_command(
            step=step,
            step_index=step_index,
            core=core,
            profile=profile,
            builder=builder,
        )

    if step.inject is not None:
        builder.add_atom(
            kind="telemetry_injection",
            role="action",
            step_index=step_index,
            scenario_t=step.t,
            disposition="not_projected",
            source=_core_source(core, "telemetry", step.inject.telemetry),
            reason=NOT_PROJECTED_REASONS["telemetry_injection"],
        )

    if step.expect_event is not None:
        builder.add_atom(
            kind="expect_event",
            role="expectation",
            step_index=step_index,
            scenario_t=step.t,
            disposition="not_projected",
            source=_core_source(core, "events", step.expect_event),
            reason=NOT_PROJECTED_REASONS["expect_event"],
        )

    if step.expect_mode is not None:
        builder.add_atom(
            kind="expect_mode",
            role="expectation",
            step_index=step_index,
            scenario_t=step.t,
            disposition="not_projected",
            source=_core_source(core, "modes", step.expect_mode),
            reason=NOT_PROJECTED_REASONS["expect_mode"],
        )

    if step.expect_command is not None:
        builder.add_atom(
            kind="expect_command",
            role="expectation",
            step_index=step_index,
            scenario_t=step.t,
            disposition="not_projected",
            source=_core_source(core, "commands", step.expect_command.id),
            reason=NOT_PROJECTED_REASONS["expect_command"],
        )

    if step.expect_telemetry is not None:
        for telemetry_id in sorted(step.expect_telemetry):
            builder.add_atom(
                kind="expect_telemetry",
                role="expectation",
                step_index=step_index,
                scenario_t=step.t,
                disposition="not_projected",
                source=_core_source(core, "telemetry", telemetry_id),
                reason=NOT_PROJECTED_REASONS["expect_telemetry"],
            )

    if step.expect is not None:
        _project_nested_expectations(
            step=step,
            step_index=step_index,
            core=core,
            builder=builder,
        )


def _project_command(
    *,
    step: Any,
    step_index: int,
    core: CoreInputSet,
    profile: ProjectionProfile,
    builder: _PlanBuilder,
) -> None:
    source = _core_source(core, "commands", step.command)

    if step.args:
        reason = (
            "Stage 7.10 v0 cannot project command arguments without an explicit "
            "target argument encoder."
        )
        atom = builder.add_atom(
            kind="command",
            role="action",
            step_index=step_index,
            scenario_t=step.t,
            disposition="blocked",
            source=source,
            reason=reason,
        )
        builder.add_blocking_diagnostic(
            "OFI-VPROJ-CMDARGS-001",
            f"Command {step.command!r} at scenario step {step_index} has arguments "
            "but Stage 7.10 v0 defines no target argument encoder.",
        )
        for argument_name in sorted(step.args):
            builder.add_atom(
                kind="command_argument",
                role="action",
                step_index=step_index,
                scenario_t=step.t,
                disposition="blocked",
                source=source,
                binding_id=atom["binding_id"],
                reason=reason,
            )
        return

    binding, failure = _select_command_binding(profile, step.command)
    if failure is not None:
        code, message, binding_id = failure
        builder.add_atom(
            kind="command",
            role="action",
            step_index=step_index,
            scenario_t=step.t,
            disposition="blocked",
            source=source,
            binding_id=binding_id,
            reason=message,
        )
        builder.add_blocking_diagnostic(code, message)
        return

    assert binding is not None
    binding_id = binding["id"]
    atom = builder.add_atom(
        kind="command",
        role="action",
        step_index=step_index,
        scenario_t=step.t,
        disposition="projected",
        source=source,
        binding_id=binding_id,
    )

    pus = binding["config"]["pus"]
    default_apid = profile.document["settings"]["pus"]["tc_apid"]
    builder.add_operation(
        atom,
        operation="pus_tc",
        binding_id=binding_id,
        origin="profile_mapping",
        resolved={
            "apid": pus.get("apid", default_apid),
            "service": pus["service"],
            "subtype": pus["subtype"],
            "data_hex": "",
        },
    )

    for response in binding["config"].get("expected_responses", []):
        builder.add_operation(
            atom,
            operation="expect_pus_tm",
            binding_id=binding_id,
            origin="profile_expected_response",
            resolved={
                "service": response["service"],
                "subtype": response["subtype"],
            },
        )


def _select_command_binding(
    profile: ProjectionProfile,
    command_id: str,
) -> tuple[dict[str, Any] | None, tuple[str, str, str | None] | None]:
    matching: list[dict[str, Any]] = []
    for binding in profile.bindings:
        sources = binding.get("sources")
        if not isinstance(sources, list) or len(sources) != 1:
            continue
        source = sources[0]
        if source == {"domain": "commands", "id": command_id}:
            matching.append(binding)

    if not matching:
        return None, (
            "OFI-VPROJ-BINDING-001",
            f"Scenario command {command_id!r} has no single-source Profile binding.",
            None,
        )

    if len(matching) > 1:
        return None, (
            "OFI-VPROJ-AMBIGUOUS-001",
            f"Scenario command {command_id!r} matches multiple Profile bindings: "
            + ", ".join(sorted(item["id"] for item in matching)),
            None,
        )

    binding = matching[0]
    if binding.get("intent") != "project":
        return None, (
            "OFI-VPROJ-INTENT-001",
            f"Scenario command {command_id!r} is explicitly do_not_project in "
            f"Profile binding {binding['id']!r}.",
            binding["id"],
        )

    return binding, None


def _project_nested_expectations(
    *,
    step: Any,
    step_index: int,
    core: CoreInputSet,
    builder: _PlanBuilder,
) -> None:
    expectation = step.expect
    assert isinstance(expectation, dict)

    unknown = sorted(set(expectation) - KNOWN_EXPECT_KEYS)
    if unknown:
        raise AdapterFailure(
            "OFI-VPROJ-SCENARIO-002",
            "verification_projection",
            "Scenario contains expectation keys outside the documented Stage 7.10 "
            f"inventory: {unknown}",
        )

    if not expectation:
        raise AdapterFailure(
            "OFI-VPROJ-SCENARIO-002",
            "verification_projection",
            "Scenario contains an empty expect mapping with no documented "
            "expectation semantics.",
        )

    if "command_status" in expectation:
        source = (
            _core_source(core, "commands", step.command)
            if step.command is not None
            else None
        )
        builder.add_atom(
            kind="expect_command_status",
            role="expectation",
            step_index=step_index,
            scenario_t=step.t,
            disposition="not_projected",
            source=source,
            reason=NOT_PROJECTED_REASONS["expect_command_status"],
        )

    if "payload_lifecycle" in expectation:
        payload = expectation["payload_lifecycle"]
        payload_id = payload.get("payload") if isinstance(payload, dict) else None
        source = (
            _core_source(core, "payloads", payload_id)
            if isinstance(payload_id, str)
            else None
        )
        builder.add_atom(
            kind="expect_payload_lifecycle",
            role="expectation",
            step_index=step_index,
            scenario_t=step.t,
            disposition="not_projected",
            source=source,
            reason=NOT_PROJECTED_REASONS["expect_payload_lifecycle"],
        )

    if "data_flow" in expectation:
        data_flow = expectation["data_flow"]
        product_id = (
            data_flow.get("data_product") if isinstance(data_flow, dict) else None
        )
        source = (
            _core_source(core, "data_products", product_id)
            if isinstance(product_id, str)
            else None
        )
        builder.add_atom(
            kind="expect_data_flow",
            role="expectation",
            step_index=step_index,
            scenario_t=step.t,
            disposition="not_projected",
            source=source,
            reason=NOT_PROJECTED_REASONS["expect_data_flow"],
        )

    if "scenario_status" in expectation:
        builder.add_atom(
            kind="expect_scenario_status",
            role="expectation",
            step_index=step_index,
            scenario_t=step.t,
            disposition="not_projected",
            source=None,
            reason=NOT_PROJECTED_REASONS["expect_scenario_status"],
        )


def _core_source(
    core: CoreInputSet,
    domain: str,
    identifier: str,
) -> dict[str, str]:
    try:
        core.resolve_source(domain, identifier)
    except AdapterFailure as exc:
        raise AdapterFailure(
            "OFI-VPROJ-PROVENANCE-001",
            "verification_projection",
            "Scenario source identity does not resolve through the consumed Core "
            f"Integration Input Set: {domain}/{identifier}",
            sources=[{"domain": domain, "id": identifier}],
        ) from exc
    return {"domain": domain, "id": identifier}


def _build_accounting(
    atoms: list[dict[str, Any]],
    operations: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "source_atoms": len(atoms),
        "projected_atoms": sum(
            1 for atom in atoms if atom["disposition"] == "projected"
        ),
        "not_projected_atoms": sum(
            1 for atom in atoms if atom["disposition"] == "not_projected"
        ),
        "blocked_atoms": sum(
            1 for atom in atoms if atom["disposition"] == "blocked"
        ),
        "source_actions": sum(1 for atom in atoms if atom["role"] == "action"),
        "source_expectations": sum(
            1 for atom in atoms if atom["role"] == "expectation"
        ),
        "projected_source_actions": sum(
            1
            for atom in atoms
            if atom["role"] == "action" and atom["disposition"] == "projected"
        ),
        "projected_source_expectations": sum(
            1
            for atom in atoms
            if atom["role"] == "expectation"
            and atom["disposition"] == "projected"
        ),
        "profile_verification_obligations": sum(
            1 for operation in operations if operation["operation"] == "expect_pus_tm"
        ),
    }
