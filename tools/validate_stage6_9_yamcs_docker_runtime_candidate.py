#!/usr/bin/env python3
"""Validate Stage 6.9 Docker-based YAMCS runtime candidate."""

from __future__ import annotations

import argparse
import http.client
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

YAMCS_DIR = REPO_ROOT / "execution" / "yamcs"
DOCKERFILE = YAMCS_DIR / "Dockerfile.candidate"
COMPOSE_FILE = YAMCS_DIR / "docker-compose.candidate.yml"
YAMCS_YAML = YAMCS_DIR / "etc" / "yamcs.yaml"
INSTANCE_YAML = YAMCS_DIR / "etc" / "yamcs.opensvf.yaml"
PROCESSOR_YAML = YAMCS_DIR / "etc" / "processor.yaml"
MDB_PATH = REPO_ROOT / "execution" / "generated" / "poc_xtce_mdb.xml"

EXPECTED_YAMCS_VERSION = "5.12.6"
EXPECTED_IMAGE = "orbitfabric-yamcs-minimal-candidate:stage6.9-local"
EXPECTED_CONTAINER = "orbitfabric-stage6-9-yamcs-candidate"
EXPECTED_INSTANCE = "opensvf"
EXPECTED_MDB_CONTAINER_PATH = "/yamcs/mdb/poc_xtce_mdb.xml"
EXPECTED_PARAMETER_NAME = "eps_obc_bus_voltage_mv"
EXPECTED_HK_CONTAINER_NAME = "TM_3_25_HK"


def fail(message: str) -> None:
    raise SystemExit(
        "Stage 6.9 Docker-based YAMCS runtime candidate: FAIL\n"
        f"{message}"
    )


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    text = read_text(path)
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        fail(f"YAML parse failed for {path}: {exc}")

    if not isinstance(loaded, dict):
        fail(f"YAML root must be a mapping: {path}")

    return loaded


def require_contains(text: str, marker: str, path: Path) -> None:
    if marker not in text:
        fail(f"Missing marker in {path}: {marker}")


def validate_dockerfile() -> None:
    text = read_text(DOCKERFILE)

    for marker in [
        "FROM ubuntu:24.04",
        "openjdk-21-jre-headless",
        f"yamcs-{EXPECTED_YAMCS_VERSION}-linux-x86_64.tar.gz",
        "EXPOSE 8090 10015 10025/udp",
        'CMD ["/opt/yamcs/bin/yamcsd", "--etc-dir", "/yamcs/etc"]',
    ]:
        require_contains(text, marker, DOCKERFILE)


def validate_compose() -> None:
    compose = load_yaml(COMPOSE_FILE)
    yamcs = compose.get("services", {}).get("yamcs")
    if not isinstance(yamcs, dict):
        fail("Compose file must define services.yamcs")

    if yamcs.get("image") != EXPECTED_IMAGE:
        fail(f"Unexpected candidate image: {yamcs.get('image')}")

    if yamcs.get("container_name") != EXPECTED_CONTAINER:
        fail(f"Unexpected candidate container name: {yamcs.get('container_name')}")

    build = yamcs.get("build")
    if not isinstance(build, dict) or build.get("dockerfile") != "Dockerfile.candidate":
        fail("Compose build.dockerfile must be Dockerfile.candidate")

    ports = yamcs.get("ports")
    if not isinstance(ports, list):
        fail("Compose service must define ports")

    for expected_port in ["8090:8090", "10015:10015", "10025:10025/udp"]:
        if expected_port not in ports:
            fail(f"Compose service missing port mapping: {expected_port}")

    volumes = yamcs.get("volumes")
    if not isinstance(volumes, list):
        fail("Compose service must define volumes")

    for expected_volume in [
        "./etc:/yamcs/etc:ro",
        "../generated/poc_xtce_mdb.xml:/yamcs/mdb/poc_xtce_mdb.xml:ro",
    ]:
        if expected_volume not in volumes:
            fail(f"Compose service missing volume mapping: {expected_volume}")


