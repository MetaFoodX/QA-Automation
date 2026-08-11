"""One-time backfill: set the "Location in code / Steps" definition text on
every already-onboarded test (created before this format existed). Run LOCALLY
BY A HUMAN, same as xray_onboard.py — never from Jenkins.

Usage:
    python scripts/xray_backfill_definitions.py --dry-run
    python scripts/xray_backfill_definitions.py
"""
import argparse

import requests

from xray_common import GRAPHQL_URL, authenticate, build_definition, extract_tests

UPDATE_MUTATION = """
mutation($issueId: String!, $unstructured: String!) {
  updateUnstructuredTestDefinition(issueId: $issueId, unstructured: $unstructured) {
    issueId
  }
}
"""


def resolve_issue_ids(token, keys):
    """Map Jira key -> internal issueId, in batches of 100 (Xray's JQL page cap)."""
    key_to_issue_id = {}
    keys = list(keys)
    for i in range(0, len(keys), 100):
        chunk = keys[i : i + 100]
        jql = f"key in ({', '.join(chunk)})"
        gql = """
        query($jql: String!) {
          getTests(jql: $jql, limit: 100) {
            results { issueId jira(fields: ["key"]) }
          }
        }
        """
        resp = requests.post(
            GRAPHQL_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"query": gql, "variables": {"jql": jql}},
        )
        resp.raise_for_status()
        for t in resp.json()["data"]["getTests"]["results"]:
            key_to_issue_id[t["jira"]["key"]] = t["issueId"]
    return key_to_issue_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    entries = [e for e in extract_tests() if e["key"]]
    print(f"{len(entries)} already-keyed tests to backfill.")

    if args.dry_run:
        for e in entries[:5]:
            print(f"--- {e['key']} ---")
            print(build_definition(e["file"], e["function"], e["steps"]))
        print("Dry run only — nothing sent to Xray.")
        return

    token = authenticate()
    key_to_issue_id = resolve_issue_ids(token, [e["key"] for e in entries])

    updated, failed = 0, []
    for e in entries:
        issue_id = key_to_issue_id.get(e["key"])
        if not issue_id:
            failed.append(e["key"])
            continue
        definition = build_definition(e["file"], e["function"], e["steps"])
        resp = requests.post(
            GRAPHQL_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"query": UPDATE_MUTATION, "variables": {"issueId": issue_id, "unstructured": definition}},
        )
        if resp.ok:
            updated += 1
        else:
            print(f"WARNING: failed to update {e['key']}: {resp.status_code} {resp.text}")
            failed.append(e["key"])

    print(f"Updated {updated}/{len(entries)} tests.")
    if failed:
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
