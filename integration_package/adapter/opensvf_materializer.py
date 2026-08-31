from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from .io import sha256_file
from .model import AdapterFailure
from .verification_plan import load_verification_projection_plan


MATERIALIZATION_KIND = "orbitfabric.opensvf_materialization"
MATERIALIZATION_VERSION = "0.1-candidate"
DEFAULT_TM_TIMEOUT_S = 5.0

PROCEDURE_REL = Path("procedures") / "verification_projection_procedure.py"
CAMPAIGN_REL = Path("campaigns") / "verification_projection_campaign.yaml"
SPACECRAFT_REL = Path("opensvf") / "spacecraft.yaml"
MANIFEST_REL = Path("materialization_manifest.json")


def materialize_opensvf_plan(
    plan_path: Path,
    spacecraft_path: Path,
    output_dir: Path,
    *,
    tm_timeout_s: float = DEFAULT_TM_TIMEOUT_S,
) -> dict[str, Any]:
    """Materialize one validated Verification Projection Plan into OpenSVF assets."""

    plan_path = plan_path.resolve()
    spacecraft_path = spacecraft_path.resolve()
    output_dir = output_dir.resolve()

    plan = load_verification_projection_plan(plan_path)

    if plan["status"] != "executable_subset":
        raise AdapterFailure(
            "OFI-VPROJ-MAT-001",
            "verification_materialization",
            "Only status=executable_subset plans may be materialized into OpenSVF.",
        )

    if not plan["operations"]:
        raise AdapterFailure(
            "OFI-VPROJ-MAT-001",
            "verification_materialization",
            "Verification Projection Plan contains no executable operations.",
        )

    if tm_timeout_s <= 0:
        raise AdapterFailure(
            "OFI-VPROJ-MAT-001",
            "verification_materialization",
            "OpenSVF TM expectation timeout must be greater than zero.",
        )

    if not spacecraft_path.is_file():
        raise AdapterFailure(
            "OFI-VPROJ-MAT-001",
            "verification_materialization",
            f"OpenSVF spacecraft template does not exist: {spacecraft_path}",
        )

    _prepare_output(output_dir)

    plan_sha256 = sha256_file(plan_path)

    procedure_path = output_dir / PROCEDURE_REL
    campaign_path = output_dir / CAMPAIGN_REL
    materialized_spacecraft_path = output_dir / SPACECRAFT_REL
    manifest_path = output_dir / MANIFEST_REL

    procedure_path.parent.mkdir(parents=True, exist_ok=True)
    campaign_path.parent.mkdir(parents=True, exist_ok=True)
    materialized_spacecraft_path.parent.mkdir(parents=True, exist_ok=True)

    procedure_path.write_text(
        _procedure_source(
            plan,
            plan_sha256=plan_sha256,
            tm_timeout_s=tm_timeout_s,
        ),
        encoding="utf-8",
    )

    materialized_spacecraft_path.write_bytes(spacecraft_path.read_bytes())

    campaign_payload = {
        "campaign": f"OrbitFabric verification projection - {plan['source']['scenario_name']}",
        "spacecraft": "../opensvf/spacecraft.yaml",
        "procedures": ["../procedures/verification_projection_procedure.py"],
    }
    campaign_path.write_text(
        yaml.safe_dump(campaign_payload, sort_keys=False),
        encoding="utf-8",
    )

    operation_trace = []
    for step_index, operation in enumerate(plan["operations"], start=1):
        operation_trace.append(
            {
                "plan_operation_id": operation["id"],
                "plan_operation": operation["operation"],
                "procedure_step_index": step_index,
                "native_primitive": (
                    "ctx.tc"
                    if operation["operation"] == "pus_tc"
                    else "ctx.expect_tm"
                ),
            }
        )

    manifest = {
        "kind": MATERIALIZATION_KIND,
        "materialization_version": MATERIALIZATION_VERSION,
        "source_plan": {
            "kind": plan["kind"],
            "plan_version": plan["plan_version"],
            "sha256": plan_sha256,
            "scenario_id": plan["source"]["scenario_id"],
            "scenario_sha256": plan["source"]["scenario_sha256"],
        },
        "execution_policy": {
            "tm_expectation_timeout_s": tm_timeout_s,
            "scenario_time_interpretation": "provenance_only",
        },
        "spacecraft": {
            "path": SPACECRAFT_REL.as_posix(),
            "sha256": sha256_file(materialized_spacecraft_path),
        },
        "artifacts": [
            {
                "role": "procedure",
                "path": PROCEDURE_REL.as_posix(),
                "sha256": sha256_file(procedure_path),
            },
            {
                "role": "campaign",
                "path": CAMPAIGN_REL.as_posix(),
                "sha256": sha256_file(campaign_path),
            },
            {
                "role": "spacecraft",
                "path": SPACECRAFT_REL.as_posix(),
                "sha256": sha256_file(materialized_spacecraft_path),
            },
        ],
        "operation_trace": operation_trace,
    }

    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _prepare_output(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for relative in (
        PROCEDURE_REL,
        CAMPAIGN_REL,
        SPACECRAFT_REL,
        MANIFEST_REL,
    ):
        path = output_dir / relative
        if path.exists() and path.is_file():
            path.unlink()


def _procedure_source(
    plan: dict[str, Any],
    *,
    plan_sha256: str,
    tm_timeout_s: float,
) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "from svf.campaign.procedure import Procedure, ProcedureContext",
        "",
        "",
        "# Generated from a validated OrbitFabric Verification Projection Plan.",
        f"# plan_sha256: {plan_sha256}",
        f"# scenario_sha256: {plan['source']['scenario_sha256']}",
        "",
        "",
        "class A01_VerificationProjectionProcedure(Procedure):",
        f"    id = {_py_string('OF-VPROJ-' + plan['source']['scenario_id'])}",
        f"    title = {_py_string('Verification projection: ' + plan['source']['scenario_name'])}",
        '    requirement = ""',
        "",
        "    def run(self, ctx: ProcedureContext) -> None:",
    ]

    for operation in plan["operations"]:
        lines.extend(_operation_lines(operation, tm_timeout_s=tm_timeout_s))

    return "\n".join(lines) + "\n"


