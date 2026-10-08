"""Root pytest configuration for QA-Automation.

Reporting is deliberately split in two:
  - THIS file only ever records what happened in ITS OWN pytest process, as a
    small raw JSON dump under reports/_raw/. It never builds the Excel sheet,
    never calls `allure generate`, never talks to Xray.
  - scripts/finalize_report.py is the only thing that turns raw dumps + the
    accumulated allure-results/ into the one Excel file, one Allure HTML, and
    one Xray push a human/Jenkins actually looks at.

Why: a single logical test run (e.g. "smoke suite") can span several pytest
PROCESSES — run_qa.sh's main-suite pass and its separate weekly-report pass,
and (via scripts/run_suite.sh) up to 3 attempts of each pass when retrying
failures with `--last-failed`. If every process generated its own report,
retrying 10 failures would produce a confusing extra Excel/Allure/Xray-push
containing just those 10 — hence dump-here, merge-once-at-the-end-there.
"""

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

RAW_DIR = Path(os.environ.get("QA_RAW_DIR", "reports/_raw"))
ALLURE_RESULTS = Path("allure-results")

_test_results: list[dict] = []


def _fetch_deployed_branch() -> str:
    return os.environ.get("DEPLOYED_BRANCH", "unknown")


def _write_allure_environment():
    branch   = _fetch_deployed_branch()
    env      = os.environ.get("ENV", "staging")
    base_url = os.environ.get("BASE_URL", "https://staging-mercato.skoopin.net")
    ALLURE_RESULTS.mkdir(parents=True, exist_ok=True)
    (ALLURE_RESULTS / "environment.properties").write_text(
        f"Deployed.Branch={branch}\n"
        f"Environment={env}\n"
        f"Base.URL={base_url}\n"
    )


def pytest_sessionstart(session):  # noqa: ARG001
    _write_allure_environment()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.outcome == "rerun":
        return
    # A test skipped via a marker (e.g. @pytest.mark.skip) — or one whose
    # fixture setup itself errors — is decided during "setup", before "call"
    # ever runs, so there is no "call" phase report for it at all. Missing
    # this meant skip-marked tests (and setup errors) vanished from every
    # downstream report instead of showing up as skipped/errored.
    is_relevant = report.when == "call" or (report.when == "setup" and not report.passed)
    if is_relevant:
        marker = item.get_closest_marker("testcase")
        if marker:
            # classname/function mirror exactly how scripts/xray_common.py's
            # extract_tests() identifies the same test from source (dotted
            # module path + function name) — this is also this test's merge
            # key across multiple raw dumps, see finalize_report.py.
            filepath = Path(item.location[0])
            _test_results.append({
                "classname":    ".".join(filepath.with_suffix("").parts),
                "function":     item.location[2],
                "component":    marker.kwargs.get("component", ""),
                "type":         marker.kwargs.get("type", ""),
                "description":  marker.kwargs.get("description", ""),
                "steps":        marker.kwargs.get("steps", ""),
                "status":       report.outcome.upper(),
                "error_detail": report.longreprtext if report.failed else "",
            })


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Dump this process's own results — nothing more. See the module
    docstring: scripts/finalize_report.py is what turns these (plus whatever
    other raw dumps already exist from earlier attempts/passes in this same
    run) into the one Excel/Allure/Xray report a human looks at.

    QA_RUN_LABEL / QA_RUN_ATTEMPT let scripts/run_suite.sh tell us which pass
    and which retry attempt this process is, so dumps don't collide and merge
    in the right order (later attempt overwrites earlier for the same test).
    Default label mirrors the old auto-detection for ad hoc standalone runs
    (e.g. a developer running `pytest ...` directly, not through run_suite.sh).
    """
    if not _test_results:
        return

    label = os.environ.get("QA_RUN_LABEL")
    if not label:
        modules = {item.module.__name__.rsplit(".", 1)[-1] for item in session.items}
        label = (
            "weekly_report_cases"
            if modules == {"test_weekly_service_line_report"}
            else "summary_cases"
        )
    attempt = os.environ.get("QA_RUN_ATTEMPT", "1")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dump_path = RAW_DIR / f"{label}_attempt{int(attempt):02d}.json"
    dump_path.write_text(json.dumps(_test_results, indent=2))
    print(f"Recorded {len(_test_results)} result(s) -> {dump_path} "
          f"(run `python scripts/finalize_report.py` for the Excel/Allure/Xray report)")


load_dotenv(Path(__file__).parent / ".env")

from dashboard.fixtures.browser_fixtures import *  # noqa: F401, F403, E402
from dashboard.fixtures.auth_fixtures import *     # noqa: F401, F403, E402
from dashboard.fixtures.api_fixtures import *      # noqa: F401, F403, E402
