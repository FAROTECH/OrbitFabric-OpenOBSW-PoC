from __future__ import annotations

from dataclasses import dataclass


INTEGRATION_ID = "openobsw-opensvf-reference"
ADAPTER_ID = "orbitfabric-openobsw-opensvf"
ADAPTER_VERSION = "0.2.0.dev2"
RESULT_KIND = "orbitfabric.integration_result"
RESULT_VERSION = "0.2-lab"


@dataclass(frozen=True)
class AdapterFailure(Exception):
    code: str
    phase: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} [{self.phase}] {self.message}"


def source_ref(domain: str, identifier: str) -> dict[str, str]:
    return {"domain": domain, "id": identifier}


def target_ref(namespace: str, kind: str, identifier: str) -> dict[str, str]:
    return {"namespace": namespace, "kind": kind, "id": identifier}


def diagnostic(
    *,
    identifier: str,
    phase: str,
    severity: str,
    code: str,
    message: str,
    sources: list[dict[str, str]] | None = None,
    profile_bindings: list[str] | None = None,
    targets: list[dict[str, str]] | None = None,
) -> dict:
    return {
        "id": identifier,
        "owner": "integration",
        "producer": INTEGRATION_ID,
        "phase": phase,
        "severity": severity,
        "code": code,
        "message": message,
        "sources": sources or [],
        "profile_bindings": profile_bindings or [],
        "targets": targets or [],
    }