def _operation_lines(
    operation: dict[str, Any],
    *,
    tm_timeout_s: float,
) -> list[str]:
    resolved = operation["resolved"]
    operation_id = operation["id"]

    if operation["operation"] == "pus_tc":
        data_hex = resolved["data_hex"]
        step = (
            f"{operation_id}: Send PUS TC("
            f"{resolved['service']},{resolved['subtype']})"
        )
        return [
            f"        self.step({_py_string(step)})",
            (
                "        ctx.tc("
                f"service={resolved['service']}, "
                f"subservice={resolved['subtype']}, "
                f"data=bytes.fromhex({_py_string(data_hex)}), "
                f"apid=0x{resolved['apid']:03X})"
            ),
            "",
        ]

    if operation["operation"] == "expect_pus_tm":
        step = (
            f"{operation_id}: Expect PUS TM("
            f"{resolved['service']},{resolved['subtype']})"
        )
        return [
            f"        self.step({_py_string(step)})",
            (
                "        ctx.expect_tm("
                f"service={resolved['service']}, "
                f"subservice={resolved['subtype']}, "
                f"timeout={tm_timeout_s!r})"
            ),
            "",
        ]

    raise AdapterFailure(
        "OFI-VPROJ-MAT-002",
        "verification_materialization",
        f"Unsupported Verification Projection Plan operation: "
        f"{operation['operation']!r}",
    )


def _py_string(value: str) -> str:
    """Return a deterministic Python double-quoted string literal."""

    return json.dumps(value, ensure_ascii=True)
