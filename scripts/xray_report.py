"""Report pytest results to Xray Cloud. Safe to run from Jenkins — this script
NEVER creates a Test issue. It only reports results against tests that already
have a `key=` stamped in their testcase marker (via xray_onboard.py).

Any test that ran but has no key is skipped with a warning, not auto-created —
onboarding new tests is a separate, deliberate, human-run step.

Usage:
    pytest dashboard/tests/ --ignore=dashboard/tests/test_seed.py   # writes reports/junit.xml
    python scripts/xray_report.py --build local --dry-run           # preview, sends nothing
    python scripts/xray_report.py --build local                     # actually push
    python scripts/xray_report.py --build $BUILD_NUMBER              # from Jenkins
    python scripts/xray_report.py --build 36 --execution-key FQL-199 # fill an existing execution
"""
import argparse
import json
from pathlib import Path

from xray_common import extract_tests, load_junit_results, push_execution_results


def build_entries():
    """Match dashboard/tests source (via extract_tests) against reports/junit.xml,
    returning (keyed_entries, skipped_unkeyed_names)."""
    entries = extract_tests()
    junit_results = load_junit_results()

    keyed, skipped_unkeyed = [], []
    for e in entries:
        result = junit_results.get((e["classname"], e["function"]))
        if result is None:
            continue
        if not e["key"]:
            skipped_unkeyed.append(e["function"])
            continue
        status, message = result
        entry = {"key": e["key"], "status": status}
        if message:
            entry["comment"] = message
        keyed.append(entry)
    return keyed, skipped_unkeyed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", default="Local Execution")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execution-key", default=None,
                         help="Fill an existing Test Execution (e.g. FQL-199) instead of creating a new one")
    args = parser.parse_args()

    keyed, skipped_unkeyed = build_entries()

    if skipped_unkeyed:
        print(f"WARNING: {len(skipped_unkeyed)} test(s) ran but have no Xray key yet — "
              f"skipped, not reported. Run scripts/xray_onboard.py locally to onboard them:")
        for name in skipped_unkeyed:
            print(f"  - {name}")

    if not keyed:
        print("Nothing to report — no keyed tests matched reports/junit.xml.")
        return

    print(f"{len(keyed)} result(s) to report for build '{args.build}'.")

    if args.dry_run:
        Path("reports/xray_report_payload.json").write_text(json.dumps(keyed, indent=2))
        print("Dry run only — wrote reports/xray_report_payload.json, nothing sent to Xray.")
        return

    execution = push_execution_results(keyed, args.build, existing_key=args.execution_key)
    print(f"Reported. Test Execution: {execution['key']}")


if __name__ == "__main__":
    main()