def validate_yamcs_config() -> None:
    yamcs = load_yaml(YAMCS_YAML)

    instances = yamcs.get("instances")
    if not isinstance(instances, list) or EXPECTED_INSTANCE not in instances:
        fail(f"yamcs.yaml must declare instance {EXPECTED_INSTANCE}")

    services = yamcs.get("services")
    if not isinstance(services, list):
        fail("yamcs.yaml must declare services")

    for service in services:
        if isinstance(service, dict) and service.get("class") == "org.yamcs.http.HttpServer":
            args = service.get("args")
            if isinstance(args, dict) and args.get("port") == 8090:
                return

    fail("yamcs.yaml must declare org.yamcs.http.HttpServer on port 8090")


def validate_instance_config() -> None:
    instance = load_yaml(INSTANCE_YAML)
    data_links = instance.get("dataLinks")
    if not isinstance(data_links, list):
        fail("yamcs.opensvf.yaml must declare dataLinks")

    tm_link = next((x for x in data_links if isinstance(x, dict) and x.get("name") == "tm-in"), None)
    if not isinstance(tm_link, dict):
        fail("Missing tm-in data link")

    expected_tm = {
        "class": "org.yamcs.tctm.TcpTmDataLink",
        "host": "127.0.0.1",
        "port": 10015,
        "stream": "tm_realtime",
        "packetPreprocessorClassName": "org.yamcs.pus.PusPacketPreprocessor",
    }
    for key, expected in expected_tm.items():
        if tm_link.get(key) != expected:
            fail(f"Unexpected tm-in {key}: {tm_link.get(key)}")

    preprocessor_args = tm_link.get("packetPreprocessorArgs")
    if not isinstance(preprocessor_args, dict) or preprocessor_args.get("useLocalGenerationTime") is not True:
        fail("tm-in must set useLocalGenerationTime: true")

    tc_link = next((x for x in data_links if isinstance(x, dict) and x.get("name") == "tc-out"), None)
    if not isinstance(tc_link, dict):
        fail("Missing tc-out data link")

    expected_tc = {
        "class": "org.yamcs.tctm.UdpTcDataLink",
        "host": "127.0.0.1",
        "port": 10025,
        "stream": "tc_realtime",
    }
    for key, expected in expected_tc.items():
        if tc_link.get(key) != expected:
            fail(f"Unexpected tc-out {key}: {tc_link.get(key)}")

    mdb = instance.get("mdb")
    if not isinstance(mdb, list) or not isinstance(mdb[0], dict):
        fail("yamcs.opensvf.yaml must declare mdb")

    if mdb[0].get("type") != "xtce":
        fail("MDB type must be xtce")

    if mdb[0].get("spec") != EXPECTED_MDB_CONTAINER_PATH:
        fail(f"Unexpected MDB spec path: {mdb[0].get('spec')}")


def validate_processor_config() -> None:
    processor = load_yaml(PROCESSOR_YAML)
    realtime = processor.get("realtime")
    if not isinstance(realtime, dict):
        fail("processor.yaml must define realtime")

    services = realtime.get("services")
    if not isinstance(services, list):
        fail("processor.yaml realtime.services must be a list")

    service_classes = {s.get("class") for s in services if isinstance(s, dict)}
    for expected_class in [
        "org.yamcs.StreamTmPacketProvider",
        "org.yamcs.StreamTcCommandReleaser",
        "org.yamcs.algorithms.AlgorithmManager",
        "org.yamcs.parameter.LocalParameterManager",
    ]:
        if expected_class not in service_classes:
            fail(f"processor.yaml missing service class: {expected_class}")


def validate_mdb() -> None:
    xml_text = read_text(MDB_PATH)

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        fail(f"Generated XTCE/MDB is not valid XML: {exc}")

    ns = {"xtce": "http://www.omg.org/spec/XTCE/20180204"}

    parameter = root.find(f".//xtce:Parameter[@name='{EXPECTED_PARAMETER_NAME}']", ns)
    if parameter is None:
        fail(f"Generated XTCE/MDB does not contain parameter {EXPECTED_PARAMETER_NAME}")

    hk_container = root.find(f".//xtce:SequenceContainer[@name='{EXPECTED_HK_CONTAINER_NAME}']", ns)
    if hk_container is None:
        fail(f"Generated XTCE/MDB does not contain sequence container {EXPECTED_HK_CONTAINER_NAME}")


