from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

INTEGRATION_ID = "orbitfabric-openobsw-opensvf"
ADAPTER_ID = INTEGRATION_ID
ADAPTER_VERSION = "0.1.0-dev.2"
RESULT_VERSION = "0.1-candidate"
PROFILE_VERSION = "0.1-candidate"
PROFILE_SCHEMA_VERSION = "0.1-candidate"
INPUT_SET_VERSION = "0.1-candidate"
PRODUCER = INTEGRATION_ID


@dataclass
class AdapterFailure(Exception):
    code: str
    phase: str
    message: str
    sources: list[dict[str, str]] = field(default_factory=list)
    profile_bindings: list[str] = field(default_factory=list)
    targets: list[dict[str, str]] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def as_diagnostic(self, diagnostic_id: str = "diag-001") -> dict[str, Any]:
        return {
            "id": diagnostic_id,
            "owner": "integration",
            "producer": PRODUCER,
            "phase": self.phase,
            "severity": "ERROR",
            "code": self.code,
            "message": self.message,
            "sources": self.sources,
            "profile_bindings": self.profile_bindings,
            "targets": self.targets,
        }
