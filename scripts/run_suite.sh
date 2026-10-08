#!/usr/bin/env bash
# Runs the two pytest passes (main suite, then the Weekly Service Line Report
# file — kept separate; see the comment in run_pass below for why), retrying
# failures up to twice each via pytest's built-in --last-failed. Produces
# exactly 2 reports total — one per pass — never one extra per retry attempt:
# each pass gets its own Excel+Allure report right after its own retries
# finish, built from that pass's raw dumps (last attempt wins per test). The
# one Xray push happens once at the very end, covering both passes.
#
# No Docker/AWS/Jenkins dependency — this is plain pytest plus a merge step,
# so it runs identically locally and inside the CI container. run_qa.sh is
# the thin Jenkins-specific wrapper around this (secrets, Docker, S3 upload).
#
# Usage: bash scripts/run_suite.sh <env> <base_url> <test_suite>
#   e.g. bash scripts/run_suite.sh staging https://staging-mercato.skoopin.net smoke
set -e

export ENV="${1:-staging}"
export BASE_URL="${2:-https://staging-mercato.skoopin.net}"
export TEST_SUITE="${3:-all}"
MAX_ATTEMPTS=3

MARKER_FLAG=""
if [ "$TEST_SUITE" != "all" ]; then
    MARKER_FLAG="-m $TEST_SUITE"
fi

echo "==> Clearing previous raw results and allure-results (suite: $TEST_SUITE, env: $ENV)"
rm -rf reports/_raw allure-results
mkdir -p reports/_raw

# Runs one pass with up to MAX_ATTEMPTS attempts: attempt 1 is the full
# collection for this pass's args; any attempt after that reruns ONLY what
# failed last time (--last-failed), as a genuinely separate pytest process —
# not an in-process retry — and only happens at all if the previous attempt
# actually had failures (an empty --last-failed cache defaults to rerunning
# everything, so we must never call it after a clean attempt).
run_pass() {
    local label=$1
    shift
    local attempt=1
    local exit_code=0

    while [ $attempt -le $MAX_ATTEMPTS ]; do
        echo "==> [$label] attempt $attempt/$MAX_ATTEMPTS"
        local lf_flag=""
        if [ $attempt -gt 1 ]; then
            lf_flag="--last-failed"
        fi
        set +e
        QA_RUN_LABEL="$label" QA_RUN_ATTEMPT="$attempt" \
            pytest "$@" $lf_flag -s $MARKER_FLAG --alluredir="allure-results/$label"
        exit_code=$?
        set -e
        if [ $exit_code -eq 0 ]; then
            break
        fi
        attempt=$((attempt + 1))
    done

    return $exit_code
}

EXIT1=0
EXIT2=0
PYTHON_BIN=$(command -v python3 || command -v python)

# test_consumption_summary_report.py and test_sustainability_report.py are
# still uncommitted/WIP (test_consumption_summary_report.py doesn't even
# collect yet — missing helpers) — ignored so a collection error there can't
# burn through all retry attempts on something retrying will never fix.
# Remove these two ignores once they're finished and committed.
run_pass summary_cases dashboard/tests/ \
    --ignore=dashboard/tests/test_seed.py \
    --ignore=dashboard/tests/executive_insights/reports/test_weekly_service_line_report.py \
    --ignore=dashboard/tests/executive_insights/reports/test_consumption_summary_report.py \
    --ignore=dashboard/tests/executive_insights/reports/test_sustainability_report.py \
    || EXIT1=$?

echo "==> summary_cases finished (all its retries included) — finalizing its report"
"$PYTHON_BIN" scripts/finalize_report.py --label summary_cases

# Kept as its own pass (not folded into the one above): the Weekly Service
# Line Report file's AI Ranking tests need exact, uncontaminated
# overproduction weights for a fixed set of named menu items — the same pool
# seeded_basic_scans draws from for the whole Consumption/Overproduction
# Summary suite. seeded_basic_scans is session-scoped, so its cleanup only
# fires when its pytest process exits; running this as a separate process
# guarantees that cleanup already happened before AI Ranking's data is read.
run_pass weekly_report_cases \
    dashboard/tests/executive_insights/reports/test_weekly_service_line_report.py \
    || EXIT2=$?

echo "==> weekly_report_cases finished (all its retries included) — finalizing its report"
"$PYTHON_BIN" scripts/finalize_report.py --label weekly_report_cases

echo "==> Both passes done — one Xray push covering both"
"$PYTHON_BIN" scripts/finalize_report.py --xray-only --build "${BUILD_NUMBER:-Local Execution}"

if [ $EXIT1 -ne 0 ]; then exit $EXIT1; fi
exit $EXIT2