def run_capture(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.stdout:
        print(result.stdout.rstrip())

    if check and result.returncode != 0:
        fail(f"Command failed: {' '.join(cmd)}")

    return result


def fetch_yamcs_api() -> dict[str, Any]:
    with urllib.request.urlopen("http://localhost:8090/api/", timeout=2.0) as response:
        payload = response.read().decode("utf-8")

    loaded = json.loads(payload)
    if not isinstance(loaded, dict):
        fail("YAMCS API response must be a JSON object")

    return loaded


def validate_runtime_smoke(keep_running: bool) -> None:
    compose_cmd = ["docker", "compose", "-f", str(COMPOSE_FILE)]

    run_capture(compose_cmd + ["down", "--remove-orphans"], check=False)

    started = False
    try:
        run_capture(compose_cmd + ["up", "--build", "-d"])
        started = True

        deadline = time.monotonic() + 90.0
        api = None
        while time.monotonic() < deadline:
            try:
                api = fetch_yamcs_api()
                break
            except (
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
                http.client.HTTPException,
                ConnectionError,
                OSError,
            ):
                time.sleep(1.0)

        if api is None:
            logs = run_capture(compose_cmd + ["logs", "--no-color", "yamcs"], check=False)
            fail("YAMCS HTTP API did not become ready on http://localhost:8090/api/\n" + logs.stdout)

        if api.get("yamcsVersion") != EXPECTED_YAMCS_VERSION:
            fail(f"Unexpected YAMCS API version: {api.get('yamcsVersion')}")

        if api.get("defaultYamcsInstance") != EXPECTED_INSTANCE:
            fail(f"Unexpected default YAMCS instance: {api.get('defaultYamcsInstance')}")

        run_capture(
            compose_cmd
            + [
                "exec",
                "-T",
                "yamcs",
                "sh",
                "-lc",
                "test -x /opt/yamcs/bin/yamcsd && "
                "test -f /yamcs/mdb/poc_xtce_mdb.xml && "
                "grep -q eps_obc_bus_voltage_mv /yamcs/mdb/poc_xtce_mdb.xml && "
                "grep -q TM_3_25_HK /yamcs/mdb/poc_xtce_mdb.xml",
            ]
        )

        logs = run_capture(compose_cmd + ["logs", "--no-color", "yamcs"])
        log_text = logs.stdout

        log_payload = []
        for line in log_text.splitlines():
            if "|" in line:
                line = line.split("|", 1)[1]
            log_payload.append(line)

        normalized_log = re.sub(r"\s+", " ", "\n".join(log_payload))

        required_log_markers = [
            (
                "XTCE MDB parse finish",
                "XTCE file parsing finished",
            ),
            (
                "MDB import cardinality",
                "loaded: 3 parameters, 7 tm containers, 2 commands",
            ),
            (
                "YAMCS version",
                "Yamcs 5.12.6",
            ),
            (
                "YAMCS started",
                "Yamcs started",
            ),
            (
                "HTTP API request",
                "GET /api/ 200",
            ),
        ]

        for label, marker in required_log_markers:
            if marker not in normalized_log:
                fail(f"Runtime log missing marker {label}: {marker}")

        print("Runtime smoke: PASS")
    finally:
        if started and not keep_running:
            run_capture(compose_cmd + ["down", "--remove-orphans"], check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-smoke", action="store_true")
    parser.add_argument("--keep-running", action="store_true")
    args = parser.parse_args()

    validate_dockerfile()
    validate_compose()
    validate_yamcs_config()
    validate_instance_config()
    validate_processor_config()
    validate_mdb()

    print("Stage 6.9 Docker-based YAMCS runtime candidate")
    print(f"Repository root: {REPO_ROOT}")
    print(f"YAMCS candidate directory: {YAMCS_DIR.relative_to(REPO_ROOT)}")
    print(f"Dockerfile: {DOCKERFILE.relative_to(REPO_ROOT)}")
    print(f"Compose file: {COMPOSE_FILE.relative_to(REPO_ROOT)}")
    print(f"Generated XTCE/MDB: {MDB_PATH.relative_to(REPO_ROOT)}")
    print(f"YAMCS version target: {EXPECTED_YAMCS_VERSION}")
    print("HTTP port: 8090")
    print("TM TCP port: 10015")
    print("TC UDP port: 10025")
    print("Closed-loop TM/TC runtime execution: false")
    print("Static candidate validation: PASS")

    if args.runtime_smoke:
        validate_runtime_smoke(args.keep_running)

    print("Stage 6.9 Docker-based YAMCS runtime candidate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
