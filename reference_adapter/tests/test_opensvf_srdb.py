from __future__ import annotations

from copy import deepcopy

from orbitfabric_openobsw_opensvf.opensvf_srdb import (
    OpenSvfSrdbError,
    render_opensvf_srdb,
)
from orbitfabric_openobsw_opensvf.projection_pipeline import _resolve_opensvf_telemetry
from orbitfabric_openobsw_opensvf.validator import ValidationInputError


def _resolved_before_opensvf() -> dict:
    return {
        "kind": "orbitfabric.openobsw_opensvf.resolved_projection",
        "resolved_projection_version": "0.1-candidate",
        "settings": {"opensvf": {"domain_apids": {"EPS": 0x100}}},
        "projections": [
            {
                "binding_id": "tm.obc_bus_voltage",
                "kind": "telemetry_parameter",
                "sources": [{"domain": "telemetry", "id": "eps.obc.bus_voltage_mv"}],
                "core_semantics": {
                    "origin": "core",
                    "source": {
                        "id": "eps.obc.bus_voltage_mv",
                        "description": "OBC bus voltage in raw millivolts.",
                        "unit": "mV",
                        "type": "uint16",
                        "source": "eps",
                    },
                },
                "target": {
                    "kind": "telemetry_parameter",
                    "numeric_id": 0x4001,
                    "srdb_name": "eps.obc.bus_voltage_mv",
                },
                "resolutions": [],
            },
            {
                "binding_id": "hk.obc",
                "kind": "housekeeping_packet",
                "sources": [{"domain": "packets", "id": "obc_hk"}],
                "core_semantics": {
                    "origin": "core",
                    "source": {
                        "id": "obc_hk",
                        "telemetry": ["eps.obc.bus_voltage_mv"],
                    },
                },
                "target": {
                    "kind": "housekeeping_packet",
                    "pus": {"service": 3, "subservice": 25},
                    "members": [
                        {
                            "core_id": "eps.obc.bus_voltage_mv",
                            "c_type": "uint16_t",
                            "field_name": "obc_bus_voltage_mv",
                        }
                    ],
                },
                "resolutions": [],
            },
        ],
    }


def _telemetry(payload: dict) -> dict:
    return next(item for item in payload["projections"] if item["kind"] == "telemetry_parameter")


def test_opensvf_resolution_combines_core_profile_and_hk_projection() -> None:
    payload = _resolved_before_opensvf()
    _resolve_opensvf_telemetry(payload)
    telemetry = _telemetry(payload)
    assert telemetry["target"]["opensvf"] == {
        "dtype": "int",
        "classification": "TM",
        "domain": "EPS",
        "model_id": "eps",
        "valid_range": [0.0, 65535.0],
        "pus": {
            "apid": 0x100,
            "service": 3,
            "subservice": 25,
            "parameter_id": 0x4001,
        },
    }
    service = next(
        item
        for item in telemetry["resolutions"]
        if item["property"] == "target.opensvf.pus.service"
    )
    assert service["origin"] == "profile"
    assert service["source_bindings"] == ["hk.obc"]


def test_ambiguous_hk_pus_mapping_is_rejected() -> None:
    payload = _resolved_before_opensvf()
    second = deepcopy(payload["projections"][1])
    second["binding_id"] = "hk.other"
    second["target"]["pus"] = {"service": 3, "subservice": 26}
    payload["projections"].append(second)
    try:
        _resolve_opensvf_telemetry(payload)
    except ValidationInputError as exc:
        assert "ambiguous HK PUS mappings" in str(exc)
    else:
        raise AssertionError("expected ValidationInputError")


def test_render_srdb_uses_only_resolved_opensvf_target() -> None:
    payload = _resolved_before_opensvf()
    _resolve_opensvf_telemetry(payload)
    text = render_opensvf_srdb(payload)
    assert "parameters:" in text
    assert "  eps.obc.bus_voltage_mv:" in text
    assert '    unit: "mV"' in text
    assert "    dtype: int" in text
    assert "    classification: TM" in text
    assert "    domain: EPS" in text
    assert "    model_id: eps" in text
    assert "    valid_range: [0.0, 65535.0]" in text
    assert "      apid: 0x100" in text
    assert "      service: 3" in text
    assert "      subservice: 25" in text
    assert "      parameter_id: 0x4001" in text


def test_srdb_materializer_does_not_invent_missing_opensvf_resolution() -> None:
    payload = _resolved_before_opensvf()
    try:
        render_opensvf_srdb(payload)
    except OpenSvfSrdbError as exc:
        assert "opensvf" in str(exc)
    else:
        raise AssertionError("expected OpenSvfSrdbError")
