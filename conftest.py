"""Root pytest configuration for QA-Automation."""

import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

OUTCOMES_DIR = Path(os.environ.get("QA_OUTCOMES_DIR", "reports/outcomes"))
ALLURE_RESULTS = Path("allure-results")

_run_timestamp: str = ""
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


def pytest_configure(config):  # noqa: ARG001
    global _run_timestamp
    _run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def pytest_sessionstart(session):  # noqa: ARG001
    _write_allure_environment()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        marker = item.get_closest_marker("testcase")
        if marker:
            _test_results.append({
                "component":   marker.kwargs.get("component", ""),
                "type":        marker.kwargs.get("type", ""),
                "description": marker.kwargs.get("description", ""),
                "steps":       marker.kwargs.get("steps", ""),
                "status":      report.outcome.upper(),
            })


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if not _run_timestamp:
        return

    run_dir = OUTCOMES_DIR / f"run_{_run_timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Allure report
    report_dir = run_dir / "allure-report"
    subprocess.run(
        ["allure", "generate", str(ALLURE_RESULTS), "-o", str(report_dir), "--clean", "--single-file"],
        check=False,
    )

    # Excel report
    if _test_results:
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Font, PatternFill

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Test Results"

            ws.append(["Component", "Type", "Description", "Steps", "Status"])
            for cell in ws[1]:
                cell.font = Font(bold=True)

            status_colors = {"PASSED": "92D050", "FAILED": "FF4C4C", "ERROR": "FFA500"}

            for result in _test_results:
                ws.append([
                    result["component"],
                    result["type"],
                    result["description"],
                    result["steps"],
                    result["status"],
                ])
                last_row = ws.max_row
                color = status_colors.get(result["status"], "FFFFFF")
                ws.cell(last_row, 5).fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                ws.cell(last_row, 4).alignment = Alignment(wrap_text=True)

            ws.column_dimensions["A"].width = 15
            ws.column_dimensions["B"].width = 20
            ws.column_dimensions["C"].width = 55
            ws.column_dimensions["D"].width = 60
            ws.column_dimensions["E"].width = 12

            wb.save(str(run_dir / "test_results.xlsx"))
        except ImportError:
            pass


load_dotenv(Path(__file__).parent / ".env")

from dashboard.fixtures.browser_fixtures import *  # noqa: F401, F403, E402
from dashboard.fixtures.auth_fixtures import *     # noqa: F401, F403, E402
from dashboard.fixtures.api_fixtures import *      # noqa: F401, F403, E402
