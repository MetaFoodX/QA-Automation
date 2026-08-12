"""Shared helpers for the Xray scripts — extracting testcase marker metadata
from source, reading pytest's junit.xml, and authenticating against Xray Cloud.
"""
import ast
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

TESTS_ROOT = Path("dashboard/tests")
JUNIT_PATH = Path("reports/junit.xml")
PROJECT_KEY = "FQL"
TEST_TYPE = "Generic"
AUTH_URL = "https://xray.cloud.getxray.app/api/v2/authenticate"
IMPORT_URL = "https://xray.cloud.getxray.app/api/v2/import/execution"
GRAPHQL_URL = "https://xray.cloud.getxray.app/api/v2/graphql"
LABEL_MARKERS = {"smoke", "regression", "slow", "flaky", "wip"}


def classname_for(path: Path) -> str:
    return ".".join(path.with_suffix("").parts)


def build_definition(file: Path, function: str, steps: str | None) -> str:
    text = f"Location in code : {file}::{function}"
    if steps:
        text += f"\n\nSteps:\n{steps}"
    return text


def extract_tests():
    """Walk dashboard/tests, returning one dict per @pytest.mark.testcase(...)
    test: its component/description/steps/labels, any already-stamped Xray
    `key`, and the decorator's end line (for stamping a new key back in)."""
    entries = []
    for path in sorted(TESTS_ROOT.rglob("test_*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue

            testcase_call = None
            labels = []
            for dec in node.decorator_list:
                call = dec if isinstance(dec, ast.Call) else None
                attr = call.func.attr if call and isinstance(call.func, ast.Attribute) else getattr(dec, "attr", None)
                if attr == "testcase" and call:
                    testcase_call = call
                elif attr in LABEL_MARKERS:
                    labels.append(attr)
            if testcase_call is None:
                continue

            kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in testcase_call.keywords if kw.arg != "key"}
            key = next((ast.literal_eval(kw.value) for kw in testcase_call.keywords if kw.arg == "key"), None)
            entries.append({
                "file": path,
                "function": node.name,
                "classname": classname_for(path),
                "component": kwargs.get("component"),
                "description": kwargs.get("description"),
                "steps": kwargs.get("steps"),
                "labels": sorted(labels),
                "key": key,
                "call_end_lineno": testcase_call.end_lineno,
            })
    return entries


def load_junit_results():
    """Map (classname, test name) -> (status, message) from pytest's junit.xml."""
    tree = ET.parse(JUNIT_PATH)
    results = {}
    for tc in tree.getroot().iter("testcase"):
        node_key = (tc.get("classname"), tc.get("name"))
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")
        if failure is not None:
            results[node_key] = ("FAILED", (failure.get("message") or "")[:1000])
        elif error is not None:
            results[node_key] = ("FAILED", (error.get("message") or "")[:1000])
        elif skipped is not None:
            results[node_key] = ("TODO", (skipped.get("message") or "")[:1000])
        else:
            results[node_key] = ("PASSED", "")
    return results


def authenticate():
    resp = requests.post(AUTH_URL, json={
        "client_id": os.environ["XRAY_CLIENT_ID"],
        "client_secret": os.environ["XRAY_CLIENT_SECRET"],
    })
    resp.raise_for_status()
    return resp.text.strip('"')


def build_summary(build):
    """'Dashboard Regression - Build 24 - main @ 23d609f3', trimmed down to just
    the build number when DEPLOYED_BRANCH/DEPLOYED_COMMIT aren't set (local runs)."""
    summary = f"Dashboard Regression - Build {build}"
    branch = os.environ.get("DEPLOYED_BRANCH")
    commit = os.environ.get("DEPLOYED_COMMIT")
    if branch and branch != "unknown":
        summary += f" - {branch}"
    if commit and commit != "unknown":
        summary += f" @ {commit}"
    return summary


def push_execution_results(entries, build):
    """entries: list of {"key": str, "status": str, "comment": str (optional)}.
    Never creates a Test — every entry must already carry a real Xray key.
    Creates one new Test Execution tagged with `build` (a real Jenkins build
    number in CI, or a human-readable label for a manual run)."""
    payload_tests = [
        {"status": e["status"], "testKey": e["key"], **({"comment": e["comment"]} if e.get("comment") else {})}
        for e in entries
    ]
    payload = {
        "info": {
            "project": PROJECT_KEY,
            "summary": build_summary(build),
            "revision": str(build),
        },
        "tests": payload_tests,
    }
    token = authenticate()
    resp = requests.post(IMPORT_URL, headers={"Authorization": f"Bearer {token}"}, json=payload)
    resp.raise_for_status()
    return resp.json()
