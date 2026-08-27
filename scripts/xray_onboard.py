"""Onboard new tests into Xray Cloud. Run LOCALLY BY A HUMAN, never from Jenkins.

For any test whose testcase marker has no `key=` yet, this creates the Test
issue in Xray (with the first result attached), then stamps the returned key
back into the source as `key="FQL-xxx"`. Commit that change as part of the
test's normal PR — that committed key is what lets CI report results against
it later without ever needing to create anything itself.

Usage:
    pytest dashboard/tests/ --ignore=dashboard/tests/test_seed.py   # writes reports/junit.xml
    python scripts/xray_onboard.py --dry-run                        # preview, sends nothing
    python scripts/xray_onboard.py                                  # actually create + stamp
    python scripts/xray_onboard.py --limit 1                        # validate on one test first
"""
import argparse
import json
from pathlib import Path

import requests

from xray_common import (
    GRAPHQL_URL,
    IMPORT_URL,
    PROJECT_KEY,
    TEST_TYPE,
    authenticate,
    build_definition,
    extract_tests,
    load_junit_results,
)


def stamp_keys(by_file):
    for file, inserts in by_file.items():
        lines = file.read_text().splitlines(keepends=True)
        for end_lineno, key in sorted(inserts, reverse=True):
            lines.insert(end_lineno - 1, f'    key="{key}",\n')
        file.write_text("".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="only onboard the first N unkeyed tests, for validation")
    args = parser.parse_args()

    entries = extract_tests()
    junit_results = load_junit_results()

    unkeyed = [e for e in entries if not e["key"] and (e["classname"], e["function"]) in junit_results]
    total_unkeyed = len(unkeyed)
    limit = min(args.limit, 100) if args.limit is not None else 100
    unkeyed = unkeyed[:limit]

    if not unkeyed:
        print("Nothing to onboard — every test that ran already has an Xray key.")
        return

    if total_unkeyed > len(unkeyed):
        print(f"{total_unkeyed} tests need onboarding — capping this run at {len(unkeyed)} "
              f"(the key-lookup query maxes out at 100 per batch). Re-run after this to onboard the rest.")

    # Jira's issue Summary field can't exceed 255 characters. Rather than
    # silently truncating a test's description (which would make the Jira
    # title diverge from the source), refuse to onboard anything until every
    # description in this batch fits -- shorten the offending description= in
    # source and re-run.
    SUMMARY_MAX_LEN = 255
    too_long = [
        (e["function"], len(e["description"] or e["function"]))
        for e in unkeyed
        if len(e["description"] or e["function"]) > SUMMARY_MAX_LEN
    ]
    if too_long:
        print(f"ABORTING — {len(too_long)} test(s) have a description longer than "
              f"{SUMMARY_MAX_LEN} characters (Jira's Summary field limit). Shorten these in source, "
              f"then re-run:")
        for name, length in too_long:
            print(f"  - {name} ({length} chars)")
        return

    payload_tests = []
    for e in unkeyed:
        status, message = junit_results[(e["classname"], e["function"])]
        test_obj = {
            "status": status,
            "testInfo": {
                "projectKey": PROJECT_KEY,
                "summary": e["description"] or e["function"],
                "type": TEST_TYPE,
                "labels": e["labels"],
                "definition": build_definition(e["file"], e["function"], e["steps"]),
            },
        }
        if message:
            test_obj["comment"] = message
        payload_tests.append(test_obj)

    payload = {
        "info": {
            "project": PROJECT_KEY,
            "summary": "Xray onboarding - new tests",
            "revision": "onboarding",
        },
        "tests": payload_tests,
    }

    print(f"About to create {len(unkeyed)} new Test issue(s) in {PROJECT_KEY}.")

    if args.dry_run:
        Path("reports/xray_onboard_payload.json").write_text(json.dumps(payload, indent=2))
        print("Dry run only — wrote reports/xray_onboard_payload.json, nothing sent to Xray.")
        return

    token = authenticate()

    # Snapshot every test key that exists in the project BEFORE sending anything,
    # so after the import we can tell for certain whether each linked test is a
    # key we've never seen (genuinely created) or one that already existed
    # (Xray reused/overwrote an existing Test instead of creating a new one).
    print("Snapshotting existing test keys before import ...")
    pre_query = """
    query($jql: String!) {
      getTests(jql: $jql, limit: 100) {
        total
        results { jira(fields: ["key", "created"]) }
      }
    }
    """
    pre_resp = requests.post(
        GRAPHQL_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"query": pre_query, "variables": {"jql": f"project = {PROJECT_KEY}"}},
    )
    pre_resp.raise_for_status()
    pre_data = pre_resp.json()["data"]["getTests"]
    keys_before = {t["jira"]["key"]: t["jira"]["created"] for t in pre_data["results"]}
    print(f"Snapshot: {len(keys_before)} test(s) already exist in {PROJECT_KEY} before this run.")

    resp = requests.post(IMPORT_URL, headers={"Authorization": f"Bearer {token}"}, json=payload)
    if not resp.ok:
        print(f"Xray rejected the push: HTTP {resp.status_code} {resp.reason}")
        print(f"Response headers: {dict(resp.headers)}")
        print(f"Response body (full, {len(resp.content)} bytes): {resp.text}")
        resp.raise_for_status()
    execution = resp.json()
    print(f"Created Test Execution {execution['key']} with {len(unkeyed)} new test(s).")

    gql = """
    query($issueId: String!) {
      getTestExecution(issueId: $issueId) {
        tests(limit: 100) {
          results { jira(fields: ["key", "summary"]) }
        }
      }
    }
    """
    gresp = requests.post(
        GRAPHQL_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"query": gql, "variables": {"issueId": execution["id"]}},
    )
    if not gresp.ok:
        print(f"GraphQL key lookup failed ({gresp.status_code}):")
        print(gresp.text)
        print(f"The Test(s) were created under Test Execution {execution['key']} in Jira, "
              f"but keys could not be auto-recovered — look them up manually and stamp by hand, "
              f"or fix the query and re-run the lookup against issueId={execution['id']} "
              f"(do NOT re-run this script, it would create duplicates).")
        gresp.raise_for_status()

    linked = gresp.json()["data"]["getTestExecution"]["tests"]["results"]
    summary_to_key = {t["jira"]["summary"]: t["jira"]["key"] for t in linked}

    print(f"\n--- Reuse check: {len(linked)} test(s) linked to {execution['key']} ---")
    reused_count = 0
    for t in linked:
        key = t["jira"]["key"]
        summary = t["jira"]["summary"]
        if key in keys_before:
            reused_count += 1
            print(f"  REUSED existing ticket {key} (already existed since {keys_before[key]}) "
                  f"-- now holds: {summary[:70]!r}")
        else:
            print(f"  created FRESH: {key} -- {summary[:70]!r}")
    if reused_count:
        print(f"WARNING: {reused_count}/{len(linked)} test(s) in this run REUSED an existing ticket "
              f"instead of creating a new one. Whatever test used to live at that key has now "
              f"lost its ticket -- check for it and re-onboard it separately.")
    else:
        print("All linked tests were freshly created. No existing tickets were touched.")
    print("--- end reuse check ---\n")

    by_file = {}
    stamped = 0
    for e in unkeyed:
        summary = e["description"] or e["function"]
        new_key = summary_to_key.get(summary)
        if not new_key:
            print(f"WARNING: no key found for '{summary}' — check manually, do not re-run.")
            continue
        by_file.setdefault(e["file"], []).append((e["call_end_lineno"], new_key))
        stamped += 1

    stamp_keys(by_file)
    print(f"Stamped {stamped} new Xray key(s) into {len(by_file)} file(s). "
          f"Commit these changes so CI sees the same keys.")


if __name__ == "__main__":
    main()
