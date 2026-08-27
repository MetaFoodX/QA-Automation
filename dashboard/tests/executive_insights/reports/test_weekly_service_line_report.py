"""Executive Insights > Reports — Weekly Service Line Report type.

This report type only appears in the Report Type dropdown when the restaurant
has a 'WeeklyReport' tracking preference configured (a start date from which
reportable weeks are computed). Test Kitchen has this configured. Format is
always PDF for this report type — there is no CSV path and no Report Format
field is ever shown.

Two kinds of coverage live in this one file, deliberately not split further:
  - Config/download tests (field visibility, week picker, PDF modal, etc.)
  - AI Ranking data tests (the 'Top 5 Menu Items Ranked By AI-Estimated
    Overproduction Cost' page embedded in the PDF for each venue)

The AI Ranking tests seed their own scan data for a fixed set of named menu
items and MUST run in a pytest invocation separate from the rest of
dashboard/tests/ — see run_qa.sh for why (seeded_basic_scans, used by the
Consumption/Overproduction Summary suite, draws from the same menu item pool
and is session-scoped, so its cleanup doesn't fire until its own pytest
process exits).
"""
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from dataclasses import dataclass
from pathlib import Path
from time import sleep as _sleep_seconds  # aliased: `time` above is datetime.time, not the time module
from uuid import uuid4
from zoneinfo import ZoneInfo

import allure
import pdfplumber
import pytest

from shared.config.settings import settings
from shared.data.fixtures import RESTAURANT_A
from shared.data.test_constants import SCAN_TYPE_LEFTOVER_COMPOSTABLE, SCAN_TYPE_REFILL
from dashboard.pages.reports_page import ReportsPage as Page
from dashboard.pages.overproduction_summary_page import OverproductionSummaryPage
from dashboard.tests.executive_insights.reports._helpers import _find_two_items_with_same_cost

WEEK_LABEL_PATTERN = re.compile(r"^Week of (\d{4}-\d{2}-\d{2}) - (\d{4}-\d{2}-\d{2})$")
MAX_WEEKLY_REPORT_WEEKS = 13


def _parse_week_label(label: str) -> tuple[datetime, datetime]:
    match = WEEK_LABEL_PATTERN.match(label)
    assert match, f"Week label '{label}' does not match expected 'Week of YYYY-MM-DD - YYYY-MM-DD' format"
    return datetime.strptime(match.group(1), "%Y-%m-%d"), datetime.strptime(match.group(2), "%Y-%m-%d")


# ---------------------------------------------------------------------------
# Field Visibility
# ---------------------------------------------------------------------------

@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — Form")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Selecting Weekly Service Line Report shows only the Report Start Day and Date (week) fields")
@pytest.mark.testcase(
    component="reports",
    type="smoke, regression",
    description="Weekly Service Line Report hides Venue, Meal Period, Date Mode, Detail Level, Report Format, and See More Options",
    steps=(
        "1. Log in as kitchen_sapna, navigate to Executive Insights > Reports\n"
        "2. Select Report Type = Weekly Service Line Report\n"
        "3. Assert the Report Start Day and Date fields are visible\n"
        "4. Assert Venue, Meal Period, Date Mode, Detail Level, Report Format, and See More Options are all absent"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_weekly_service_line_report_shows_only_start_day_and_date_fields(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    assert page.is_field_visible("Report Start Day")
    assert page.is_field_visible("Date")
    for label in ["Venue", "Meal Period", "Date Mode", "Detail Level", "Report Format", "Category", "Menu Item"]:
        assert not page.is_field_visible(label), f"'{label}' should not be visible for Weekly Service Line Report"
    assert "See More Options" not in page.get_visible_field_labels()
    assert "See Less Options" not in page.get_visible_field_labels()


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — Form")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Report Type dropdown labels it 'Weekly Service Line Report' for a Regular restaurant")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description="For a non-Catering restaurant (Test Kitchen), the dropdown option reads 'Weekly Service Line Report', not 'Weekly Catering Report'",
    steps=(
        "1. Navigate to Reports\n"
        "2. Open the Report Type dropdown\n"
        "3. Assert 'Weekly Service Line Report' is present\n"
        "4. Assert 'Weekly Catering Report' is absent"
    ),
)
@pytest.mark.regression
def test_report_type_label_for_regular_restaurant(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()

    options = page.get_dropdown_options("Report Type")
    assert Page.REPORT_TYPE_WEEKLY_SERVICE_LINE in options
    assert "Weekly Catering Report" not in options


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — Form")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Switching away and back to Weekly Service Line Report restores the week field")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description="After switching to Consumption Summary and back, the Date field is the week-select again (not date-range pickers), and Venue stays hidden",
    steps=(
        "1. Navigate to Reports, select Weekly Service Line Report\n"
        "2. Switch to Consumption Summary\n"
        "3. Switch back to Weekly Service Line Report\n"
        "4. Assert the Date field again offers 'Week of ...' options\n"
        "5. Assert Venue is still hidden"
    ),
)
@pytest.mark.regression
def test_switching_away_and_back_restores_week_field(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    page.set_report_type(Page.REPORT_TYPE_CONSUMPTION_SUMMARY)
    assert page.is_field_visible("Venue")

    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    assert not page.is_field_visible("Venue")
    options = page.get_week_options()
    assert options, "Expected at least one week option after switching back"
    assert all(WEEK_LABEL_PATTERN.match(o) for o in options)


# ---------------------------------------------------------------------------
# Week Selection
# ---------------------------------------------------------------------------

@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — Week Selection")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("A valid week is pre-selected by default")
@pytest.mark.testcase(
    component="reports",
    type="smoke, regression",
    description="Selecting Weekly Service Line Report pre-populates the Date field with the most recent reportable week",
    steps=(
        "1. Navigate to Reports, select Weekly Service Line Report\n"
        "2. Read the selected Date value\n"
        "3. Assert it matches the 'Week of YYYY-MM-DD - YYYY-MM-DD' format"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_default_week_is_preselected(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    selected = page.get_selected_week()
    assert WEEK_LABEL_PATTERN.match(selected), f"Selected week '{selected}' doesn't match expected format"


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — Week Selection")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Week options are capped at 13 and each spans exactly 7 days")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description="No more than MAX_WEEKLY_REPORT_WEEKS (13) options are offered, and each option's start/end are 6 days apart (a full week)",
    steps=(
        "1. Navigate to Reports, select Weekly Service Line Report\n"
        "2. Read all week options\n"
        "3. Assert there are at most 13\n"
        "4. For each, assert end date = start date + 6 days"
    ),
)
@pytest.mark.regression
def test_week_options_span_seven_days_each(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    options = page.get_week_options()
    assert 1 <= len(options) <= MAX_WEEKLY_REPORT_WEEKS, (
        f"Expected 1-{MAX_WEEKLY_REPORT_WEEKS} week options, got {len(options)}"
    )

    failures = []
    for label in options:
        start, end = _parse_week_label(label)
        if (end - start) != timedelta(days=6):
            failures.append(f"'{label}': spans {(end - start).days} days, expected 6")
    assert not failures, "Week options not spanning 7 days:\n  " + "\n  ".join(failures)


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — Week Selection")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Consecutive week options are exactly 7 days apart")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description="Week options are contiguous — each option's start date is exactly 7 days before the previous option's start date",
    steps=(
        "1. Navigate to Reports, select Weekly Service Line Report\n"
        "2. Read all week options (newest first)\n"
        "3. If there are at least 2, assert each consecutive pair's start dates differ by exactly 7 days"
    ),
)
@pytest.mark.regression
def test_week_options_are_contiguous(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    options = page.get_week_options()
    if len(options) < 2:
        pytest.skip("Fewer than 2 weeks available — nothing to compare")

    starts = [_parse_week_label(label)[0] for label in options]
    failures = [
        f"{starts[i]} -> {starts[i + 1]}: {(starts[i] - starts[i + 1]).days} days apart"
        for i in range(len(starts) - 1)
        if (starts[i] - starts[i + 1]) != timedelta(days=7)
    ]
    assert not failures, "Non-contiguous week options:\n  " + "\n  ".join(failures)


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — Week Selection")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Selecting a different week updates the selection")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description="Picking a week other than the default changes the Date field's selected value",
    steps=(
        "1. Navigate to Reports, select Weekly Service Line Report\n"
        "2. Record the default selected week\n"
        "3. If more than one option exists, select the last (oldest) option\n"
        "4. Assert the selected value changed"
    ),
)
@pytest.mark.regression
def test_selecting_a_different_week_updates_selection(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    options = page.get_week_options()
    default_selection = page.get_selected_week()
    if len(options) < 2:
        pytest.skip("Fewer than 2 weeks available — nothing to switch to")

    other_week = next(o for o in options if o != default_selection)
    page.set_week(other_week)

    assert page.get_selected_week() == other_week
    assert page.get_selected_week() != default_selection


@pytest.fixture
def restore_report_start_day(logged_in_page):
    """Records the CURRENT Report Start Day before a test changes it, and
    restores it afterward — even if the test fails. This is a persistent,
    restaurant-wide setting (not per-test data), so it must never be left
    changed. Re-navigates fresh in teardown rather than trusting whatever
    state the test left the page in.
    """
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    original_day = page.get_report_start_day()

    yield original_day

    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    if page.get_report_start_day() != original_day:
        page.set_report_start_day(original_day)


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — Form")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Editing the Report Start Day shifts the Date field's week options accordingly")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "Changing the Report Start Day (e.g. Monday to Tuesday) recomputes the Date field's week "
        "options to start on the new day and span 7 days from there, instead of the previous anchor day"
    ),
    steps=(
        "1. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "2. Note the current Report Start Day and the Date field's week options\n"
        "3. Click Edit next to Report Start Day, pick a DIFFERENT day (e.g. Tuesday instead of Monday), "
        "and Save\n"
        "4. Confirm the Date field's week options now all start on the newly selected day, each still "
        "spanning a full 7 days\n"
        "5. Restore the original Report Start Day"
    ),
)
@pytest.mark.regression
def test_editing_report_start_day_shifts_week_options(logged_in_page, restore_report_start_day):
    original_day = restore_report_start_day
    new_day = "Tuesday" if original_day != "Tuesday" else "Wednesday"

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    before_options = page.get_week_options()
    allure.attach(
        f"Report Start Day: {original_day}\nWeek options before change: {before_options}",
        name="Before changing Report Start Day",
        attachment_type=allure.attachment_type.TEXT,
    )

    page.set_report_start_day(new_day)

    after_options = page.get_week_options()
    allure.attach(
        f"Report Start Day: {new_day}\nWeek options after change: {after_options}",
        name="After changing Report Start Day",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert after_options != before_options, (
        f"Expected week options to change after switching Report Start Day from {original_day} to "
        f"{new_day}, but they're identical: {after_options}"
    )

    mismatched = []
    for label in after_options:
        start, end = _parse_week_label(label)
        if start.strftime("%A") != new_day:
            mismatched.append(f"'{label}' starts on a {start.strftime('%A')}, expected {new_day}")
        if (end - start).days != 6:
            mismatched.append(f"'{label}' spans {(end - start).days + 1} days, expected 7")
    assert not mismatched, "Week options not aligned to the new Report Start Day:\n  " + "\n  ".join(mismatched)


# ---------------------------------------------------------------------------
# PDF Download (format is always PDF — no CSV path exists for this report)
# ---------------------------------------------------------------------------

@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — PDF Download")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Download opens the PDF generation modal directly (no CSV option)")
@pytest.mark.testcase(
    component="reports",
    type="smoke, regression",
    description="Since Report Format is forced to PDF and hidden for this report type, clicking Download always opens the generation modal",
    steps=(
        "1. Navigate to Reports, select Weekly Service Line Report\n"
        "2. Click Download\n"
        "3. Assert the PDF generation modal appears\n"
        "4. Poll until the typewriter text finishes and assert it reads the standard generating message"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_download_opens_pdf_modal_directly(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    page.click_download()
    page.wait_for_pdf_modal()

    # The modal's message types itself out via a typewriter animation, racing
    # against actual report generation — if generation finishes fast, the
    # modal can move on (or the download can complete) before the full
    # string finishes typing. Accept whatever's showing as long as it's a
    # valid prefix of the expected message, not necessarily the complete
    # string, rather than waiting for a state that may never be reached.
    expected_text = "Generating your report(s). This will take a moment."
    actual_text = page.get_pdf_modal_text()
    assert expected_text.startswith(actual_text) and actual_text, (
        f"Expected modal text to be a (possibly partial, mid-typewriter) prefix of "
        f"'{expected_text}', got: '{actual_text}'"
    )


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — PDF Download")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Cancel button on the PDF generation modal closes it")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "Clicking Cancel on the generation modal closes it without leaving the page in a broken state — "
        "the only way out of generation for this report type, since there is no CSV alternative"
    ),
    steps=(
        "1. Navigate to Reports, select Weekly Service Line Report\n"
        "2. Click Download to open the generation modal\n"
        "3. Click Cancel\n"
        "4. Assert the modal is no longer visible\n"
        "5. Assert the Download button is still present and clickable"
    ),
)
@pytest.mark.regression
def test_pdf_modal_cancel_closes_modal(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    page.click_download()
    page.wait_for_pdf_modal()
    page.click_pdf_cancel()

    assert not page.is_pdf_modal_visible()
    assert logged_in_page.get_by_role("button", name="Download").is_visible()


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — PDF Download")
@allure.severity(allure.severity_level.MINOR)
@allure.title("PDF generation completes and downloads a .pdf file named after the selected week")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description="End-to-end PDF generation for the selected week produces a downloadable, correctly named, non-empty file",
    steps=(
        "1. Navigate to Reports, select Weekly Service Line Report\n"
        "2. Record the selected week's start/end dates\n"
        "3. Click Download and wait for the generated PDF\n"
        "4. Assert the filename matches 'Weekly Service Line Report-<start>-<end>.pdf'\n"
        "5. Assert the downloaded file is non-empty"
    ),
)
@pytest.mark.regression
@pytest.mark.slow
def test_pdf_download_completes(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)

    start, end = _parse_week_label(page.get_selected_week())
    download = page.download_pdf()

    expected_name = f"Weekly Service Line Report-{start.date().isoformat()}-{end.date().isoformat()}.pdf"
    assert download.suggested_filename == expected_name
    assert Path(download.path()).stat().st_size > 0


# ---------------------------------------------------------------------------
# AI Ranking — Data (see module docstring: run separately from the rest of
# dashboard/tests/, per run_qa.sh)
# ---------------------------------------------------------------------------

OZ_PER_LB = 16
AI_RANKING_VENUE = "Mexican Venue"
AI_RANKING_WEIGHT_RANGE_LB = (2, 30)
AI_RANKING_TOTAL_SCANS = 200  # same scale as ScanSeeder.DEFAULT_SCAN_COUNT elsewhere in this suite

AI_RANKING_PARTIAL_ITEM_COUNT = 3  # < 5, so A-02 expects all of them shown, not padded to 5
AI_RANKING_PARTIAL_TOTAL_SCANS = 75  # proportionally smaller scan volume for a smaller item pool

# Test Kitchen's configured timezone (confirmed via dashboard Edit Restaurant:
# "(UTC-07:00) Pacific Time (US & Canada)"). Scans must be timestamped at a
# safe point in the *local* day, not naive UTC midnight — midnight UTC is
# 5pm the previous day in Pacific time, which silently shifts a scan meant
# for e.g. Monday onto Sunday and drops it out of a strict Mon-Sun week query.
RESTAURANT_TIMEZONE = ZoneInfo("America/Los_Angeles")

AI_RANKING_SETTLE_TIMEOUT_SECONDS = 300  # give up waiting for Overproduction Summary to match after this long
AI_RANKING_SETTLE_POLL_INTERVAL_SECONDS = 15
AI_RANKING_SETTLE_TOLERANCE_LB = 0.5
AI_RANKING_MAX_GENERATION_SECONDS = 60  # generous ceiling for a full PDF generation + download round trip

AI_RANKING_TITLE = "Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost"
AI_RANKING_DISCLOSURE_START = "How the menu items are ranked by AI"
VENUE_SECTION_HEADER = "Venue Performance Overview"


@dataclass(frozen=True)
class AiRankingMenuItem:
    id: int
    name: str
    category: str


# Each of these 8 has a real, distinct, non-zero CostPerLb set on the
# dashboard as of 2026-08-24. Overproduction weight is never hardcoded —
# seeded_ai_ranking_scans below seeds a random weight per item and the test
# reads it back off the returned payload.
AI_RANKING_ITEMS = [
    AiRankingMenuItem(id=85641, name="One Birthday Protein Bar", category="Fruits"),
    AiRankingMenuItem(id=85572, name="Fresas", category="Fruits"),
    AiRankingMenuItem(id=85536, name="Corn", category="Vegetables"),
    AiRankingMenuItem(id=85756, name="Uvas", category="Fruits"),
    AiRankingMenuItem(id=85735, name="Strawberries", category="Fruits"),
    AiRankingMenuItem(id=85522, name="Cherries", category="Fruits"),
    AiRankingMenuItem(id=85639, name="Nuts", category="Vegetables"),
    AiRankingMenuItem(id=85475, name="Bananas", category="Fruits"),
]


def _target_week_range(today: date | None = None) -> tuple[date, date]:
    """The most recently completed Monday-Sunday week, relative to today.

    Mirrors the app's own week computation (isoWeek-based, see
    weeklyReportDateRange.js:getWeeklyReportWeeks): last week's Monday
    through the Sunday right before this week's Monday.
    """
    today = today or date.today()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    return last_monday, last_sunday


def _target_week_label(today: date | None = None) -> str:
    start, end = _target_week_range(today)
    return f"Week of {start.isoformat()} - {end.isoformat()}"


def _extract_pdf_text(pdf_path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _extract_ai_ranking_section(pdf_path, venue_name: str) -> str:
    """The AI Ranking section's raw text for one venue's page(s) within a
    merged Weekly Service Line Report PDF. Returns '' if the section isn't
    present for that venue (e.g. no overproduction scans that week).

    Deliberately doesn't parse exact rank-badge/table layout — pdfplumber's
    text reconstruction from a Puppeteer-rendered flex/table isn't
    guaranteed to preserve visual order character-for-character. Instead
    get_ranked_item_order locates each known item name's offset within this
    section and sorts by that, which is robust to spacing/layout quirks.
    """
    text = _extract_pdf_text(pdf_path)

    venue_marker = f"— {venue_name}"
    venue_start = text.find(venue_marker)
    if venue_start == -1:
        return ""
    text = text[venue_start:]

    next_venue = text.find(VENUE_SECTION_HEADER, len(venue_marker))
    if next_venue != -1:
        text = text[:next_venue]

    title_start = text.find(AI_RANKING_TITLE)
    if title_start == -1:
        return ""

    disclosure_start = text.find(AI_RANKING_DISCLOSURE_START, title_start)
    return text[title_start:disclosure_start] if disclosure_start != -1 else text[title_start:]


def _get_ranked_item_order(section_text: str, candidate_items: list[str]) -> list[str]:
    """Of the given candidate item names, return those present in the
    section, ordered by first-appearance offset (i.e. rendered rank order).
    """
    positions = []
    for name in candidate_items:
        pos = section_text.find(name)
        if pos != -1:
            positions.append((pos, name))
    positions.sort(key=lambda p: p[0])
    return [name for _, name in positions]


# Matches a per-day overproduction row, e.g. "Mon 8/17 163 lb / 8 pans".
# Days with zero overproduction render as "N/A" instead (formatWithPan in
# single-venue.html), so those simply produce no match — treated as 0 lb.
DAILY_ROW_PATTERN = re.compile(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d{1,2})/(\d{1,2}) ([\d,]+(?:\.\d+)?) lb")


def _extract_item_daily_overproduction(
    section_text: str, item_name: str, other_item_names: list[str], year: int
) -> dict:
    """Per-day overproduction (lb) for one item's block within the AI Ranking
    section, keyed by date. Slices from this item's rank header to whichever
    comes first: the next listed item's header, or the end of the section.
    """
    start = section_text.find(item_name)
    if start == -1:
        return {}

    end = len(section_text)
    for other in other_item_names:
        if other == item_name:
            continue
        pos = section_text.find(other, start + len(item_name))
        if pos != -1:
            end = min(end, pos)
    block = section_text[start:end]

    daily = {}
    for month, day, lb in DAILY_ROW_PATTERN.findall(block):
        daily[date(year, int(month), int(day))] = float(lb.replace(",", ""))
    return daily


# Overproduction and each consumption-cycle field independently render as
# either literal "N/A" (zero/no data) or "<number> lb / <n> pan(s)" -- e.g.
# "Mon 8/17 26 lb / 1 pan N/A -> N/A -" (no consumption at all that day) or
# "Wed 8/19 N/A N/A -> 25 lb / 1 pan -" (consumption but zero overproduction).
# Confirmed against a real generated PDF showing an actual nonzero
# consumption value -- a bare number like "45 -> 60" never actually occurs.
_QTY_OR_NA = r"N/A|[\d,]+(?:\.\d+)? lb / \d+ pans?"

DAILY_ROW_WITH_CONSUMPTION_PATTERN = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d{1,2})/(\d{1,2}) "
    rf"(?:{_QTY_OR_NA}) "
    rf"({_QTY_OR_NA}) → ({_QTY_OR_NA})"
)


def _parse_qty_or_na(raw: str) -> float | None:
    """'N/A' -> None, '<number> lb / <n> pan(s)' -> the leading number."""
    if raw == "N/A":
        return None
    return float(raw.split(" lb", 1)[0].replace(",", ""))


def _extract_item_daily_consumption_cycles(
    section_text: str, item_name: str, other_item_names: list[str], year: int
) -> dict:
    """Per-day (consumption_last_cycle, consumption_this_cycle) for one
    item's block, keyed by date — 'N/A' becomes None (no data for that
    cycle), a real value becomes a float lb amount.
    """
    start = section_text.find(item_name)
    if start == -1:
        return {}

    end = len(section_text)
    for other in other_item_names:
        if other == item_name:
            continue
        pos = section_text.find(other, start + len(item_name))
        if pos != -1:
            end = min(end, pos)
    block = section_text[start:end]

    daily = {}
    for month, day, last_cycle, this_cycle in DAILY_ROW_WITH_CONSUMPTION_PATTERN.findall(block):
        daily[date(year, int(month), int(day))] = (
            _parse_qty_or_na(last_cycle),
            _parse_qty_or_na(this_cycle),
        )
    return daily


def _local_date_of_captured_at(captured_at: str) -> date:
    """The restaurant-local calendar date a UTC CapturedAt timestamp falls on."""
    utc_dt = datetime.strptime(captured_at, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=ZoneInfo("UTC"))
    return utc_dt.astimezone(RESTAURANT_TIMEZONE).date()


def _assert_daily_breakdown_matches(
    section: str, target_item: str, other_item_names: list[str], seeded_scans: list[dict], year: int
) -> dict:
    """Shared day-by-day check, reused by every AI Ranking test below: sums
    the actual seeded weight per local calendar day for target_item, extracts
    the PDF's per-day rows for that same item, attaches the comparison to
    Allure, and asserts they match within a 0.5 lb tolerance. Returns the
    PDF's extracted per-day dict (e.g. for callers that also check day count).
    """
    expected_daily = {}
    for scan in seeded_scans:
        if scan["MenuItemName"] != target_item:
            continue
        scan_date = _local_date_of_captured_at(scan["CapturedAt"])
        expected_daily[scan_date] = expected_daily.get(scan_date, 0) + scan["Weight"] / OZ_PER_LB

    actual_daily = _extract_item_daily_overproduction(section, target_item, other_item_names, year)

    all_days = sorted(set(expected_daily) | set(actual_daily))
    daily_table = "\n".join(
        f"{d}: expected {expected_daily.get(d, 0):.2f} lb, PDF shows {actual_daily.get(d, 0):.2f} lb"
        for d in all_days
    )
    allure.attach(
        daily_table,
        name=f"Day-by-day overproduction check — {target_item}",
        attachment_type=allure.attachment_type.TEXT,
    )

    daily_failures = [
        f"{d}: expected {expected_daily.get(d, 0):.2f} lb, PDF shows {actual_daily.get(d, 0):.2f} lb"
        for d in all_days
        if abs(expected_daily.get(d, 0) - actual_daily.get(d, 0)) > 0.5
    ]
    assert not daily_failures, (
        f"Day-by-day overproduction mismatch for '{target_item}':\n  " + "\n  ".join(daily_failures)
    )
    return actual_daily


def _seed_ai_ranking_scans(scan_client, item_pool: list[AiRankingMenuItem], total_scans: int) -> list[dict]:
    """Seed total_scans pure-overproduction scans at Mexican Venue, spread
    across the current target week — same shape as
    ScanSeeder.generate_scans/seed_concurrent elsewhere in this suite: each
    scan independently picks a random item from item_pool and a random
    weight, inserted concurrently. 'Pure overproduction' means every scan is
    Type=2 (ServedLeftover/Compostable) with no matching Refill, so
    Consumption=0 and Overproduction=the full seeded weight.

    Shared by every AI Ranking fixture below — only item_pool/total_scans
    differ per test case (e.g. all 8 items for the top-5 test, a smaller
    subset for the fewer-than-5 test).
    """
    venue = RESTAURANT_A.venues["v_a1"]  # Mexican Venue
    station = RESTAURANT_A.stations["s_a1"]
    service_period = RESTAURANT_A.service_periods["all_day"]
    week_start, _ = _target_week_range()

    def build_scan(index: int) -> dict:
        item = random.choice(item_pool)
        weight_lb = random.randint(*AI_RANKING_WEIGHT_RANGE_LB)

        # Noon in the restaurant's own local timezone, converted to UTC —
        # safely mid-day so it can never cross into an adjacent local
        # calendar date, unlike naive UTC midnight.
        local_day = week_start + timedelta(days=index % 7)
        local_noon = datetime.combine(local_day, time(12, 0), tzinfo=RESTAURANT_TIMEZONE)
        captured_at = local_noon.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        return {
            "ID": str(uuid4()),
            "RestaurantID": RESTAURANT_A.id,
            "StationID": station.id,
            "VenueID": venue.id,
            "ServicePeriodID": service_period.id,
            "MenuItemID": item.id,
            "MenuItemName": item.name,
            "Weight": weight_lb * OZ_PER_LB,
            "WeightUnit": "oz",
            "ImageBase64": "data:image/jpeg;base64,/9j/111",
            "DepthArray": [[12, 2, 1], [2, 3, 4]],
            "ImageType": "jpg",
            "Type": SCAN_TYPE_LEFTOVER_COMPOSTABLE,
            "CapturedAt": captured_at,
            "WithPreSignedURL": False,
        }

    scans = [build_scan(i) for i in range(total_scans)]

    inserted = []
    lock = threading.Lock()

    def insert(scan):
        try:
            scan_client.insert_scan(scan)
            with lock:
                inserted.append(scan)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(insert, scans)

    print(f"[seed_ai_ranking_scans] Inserted {len(inserted)}/{total_scans} scans")
    return inserted


def _seed_exact_scans(scan_client, item_weights: dict) -> list[dict]:
    """Seed exactly one scan per item, each with a precisely specified
    overproduction weight (lb) — used only by tests that need an exact,
    non-random total to construct a deliberate tie (D-01, D-04), unlike
    _seed_ai_ranking_scans' random per-scan weights. All land on the target
    week's Monday at local noon — only the weekly total matters here, not
    day-by-day distribution.
    """
    venue = RESTAURANT_A.venues["v_a1"]
    station = RESTAURANT_A.stations["s_a1"]
    service_period = RESTAURANT_A.service_periods["all_day"]
    week_start, _ = _target_week_range()
    local_noon = datetime.combine(week_start, time(12, 0), tzinfo=RESTAURANT_TIMEZONE)
    captured_at = local_noon.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    scans = [
        {
            "ID": str(uuid4()),
            "RestaurantID": RESTAURANT_A.id,
            "StationID": station.id,
            "VenueID": venue.id,
            "ServicePeriodID": service_period.id,
            "MenuItemID": item.id,
            "MenuItemName": item.name,
            "Weight": weight_lb * OZ_PER_LB,
            "WeightUnit": "oz",
            "ImageBase64": "data:image/jpeg;base64,/9j/111",
            "DepthArray": [[12, 2, 1], [2, 3, 4]],
            "ImageType": "jpg",
            "Type": SCAN_TYPE_LEFTOVER_COMPOSTABLE,
            "CapturedAt": captured_at,
            "WithPreSignedURL": False,
        }
        for item, weight_lb in item_weights.items()
    ]

    inserted = []
    lock = threading.Lock()

    def insert(scan):
        try:
            scan_client.insert_scan(scan)
            with lock:
                inserted.append(scan)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(insert, scans)

    print(f"[seed_exact_scans] Inserted {len(inserted)}/{len(scans)} scans")
    return inserted


def _delete_ai_ranking_scans(scan_client, scans: list[dict]) -> None:
    deleted = []
    failed = []
    lock = threading.Lock()

    def delete(scan):
        try:
            scan_client.delete_scan(scan["ID"])
            with lock:
                deleted.append(scan["ID"])
        except Exception as e:
            with lock:
                failed.append((scan["ID"], str(e)))

    print(f"[delete] Deleting {len(scans)} scan(s) ...")
    with ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(delete, scans)

    print(f"[delete] {len(deleted)}/{len(scans)} DELETE call(s) succeeded, {len(failed)} failed")
    for scan_id, error in failed:
        print(f"[delete] FAILED {scan_id}: {error}")


def _expected_lb_by_item(scans: list[dict]) -> dict[str, float]:
    """Sum seeded weight (lb) per item name from a list of scan payloads —
    works for both _seed_ai_ranking_scans' and _seed_exact_scans' output."""
    totals: dict[str, float] = {}
    for scan in scans:
        name = scan["MenuItemName"]
        totals[name] = totals.get(name, 0) + scan["Weight"] / OZ_PER_LB
    return totals


def _wait_for_overproduction_summary_to_match(browser, storage_state: str, scans: list[dict]) -> None:
    """Called from inside a seeding fixture, right after seeding, before
    yield — not from a test. Opens its own throwaway logged-in context (the
    fixture runs before any test's own logged_in_page exists) and polls
    Overproduction Summary — a separate, already-trusted report — until
    every seeded item's Total Overproduction matches what was just seeded,
    within tolerance. insert_scan returning success does not mean the data
    is immediately reflected in any report; this confirms the backend has
    actually caught up before any test in this module runs. Gives up after
    AI_RANKING_SETTLE_TIMEOUT_SECONDS and raises with the last mismatch.
    """
    expected_lb = _expected_lb_by_item(scans)

    ctx = browser.new_context(storage_state=storage_state)
    page = ctx.new_page()
    page.set_default_navigation_timeout(settings.timeouts.navigation)
    page.set_default_timeout(settings.timeouts.default)
    page.goto(settings.base_url)
    try:
        op_page = OverproductionSummaryPage(page)
        week_start, week_end = _target_week_range()

        deadline = datetime.now() + timedelta(seconds=AI_RANKING_SETTLE_TIMEOUT_SECONDS)
        mismatches: dict[str, tuple[float, float]] = {}

        while datetime.now() < deadline:
            op_page.open_via_nav()
            op_page.set_venue(AI_RANKING_VENUE)
            op_page.set_date_range(week_start.strftime("%m/%d/%Y"), week_end.strftime("%m/%d/%Y"))

            actual_lb = {}
            for row in op_page.get_all_rows():
                name = row.get(OverproductionSummaryPage.COL_MENU_ITEM, "")
                raw = row.get(OverproductionSummaryPage.COL_TOTAL_OVERPRODUCTION, "0")
                actual_lb[name] = float(raw.replace(",", "").strip() or 0)

            mismatches = {
                name: (expected, actual_lb.get(name, 0.0))
                for name, expected in expected_lb.items()
                if abs(actual_lb.get(name, 0.0) - expected) > AI_RANKING_SETTLE_TOLERANCE_LB
            }
            if not mismatches:
                return

            _sleep_seconds(AI_RANKING_SETTLE_POLL_INTERVAL_SECONDS)
    finally:
        ctx.close()

    mismatch_text = "\n".join(
        f"{name}: expected {expected:.2f} lb, Overproduction Summary shows {actual:.2f} lb"
        for name, (expected, actual) in mismatches.items()
    )
    raise TimeoutError(
        f"Overproduction Summary did not settle to match seeded data within "
        f"{AI_RANKING_SETTLE_TIMEOUT_SECONDS}s:\n{mismatch_text}"
    )


def _wait_for_overproduction_summary_to_clear(browser, storage_state: str, scans: list[dict]) -> None:
    """Called from inside a seeding fixture's teardown, right after delete,
    before the next seeding fixture is allowed to start. Polls Overproduction
    Summary until every deleted item's Total Overproduction has dropped back
    to ~0 — delete_scan returning success does not mean the removal is
    immediately reflected in any report, the same lag seen on inserts. Gives
    up after AI_RANKING_SETTLE_TIMEOUT_SECONDS and raises with what's left.
    """
    deleted_items = {scan["MenuItemName"] for scan in scans}
    print(f"[clear-check] Waiting for Overproduction Summary to drop {sorted(deleted_items)} to ~0 "
          f"(timeout {AI_RANKING_SETTLE_TIMEOUT_SECONDS}s) ...")

    ctx = browser.new_context(storage_state=storage_state)
    page = ctx.new_page()
    page.set_default_navigation_timeout(settings.timeouts.navigation)
    page.set_default_timeout(settings.timeouts.default)
    page.goto(settings.base_url)
    try:
        op_page = OverproductionSummaryPage(page)
        week_start, week_end = _target_week_range()

        deadline = datetime.now() + timedelta(seconds=AI_RANKING_SETTLE_TIMEOUT_SECONDS)
        leftovers: dict[str, float] = {}
        attempt = 0

        while datetime.now() < deadline:
            attempt += 1
            op_page.open_via_nav()
            op_page.set_venue(AI_RANKING_VENUE)
            op_page.set_date_range(week_start.strftime("%m/%d/%Y"), week_end.strftime("%m/%d/%Y"))

            actual_lb = {}
            for row in op_page.get_all_rows():
                name = row.get(OverproductionSummaryPage.COL_MENU_ITEM, "")
                raw = row.get(OverproductionSummaryPage.COL_TOTAL_OVERPRODUCTION, "0")
                actual_lb[name] = float(raw.replace(",", "").strip() or 0)

            leftovers = {
                name: actual_lb[name]
                for name in deleted_items
                if actual_lb.get(name, 0.0) > AI_RANKING_SETTLE_TOLERANCE_LB
            }
            if not leftovers:
                print(f"[clear-check] attempt {attempt}: cleared, all {len(deleted_items)} item(s) at ~0")
                return

            remaining = (deadline - datetime.now()).total_seconds()
            leftover_summary = ", ".join(f"{name}={lb:.1f}lb" for name, lb in leftovers.items())
            print(f"[clear-check] attempt {attempt}: {len(leftovers)}/{len(deleted_items)} still nonzero "
                  f"({leftover_summary}), ~{remaining:.0f}s left — retrying in "
                  f"{AI_RANKING_SETTLE_POLL_INTERVAL_SECONDS}s")
            _sleep_seconds(AI_RANKING_SETTLE_POLL_INTERVAL_SECONDS)
    finally:
        ctx.close()

    leftover_text = "\n".join(f"{name}: still shows {lb:.2f} lb" for name, lb in leftovers.items())
    raise TimeoutError(
        f"Overproduction Summary did not clear deleted scans within "
        f"{AI_RANKING_SETTLE_TIMEOUT_SECONDS}s:\n{leftover_text}"
    )



_shared_batch_cache: dict[str, tuple] = {}
_shared_batch_counters: dict[str, int] = {}


def _get_shared_batch(request, key, seed_fn, scan_client, browser, storage_state):
    total_in_session = sum(1 for item in request.session.items if key in item.fixturenames)

    if key not in _shared_batch_cache:
        inserted, payload = seed_fn()
        try:
            _wait_for_overproduction_summary_to_match(browser, storage_state, inserted)
        except Exception:
            # Don't leave freshly-seeded data orphaned just because the
            # settle-check itself failed — the code after `yield` below would
            # otherwise never run, since we never reach it.
            _delete_ai_ranking_scans(scan_client, inserted)
            raise
        _shared_batch_cache[key] = (inserted, payload)
        _shared_batch_counters[key] = 0

    inserted, payload = _shared_batch_cache[key]
    yield payload

    _shared_batch_counters[key] += 1
    if _shared_batch_counters[key] >= total_in_session:
        _delete_ai_ranking_scans(scan_client, inserted)
        _wait_for_overproduction_summary_to_clear(browser, storage_state, inserted)
        del _shared_batch_cache[key]
        del _shared_batch_counters[key]


@pytest.fixture
def seeded_ai_ranking_scans(request, scan_client, browser, kitchen_sapna_storage_state):
    """All 8 known items in play — enough that the report must actually
    choose a top 5 out of a larger pool (see A-01). Nothing is hardcoded —
    the test sums the actual inserted weights per item off the returned
    payload rather than assuming fixed totals.

    Seeded once, shared by every test in this session that reads (never
    mutates) this same pool — see _get_shared_batch for why this isn't a
    plain scope="module" fixture.
    """
    def seed():
        inserted = _seed_ai_ranking_scans(scan_client, AI_RANKING_ITEMS, AI_RANKING_TOTAL_SCANS)
        return inserted, inserted

    yield from _get_shared_batch(
        request, "seeded_ai_ranking_scans", seed, scan_client, browser, kitchen_sapna_storage_state
    )


@pytest.fixture
def seeded_ai_ranking_scans_partial(request, scan_client, browser, kitchen_sapna_storage_state):
    """Only AI_RANKING_PARTIAL_ITEM_COUNT (<5) of the 8 known items get any
    overproduction this week — precondition for A-02: with fewer than 5
    qualifying items, the AI Ranking section should show exactly those
    items, not pad the list to a fixed 5.

    Seeded once, shared by every test in this session that reads this same
    pool — see _get_shared_batch for why this isn't a plain scope="module"
    fixture.
    """
    def seed():
        chosen_items = random.sample(AI_RANKING_ITEMS, AI_RANKING_PARTIAL_ITEM_COUNT)
        inserted = _seed_ai_ranking_scans(scan_client, chosen_items, AI_RANKING_PARTIAL_TOTAL_SCANS)
        return inserted, (inserted, chosen_items)

    yield from _get_shared_batch(
        request, "seeded_ai_ranking_scans_partial", seed, scan_client, browser, kitchen_sapna_storage_state
    )


@pytest.fixture
def seed_scans(request, scan_client, browser, kitchen_sapna_storage_state):
    """Factory fixture — yields a function tests call with their own list of
    (item, weight_lb, day_offset, scan_type) tuples, instead of every
    scenario needing its own bespoke named fixture. Builds and inserts
    exactly those scans, waits for the overproduction-type ones to be
    reflected in Overproduction Summary before returning, and automatically
    deletes + waits for clearing on teardown for whatever was inserted
    across any number of calls in the test.

    day_offset is 0-6 (Monday-Sunday) within the current target week.
    """
    venue = RESTAURANT_A.venues["v_a1"]
    station = RESTAURANT_A.stations["s_a1"]
    service_period = RESTAURANT_A.service_periods["all_day"]
    week_start, _ = _target_week_range()
    all_inserted = []

    def build(item, weight_lb, day_offset, scan_type):
        local_day = week_start + timedelta(days=day_offset)
        local_noon = datetime.combine(local_day, time(12, 0), tzinfo=RESTAURANT_TIMEZONE)
        captured_at = local_noon.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return {
            "ID": str(uuid4()),
            "RestaurantID": RESTAURANT_A.id,
            "StationID": station.id,
            "VenueID": venue.id,
            "ServicePeriodID": service_period.id,
            "MenuItemID": item.id,
            "MenuItemName": item.name,
            "Weight": weight_lb * OZ_PER_LB,
            "WeightUnit": "oz",
            "ImageBase64": "data:image/jpeg;base64,/9j/111",
            "DepthArray": [[12, 2, 1], [2, 3, 4]],
            "ImageType": "jpg",
            "Type": scan_type,
            "CapturedAt": captured_at,
            "WithPreSignedURL": False,
        }

    def seed(scan_specs):
        scans = [build(*spec) for spec in scan_specs]
        inserted = []
        lock = threading.Lock()

        def insert(scan):
            try:
                scan_client.insert_scan(scan)
                with lock:
                    inserted.append(scan)
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(insert, scans)
        print(f"[seed_scans] Inserted {len(inserted)}/{len(scans)} scans")

        overproduction_only = [s for s in inserted if s["Type"] != SCAN_TYPE_REFILL]
        try:
            if overproduction_only:
                _wait_for_overproduction_summary_to_match(browser, kitchen_sapna_storage_state, overproduction_only)
        except Exception:
            _delete_ai_ranking_scans(scan_client, inserted)
            raise

        all_inserted.extend(inserted)
        return inserted

    yield seed

    # TEMP: cleanup disabled for test_consumption_last_cycle_vs_this_cycle_per_day (A-05) for manual
    # dashboard inspection of a suspected FX-4827-style last-cycle-consumption mapping issue
    if all_inserted and request.node.name != "test_consumption_last_cycle_vs_this_cycle_per_day":
        overproduction_only = [s for s in all_inserted if s["Type"] != SCAN_TYPE_REFILL]
        _delete_ai_ranking_scans(scan_client, all_inserted)
        if overproduction_only:
            _wait_for_overproduction_summary_to_clear(browser, kitchen_sapna_storage_state, overproduction_only)


@pytest.fixture
def update_menu_item_cost(menu_item_client):
    """Factory fixture — yields a function tests call with (item, new_cost)
    to update a menu item's live CostPerLb via API. Automatically restores
    every changed item's ORIGINAL cost on teardown, even if the test fails
    — this mutates real, persistent dashboard data, not a per-test scan row,
    so it must never be left changed.
    """
    original_costs = {}

    def update(item, new_cost):
        if item.id not in original_costs:
            original_costs[item.id] = menu_item_client.get_cost_per_lb(item.name, restaurant_id=RESTAURANT_A.id)
        menu_item_client.update_cost_per_lb(item.id, new_cost)

    yield update

    for item_id, original_cost in original_costs.items():
        try:
            menu_item_client.update_cost_per_lb(item_id, original_cost)
            print(f"[update_menu_item_cost] Restored item {item_id} to CostPerLb={original_cost}")
        except Exception as e:
            print(f"[update_menu_item_cost] FAILED to restore item {item_id} to {original_cost}: {e}")


def _find_two_items_with_distinct_costs(menu_item_client, items: list[AiRankingMenuItem]):
    """First pair (by list order) of items in `items` with different live
    CostPerLb values, plus both costs. Returns None if every item in the
    pool currently shares the same cost (practically never, with 8 items).

    This is what makes the weight-forced score tie below possible: rather
    than updating either item's CostPerLb (see MenuItemClient.update_cost_
    per_lb, used by C-02), distinct costs are read live as-is and only the
    *weight* is set — keeps this test independent of that mutation path.
    """
    costs = {
        item.name: menu_item_client.get_cost_per_lb(item.name, restaurant_id=RESTAURANT_A.id)
        for item in items
    }
    for i, item_a in enumerate(items):
        for item_b in items[i + 1:]:
            if costs[item_a.name] != costs[item_b.name]:
                return item_a, item_b, costs[item_a.name], costs[item_b.name]
    return None


@pytest.fixture
def seeded_tie_break_scores(scan_client, menu_item_client, browser, kitchen_sapna_storage_state):
    """Two items engineered to land on an IDENTICAL score (weight x cost)
    while differing in both weight and cost individually — precondition for
    D-01. Cost is read live, not updated (see MenuItemClient.update_cost_
    per_lb for the mutation path C-02 uses instead): giving item A the
    weight equal to item B's cost (and vice versa) forces weight*cost to
    match exactly for both (cost_a*cost_b == cost_b*cost_a), guaranteeing
    the tie for any pair with distinct costs.
    """
    found = _find_two_items_with_distinct_costs(menu_item_client, AI_RANKING_ITEMS)
    if found is None:
        pytest.skip("Every item in the pool currently shares the same CostPerLb — can't build a distinct-cost tie")
    item_a, item_b, cost_a, cost_b = found

    weight_a, weight_b = cost_b, cost_a
    inserted = _seed_exact_scans(scan_client, {item_a: weight_a, item_b: weight_b})
    try:
        _wait_for_overproduction_summary_to_match(browser, kitchen_sapna_storage_state, inserted)
    except Exception:
        _delete_ai_ranking_scans(scan_client, inserted)
        raise
    higher_cost_item, lower_cost_item = (item_a, item_b) if cost_a > cost_b else (item_b, item_a)
    yield inserted, higher_cost_item, lower_cost_item, cost_a, cost_b, weight_a, weight_b
    _delete_ai_ranking_scans(scan_client, inserted)
    _wait_for_overproduction_summary_to_clear(browser, kitchen_sapna_storage_state, inserted)


@pytest.fixture
def seeded_boundary_tie_pair(scan_client, menu_item_client, browser, kitchen_sapna_storage_state):
    """Two items that currently share the exact same live CostPerLb, seeded
    with an identical weight too — a genuine same-cost-AND-same-weight tie
    (per D-04's spec), not just a tied score via different combos like D-01
    — placed right at the rank 5/6 boundary via 4 higher-scoring filler
    items. Ranks 1-4 go to the fillers (each deliberately weighted to
    comfortably out-score the tied pair regardless of its own cost); the
    tied pair then competes for the single remaining (5th) slot. Skips if
    no two items in the pool currently share a cost, to keep this test
    independent of MenuItemClient.update_cost_per_lb (see C-02) rather
    than forcing the match via that mutation path.
    """
    found = _find_two_items_with_same_cost(menu_item_client, AI_RANKING_ITEMS)
    if found is None:
        pytest.skip("No two items in the pool currently share the same CostPerLb — can't build a same-cost-and-weight tie")
    item_a, item_b, shared_cost = found

    shared_weight = random.randint(*AI_RANKING_WEIGHT_RANGE_LB)
    tied_score = shared_weight * shared_cost

    fillers = [item for item in AI_RANKING_ITEMS if item.name not in (item_a.name, item_b.name)][:4]
    filler_costs = {
        item.name: menu_item_client.get_cost_per_lb(item.name, restaurant_id=RESTAURANT_A.id)
        for item in fillers
    }

    item_weights = {item_a: shared_weight, item_b: shared_weight}
    for filler in fillers:
        item_weights[filler] = (tied_score * 2) / filler_costs[filler.name]

    inserted = _seed_exact_scans(scan_client, item_weights)
    try:
        _wait_for_overproduction_summary_to_match(browser, kitchen_sapna_storage_state, inserted)
    except Exception:
        _delete_ai_ranking_scans(scan_client, inserted)
        raise
    yield inserted, item_a, item_b, [f.name for f in fillers]
    _delete_ai_ranking_scans(scan_client, inserted)
    _wait_for_overproduction_summary_to_clear(browser, kitchen_sapna_storage_state, inserted)


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("No overproduction this week means the AI Ranking section is not generated at all")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When a venue has zero overproduction scans for the report week, the AI Ranking "
        "('Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost') section must not "
        "appear anywhere in that venue's pages of the PDF — not even an empty shell. Relies on "
        "the target week naturally being at zero for Mexican Venue: every other AI Ranking test "
        "in this file cleans up its own seeded scans before the next test runs, and Test Kitchen "
        "has no real ambient activity of its own."
    ),
    steps=(
        "1. For a given venue and week, make sure there are zero overproduction scans recorded at all\n"
        "2. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "3. Select that same week, click Download, and open the generated PDF\n"
        "4. Confirm the 'Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost' heading does "
        "not appear anywhere in that venue's section of the PDF"
    ),
)
@pytest.mark.regression
def test_no_overproduction_hides_ai_ranking_section(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert not section, (
        f"Expected no AI Ranking section for {AI_RANKING_VENUE} with zero overproduction this week, "
        f"but found one:\n{section[:500]}"
    )


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("No overproduction and no consumption at all means the venue's page stays empty")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When a venue has zero scans of any kind (no overproduction, no consumption) for the "
        "report week, its entire page in the PDF shows the 'no data available' fallback state — "
        "not a populated overview with charts/tables and an empty AI Ranking section underneath. "
        "Broader than A-03: this checks the whole-page fallback template, not just the AI Ranking "
        "sub-section's own skip condition."
    ),
    steps=(
        "1. For a given venue and week, make sure there are zero scans of any kind recorded — "
        "no overproduction and no consumption\n"
        "2. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "3. Select that same week, click Download, and open the generated PDF\n"
        "4. Confirm that venue's page shows 'No scan data available for this venue from the past "
        "week' (0/7 Days with data) instead of populated charts/tables\n"
        "5. Confirm the 'Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost' section is "
        "also absent from that page"
    ),
)
@pytest.mark.regression
def test_no_data_at_all_shows_empty_state(logged_in_page):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    text = _extract_pdf_text(download.path())

    venue_marker = f"— {AI_RANKING_VENUE}"
    venue_start = text.find(venue_marker)
    assert venue_start != -1, f"'{AI_RANKING_VENUE}' section not found in the PDF at all"

    next_venue = text.find(VENUE_SECTION_HEADER, venue_start + len(venue_marker))
    venue_text = text[venue_start:next_venue] if next_venue != -1 else text[venue_start:]

    assert "No scan data available" in venue_text, (
        f"Expected the no-data fallback message for {AI_RANKING_VENUE} with zero scans this week, "
        f"got:\n{venue_text[:500]}"
    )
    assert "0/7 Days with data" in venue_text, (
        f"Expected '0/7 Days with data' for {AI_RANKING_VENUE}, got:\n{venue_text[:500]}"
    )
    assert AI_RANKING_TITLE not in venue_text, (
        f"AI Ranking section should not appear on an empty-state page, but found it:\n{venue_text[:500]}"
    )


# ---------------------------------------------------------------------------
# D-03  Formula: Cost Impact = CostPerLb x lbs. Per the OG plan's own note,
#       this can't be verified directly — the app never logs/persists a
#       "Cost Impact" value anywhere (DB or API); only the resulting rank
#       order is observable. Documented as a skip, same convention as C-03
#       above, rather than silently having no record of it at all.
# ---------------------------------------------------------------------------


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("Cost impact used for ranking equals CostPerLb x total overproduction lb")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description="Each item's cost-impact score backing its rank should equal CostPerLb x total overproduction lb",
    steps=(
        "1. For a ranked item, note its Total Overproduction (lb) and its Cost Per Lb from Menu Items management\n"
        "2. Manually compute Cost Impact = Cost Per Lb x Total Overproduction (lb)\n"
        "3. This testcase can't be tested directly because the app does not log or expose a 'Cost Impact' "
        "value anywhere (not in the database, not in any API response) — only the resulting rank ORDER is "
        "observable, never the underlying score itself\n"
        "4. Coverage of this formula is instead achieved indirectly: A-01 and D-01 independently compute "
        "score = lb x CostPerLb from live data and confirm the PDF's rank order matches that computation, "
        "and C-03 confirms a cost change produces an observable rank change"
    ),
)
@pytest.mark.skip(
    reason="Cost impact is never persisted or exposed anywhere observable (DB or API) — only the resulting "
    "rank order can be checked, which is already covered indirectly by A-01/D-01/C-03"
)
def test_cost_impact_formula():
    pass


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Top 5 items are ranked by cost impact (overproduction lb x CostPerLb), not cost alone")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "The AI Ranking section's top-5 order matches overproduction_lb x CostPerLb, computed "
        "from the actual seeded scan weights and live-fetched CostPerLb values — independent of "
        "the report under test — and the top-ranked item's day-by-day breakdown matches the "
        "actual seeded per-day weights"
    ),
    steps=(
        "1. In Menu Items management, ensure at least 6-8 menu items each have a distinct, known Cost Per Lb\n"
        "2. Using the scanning device, record several overproduction (leftover) scans across the week for "
        "each of those items, so every item ends up with a different total overproduction weight for the week\n"
        "3. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "4. Select the week that was just scanned, click Download, and open the generated PDF\n"
        "5. In the venue's 'Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost' section, for each "
        "item manually compute Total Overproduction (lb) x Cost Per Lb\n"
        "6. Sort those values descending and confirm the top 5 items shown in the PDF match this order exactly "
        "(a higher-cost, lower-weight item should be able to outrank a higher-weight, lower-cost item)\n"
        "7. For the #1 ranked item, compare its day-by-day overproduction shown in the PDF's table against "
        "the actual scanned weight recorded for each corresponding day"
    ),
)
@pytest.mark.regression
def test_top5_ranked_by_cost_impact(logged_in_page, menu_item_client, seeded_ai_ranking_scans):
    # --- Ground truth #1: the weight we ourselves just seeded, summed per
    # item (200 scans land on only 8 items, so most items get several) ---
    overproduction_lb = {}
    for scan in seeded_ai_ranking_scans:
        name = scan["MenuItemName"]
        overproduction_lb[name] = overproduction_lb.get(name, 0) + scan["Weight"] / OZ_PER_LB

    # --- Ground truth #2: live CostPerLb per item (mutable, dashboard-set — not seeded) ---
    costs = {
        item.name: menu_item_client.get_cost_per_lb(item.name, restaurant_id=RESTAURANT_A.id)
        for item in AI_RANKING_ITEMS
    }

    scores = {name: lb * costs[name] for name, lb in overproduction_lb.items()}
    ranked_by_score = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    expected_order = [name for name, _ in ranked_by_score][:5]

    score_table = "\n".join(
        f"{name}: {overproduction_lb[name]:.2f} lb x {costs[name]:.0f} = {score:,.2f}"
        for name, score in ranked_by_score
    )
    allure.attach(
        score_table,
        name="Overproduction x CostPerLb, all 8 items (highest score first)",
        attachment_type=allure.attachment_type.TEXT,
    )
    allure.attach(
        "\n".join(expected_order),
        name="Expected top 5 (by score)",
        attachment_type=allure.attachment_type.TEXT,
    )

    # --- Actual: what the report shows ---
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()
    Path("reports/debug").mkdir(parents=True, exist_ok=True)
    download.save_as("reports/debug/weekly_report_ai_ranking.pdf")  # TEMP: for debugging, remove once done

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, (
        f"AI Ranking section not found for {AI_RANKING_VENUE} — expected it to appear given the "
        f"overproduction scans just seeded for this week"
    )

    actual_order = _get_ranked_item_order(section, [item.name for item in AI_RANKING_ITEMS])
    allure.attach(
        "\n".join(actual_order),
        name="Actual top 5 shown in PDF",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert actual_order == expected_order, (
        f"AI Ranking order mismatch.\n"
        f"Expected (by score): {expected_order}\n"
        f"Actual (from PDF):   {actual_order}\n"
        f"Scores: {scores}"
    )

    # --- Day-by-day breakdown check, for the top-ranked item (deterministic
    # choice: whichever item actually won, not a hardcoded name) ---
    target_item = expected_order[0]
    other_names = [name for name in actual_order if name != target_item]
    week_start, _ = _target_week_range()
    _assert_daily_breakdown_matches(section, target_item, other_names, seeded_ai_ranking_scans, week_start.year)


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("All ranked items survive pagination — none lost or duplicated at a page break")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "With enough menu items and daily rows to span more than one printed page, the AI Ranking "
        "section still shows exactly 5 distinct items, each with a complete, unbroken day-by-day table "
        "— proving no item's block gets cut off or duplicated at a page boundary"
    ),
    steps=(
        "1. In Menu Items management, make sure at least 6-8 items each have a distinct Cost Per Lb\n"
        "2. Using the scanning device, record overproduction scans spread across every day of the week for "
        "each of those items — enough total rows that the AI Ranking section is likely to span more than "
        "one printed page\n"
        "3. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "4. Select that week, click Download, and open the generated PDF\n"
        "5. Count the items listed in the 'Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost' "
        "section — confirm exactly 5 distinct items appear, none missing and none listed twice\n"
        "6. For each of the 5 items, confirm its day-by-day table is complete and matches what was actually "
        "scanned, even if that item's block happens to fall across a page break"
    ),
)
@pytest.mark.regression
def test_ai_ranking_survives_pagination(logged_in_page, seeded_ai_ranking_scans):
    overproduction_lb = {}
    for scan in seeded_ai_ranking_scans:
        name = scan["MenuItemName"]
        overproduction_lb[name] = overproduction_lb.get(name, 0) + scan["Weight"] / OZ_PER_LB
    expected_item_count = min(5, len(overproduction_lb))

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, f"AI Ranking section not found for {AI_RANKING_VENUE}"

    actual_order = _get_ranked_item_order(section, [item.name for item in AI_RANKING_ITEMS])
    allure.attach(
        "\n".join(actual_order),
        name="Items shown (rank order)",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert len(actual_order) == len(set(actual_order)) == expected_item_count, (
        f"Expected exactly {expected_item_count} distinct items across the section (none lost or "
        f"duplicated at a page break), got {len(actual_order)}: {actual_order}"
    )

    week_start, _ = _target_week_range()
    for item_name in actual_order:
        other_names = [name for name in actual_order if name != item_name]
        _assert_daily_breakdown_matches(section, item_name, other_names, seeded_ai_ranking_scans, week_start.year)


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("An item's day-by-day table matches what was actually scanned each day")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "For one menu item, the AI Ranking section's day-by-day table shows, for each day it has a row, "
        "the overproduction value that was actually scanned that day"
    ),
    steps=(
        "1. Using the scanning device, record overproduction scans across the week for one menu item\n"
        "2. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "3. Select that week, click Download, and open the generated PDF\n"
        "4. In the AI Ranking section, find that item's day-by-day table\n"
        "5. Confirm each day's overproduction value matches what was actually scanned that day"
    ),
)
@pytest.mark.regression
def test_daily_breakdown_matches_scanned_data(logged_in_page, seeded_ai_ranking_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, f"AI Ranking section not found for {AI_RANKING_VENUE}"

    # Pick whichever item is actually ranked #1 -- not "most scans", which
    # has no guaranteed relation to the cost-weighted ranking and can pick
    # an item that isn't even in the top 5.
    actual_order = _get_ranked_item_order(section, [item.name for item in AI_RANKING_ITEMS])
    assert actual_order, "Expected at least one ranked item in the AI Ranking section"
    target_item = actual_order[0]

    other_names = [name for name in actual_order if name != target_item]
    week_start, _ = _target_week_range()
    # Only days with nonzero overproduction get a row at all (see
    # DAILY_ROW_PATTERN) -- a day the item wasn't scanned on simply has no
    # row, so we only assert that whichever days ARE present match.
    _assert_daily_breakdown_matches(
        section, target_item, other_names, seeded_ai_ranking_scans, week_start.year
    )


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Report generation completes within an acceptable time even with a full AI Ranking section")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        f"Downloading the Weekly Service Line Report for a week with a fully populated AI Ranking "
        f"section (8 items competing for the top 5) completes within {AI_RANKING_MAX_GENERATION_SECONDS}s"
    ),
    steps=(
        "1. Using the scanning device, record overproduction scans across the week for several menu items "
        "(enough that the AI Ranking section has real ranking work to do)\n"
        "2. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "3. Select that week and click Download\n"
        "4. Time how long it takes from clicking Download to the PDF finishing generation and downloading\n"
        f"5. Confirm it completes within {AI_RANKING_MAX_GENERATION_SECONDS} seconds rather than hanging"
    ),
)
@pytest.mark.regression
@pytest.mark.slow
def test_report_generates_within_acceptable_time(logged_in_page, seeded_ai_ranking_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())

    start = datetime.now()
    download = page.download_pdf()
    elapsed = (datetime.now() - start).total_seconds()

    allure.attach(f"{elapsed:.2f} seconds", name="PDF generation time", attachment_type=allure.attachment_type.TEXT)
    assert elapsed <= AI_RANKING_MAX_GENERATION_SECONDS, (
        f"Report took {elapsed:.2f}s to generate/download, expected <= {AI_RANKING_MAX_GENERATION_SECONDS}s"
    )

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, f"AI Ranking section not found for {AI_RANKING_VENUE}"

    actual_order = _get_ranked_item_order(section, [item.name for item in AI_RANKING_ITEMS])
    target_item = actual_order[0]
    other_names = actual_order[1:]
    week_start, _ = _target_week_range()
    _assert_daily_breakdown_matches(section, target_item, other_names, seeded_ai_ranking_scans, week_start.year)


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Regenerating the same week's report repeatedly produces the same ranking")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "Generating the Weekly Service Line Report for the same week multiple times, with no data or "
        "cost changes in between, produces an identical AI Ranking order each time — the cost used for a "
        "given week is locked in, not recomputed differently on every generation"
    ),
    steps=(
        "1. With overproduction scans already recorded for a week, go to Executive Insights > Reports, "
        "set Report Type = Weekly Service Line Report, and select that week\n"
        "2. Click Download and open the generated PDF — note the AI Ranking section's order\n"
        "3. Without changing anything (no new scans, no cost updates), click Download again for the SAME "
        "week and open the newly generated PDF\n"
        "4. Confirm the AI Ranking section's order in the second PDF is identical to the first"
    ),
)
@pytest.mark.regression
def test_regenerating_same_week_report_produces_same_ranking(logged_in_page, seeded_ai_ranking_scans):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())

    first_download = page.download_pdf()
    first_section = _extract_ai_ranking_section(first_download.path(), AI_RANKING_VENUE)
    assert first_section, f"AI Ranking section not found for {AI_RANKING_VENUE} on first generation"
    first_order = _get_ranked_item_order(first_section, [item.name for item in AI_RANKING_ITEMS])

    second_download = page.download_pdf()
    second_section = _extract_ai_ranking_section(second_download.path(), AI_RANKING_VENUE)
    assert second_section, f"AI Ranking section not found for {AI_RANKING_VENUE} on second generation"
    second_order = _get_ranked_item_order(second_section, [item.name for item in AI_RANKING_ITEMS])

    allure.attach(
        f"First generation:  {first_order}\nSecond generation: {second_order}",
        name="Ranking order across two generations",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert first_order == second_order, (
        f"Expected identical ranking order across two generations of the same week's report.\n"
        f"First:  {first_order}\nSecond: {second_order}"
    )


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("A week's report ranking reflects the cost in effect for that week, not a later cost change")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "Changing a menu item's Cost Per Lb today does not retroactively re-rank a report already "
        "generated for a past (already-completed) week — re-downloading that same week's report still "
        "shows the same ranking order, not something recomputed from today's live cost on every "
        "generation. Regression check for FX-4831 (closed)."
    ),
    steps=(
        "1. With overproduction scans already recorded for a completed past week, go to Executive "
        "Insights > Reports, set Report Type = Weekly Service Line Report, select that week, click "
        "Download, and note the AI Ranking section's order\n"
        "2. In Menu Items management, change one of the ranked items' Cost Per Lb to a noticeably "
        "different value\n"
        "3. Re-download the SAME week's Weekly Service Line Report\n"
        "4. Confirm the ranking order is UNCHANGED from step 1 — the report must not pick up today's "
        "cost change\n"
        "5. Restore the item's original Cost Per Lb"
    ),
)
@pytest.mark.regression
def test_past_week_ranking_unaffected_by_later_cost_change(
    logged_in_page, menu_item_client, seeded_ai_ranking_scans, update_menu_item_cost
):
    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())

    first_download = page.download_pdf()
    first_section = _extract_ai_ranking_section(first_download.path(), AI_RANKING_VENUE)
    assert first_section, f"AI Ranking section not found for {AI_RANKING_VENUE}"
    first_order = _get_ranked_item_order(first_section, [item.name for item in AI_RANKING_ITEMS])
    assert first_order, "Expected at least one ranked item to test a cost change against"

    target_name = first_order[0]
    target_item = next(item for item in AI_RANKING_ITEMS if item.name == target_name)
    current_cost = menu_item_client.get_cost_per_lb(target_item.name, restaurant_id=RESTAURANT_A.id)
    new_cost = current_cost * 3 + 50  # clearly, unmistakably different
    allure.attach(
        f"Ranking before cost change: {first_order}\n"
        f"Changing '{target_item.name}' Cost Per Lb from {current_cost} to {new_cost}",
        name="Cost change plan",
        attachment_type=allure.attachment_type.TEXT,
    )
    update_menu_item_cost(target_item, new_cost)

    page.set_week(_target_week_label())
    second_download = page.download_pdf()
    second_section = _extract_ai_ranking_section(second_download.path(), AI_RANKING_VENUE)
    assert second_section, f"AI Ranking section not found for {AI_RANKING_VENUE} after cost change"
    second_order = _get_ranked_item_order(second_section, [item.name for item in AI_RANKING_ITEMS])

    allure.attach(
        f"Before: {first_order}\nAfter:  {second_order}",
        name="Ranking order before vs after cost change",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert second_order == first_order, (
        f"Expected the week's ranking to stay unchanged after changing '{target_item.name}' Cost Per Lb, "
        f"but it changed.\nBefore: {first_order}\nAfter:  {second_order}"
    )


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Fewer than 5 items with overproduction shows all of them, not padded to 5")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "With fewer than 5 menu items having overproduction, the AI Ranking section shows "
        "exactly those items — not padded with zero-overproduction fillers, not truncated further"
    ),
    steps=(
        "1. For a given venue and week, make sure only 2-4 menu items have any overproduction scans "
        "recorded — every other menu item should have none for that week\n"
        "2. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "3. Select that same week, click Download, and open the generated PDF\n"
        "4. In the venue's 'Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost' section, "
        "confirm exactly those 2-4 items appear (in any order) and no others — the list should not be "
        "padded out to 5 with zero-overproduction items"
    ),
)
@pytest.mark.regression
def test_fewer_than_5_items_shows_all_available(logged_in_page, seeded_ai_ranking_scans_partial):
    _, chosen_items = seeded_ai_ranking_scans_partial
    chosen_names = {item.name for item in chosen_items}

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, (
        f"AI Ranking section not found for {AI_RANKING_VENUE} — expected it to appear given the "
        f"overproduction scans just seeded for this week"
    )

    actual_order = _get_ranked_item_order(section, [item.name for item in AI_RANKING_ITEMS])
    allure.attach(
        "\n".join(actual_order) or "(none)",
        name="Items actually shown in AI Ranking section",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert set(actual_order) == chosen_names, (
        f"Expected exactly the seeded items to appear, no more, no less.\n"
        f"Seeded: {sorted(chosen_names)}\n"
        f"Shown:  {sorted(actual_order)}"
    )
    assert len(actual_order) == AI_RANKING_PARTIAL_ITEM_COUNT, (
        f"Expected exactly {AI_RANKING_PARTIAL_ITEM_COUNT} items shown (not padded to 5), "
        f"got {len(actual_order)}: {actual_order}"
    )


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("The generated PDF contains the AI Ranking page for a venue with overproduction")
@pytest.mark.testcase(
    component="reports",
    type="smoke, regression",
    description=(
        "The 'Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost' page renders somewhere in "
        "the PDF for a venue that has overproduction this week"
    ),
    steps=(
        "1. Using the scanning device, record at least one overproduction scan this week for a menu item\n"
        "2. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "3. Select that week, click Download, and open the generated PDF\n"
        "4. Confirm the 'Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost' title appears "
        "somewhere in that venue's pages\n"
        "5. Compare the shown item's day-by-day overproduction against what was actually scanned"
    ),
)
@pytest.mark.smoke
@pytest.mark.regression
def test_ai_ranking_page_present_in_pdf(logged_in_page, seeded_ai_ranking_scans_partial):
    inserted, chosen_items = seeded_ai_ranking_scans_partial

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    text = _extract_pdf_text(download.path())
    assert AI_RANKING_TITLE in text, (
        f"Expected the AI Ranking page title '{AI_RANKING_TITLE}' to appear somewhere in the generated PDF"
    )

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, f"AI Ranking section not found for {AI_RANKING_VENUE} even though overproduction was seeded"

    target_item = chosen_items[0].name
    other_names = [item.name for item in chosen_items[1:]]
    week_start, _ = _target_week_range()
    _assert_daily_breakdown_matches(section, target_item, other_names, inserted, week_start.year)


# ---------------------------------------------------------------------------
# F-02  Manual only — no email-inbox checking tooling in this suite yet.
#       Documented per the same convention as the other manual/skip cases
#       above, rather than silently having no record of it at all.
# ---------------------------------------------------------------------------


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("The AI Ranking page is present in the PDF attached to the scheduled weekly report email")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When the Weekly Service Line Report is emailed on its schedule, the attached PDF includes the "
        "AI Ranking section, same as a manually downloaded report"
    ),
    steps=(
        "1. Wait for (or trigger) the scheduled Weekly Service Line Report email for a venue with "
        "overproduction this week\n"
        "2. Open the received email and its PDF attachment\n"
        "3. Confirm the 'Top 5 Menu Items Ranked By AI-Estimated Overproduction Cost' section is present "
        "in the attached PDF, same as it would be in a manual download"
    ),
)
@pytest.mark.skip(
    reason="No email-inbox checking tooling in this suite yet — requires either a real mailbox integration "
    "or intercepting the scheduled email job's output"
)
def test_ai_ranking_page_present_in_emailed_report():
    pass


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("An item with consumption but zero overproduction is excluded from the ranking")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "An item that was actively consumed this week but has zero overproduction (no leftover/waste "
        "scans at all) must never appear in the AI Ranking section, since ranking is strictly by "
        "overproduction cost impact, not activity or consumption alone"
    ),
    steps=(
        "1. Using the scanning device, record at least one overproduction (leftover) scan for one menu "
        "item, so the AI Ranking section has something to render\n"
        "2. For a DIFFERENT menu item, record a Refill (consumption) scan for one day this week, but "
        "record NO leftover/overproduction scan for that item at all\n"
        "3. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "4. Select that week, click Download, and open the generated PDF\n"
        "5. Confirm the item with consumption-only activity does NOT appear anywhere in the AI Ranking "
        "section, while the item with actual overproduction does\n"
        "6. Compare the shown item's day-by-day overproduction against what was actually scanned"
    ),
)
@pytest.mark.regression
def test_consumption_only_item_excluded_from_ranking(logged_in_page, seed_scans):
    filler_item, consumption_only_item = random.sample(AI_RANKING_ITEMS, 2)
    inserted = seed_scans([
        (filler_item, random.randint(*AI_RANKING_WEIGHT_RANGE_LB), 0, SCAN_TYPE_LEFTOVER_COMPOSTABLE),
        (consumption_only_item, random.randint(*AI_RANKING_WEIGHT_RANGE_LB), 0, SCAN_TYPE_REFILL),
    ])
    filler_scans = [s for s in inserted if s["Type"] == SCAN_TYPE_LEFTOVER_COMPOSTABLE]

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, f"AI Ranking section not found for {AI_RANKING_VENUE}"

    actual_order = _get_ranked_item_order(section, [item.name for item in AI_RANKING_ITEMS])
    allure.attach(
        "\n".join(actual_order) or "(none)",
        name="Items shown in AI Ranking section",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert filler_item.name in actual_order, (
        f"Expected '{filler_item.name}' (has real overproduction) to appear in the ranking, got: {actual_order}"
    )
    assert consumption_only_item.name not in actual_order, (
        f"'{consumption_only_item.name}' had consumption but zero overproduction — it must not appear in "
        f"the ranking, but was found in: {actual_order}"
    )

    other_names = [name for name in actual_order if name != filler_item.name]
    week_start, _ = _target_week_range()
    _assert_daily_breakdown_matches(section, filler_item.name, other_names, filler_scans, week_start.year)


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("A day with consumption but zero overproduction still shows that day's real consumption")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "For an item shown in the AI Ranking section, a day where consumption occurred but "
        "overproduction was zero still shows a real 'this cycle' consumption value for that day — "
        "consumption data isn't dropped just because overproduction happened to be zero that day. "
        "(Overproduction itself still renders as 'N/A' at zero, same as any other zero-overproduction "
        "day — that part is expected, established behavior, not what this test checks.)"
    ),
    steps=(
        "1. Using the scanning device, record overproduction (leftover) scans for one menu item on at "
        "least 2 days this week, so it qualifies for the AI Ranking top 5\n"
        "2. For a THIRD day this week, record a Refill (consumption) scan for that same item, but no "
        "leftover/overproduction scan at all\n"
        "3. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "4. Select that week, click Download, and open the generated PDF\n"
        "5. In that item's day-by-day table, confirm the consumption-only day shows a real 'this cycle' "
        "consumption number, not N/A"
    ),
)
@pytest.mark.regression
def test_zero_overproduction_day_still_shows_consumption(logged_in_page, seed_scans):
    item = random.choice(AI_RANKING_ITEMS)
    zero_day_offset = 2  # Wednesday — consumption-only, no overproduction
    consumption_lb = random.randint(*AI_RANKING_WEIGHT_RANGE_LB)
    seed_scans([
        (item, random.randint(*AI_RANKING_WEIGHT_RANGE_LB), 0, SCAN_TYPE_LEFTOVER_COMPOSTABLE),
        (item, random.randint(*AI_RANKING_WEIGHT_RANGE_LB), 1, SCAN_TYPE_LEFTOVER_COMPOSTABLE),
        (item, consumption_lb, zero_day_offset, SCAN_TYPE_REFILL),
    ])

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, f"AI Ranking section not found for {AI_RANKING_VENUE}"

    actual_order = _get_ranked_item_order(section, [item.name])
    assert item.name in actual_order, (
        f"Expected '{item.name}' (has real overproduction) to be in the ranking, got: {actual_order}"
    )

    week_start, _ = _target_week_range()
    zero_day_date = week_start + timedelta(days=zero_day_offset)
    cycles = _extract_item_daily_consumption_cycles(section, item.name, [], week_start.year)
    allure.attach(
        "\n".join(f"{d}: last={last} -> this={this}" for d, (last, this) in sorted(cycles.items())) or "(none)",
        name=f"Consumption last cycle -> this cycle for {item.name}",
        attachment_type=allure.attachment_type.TEXT,
    )

    _, this_cycle = cycles.get(zero_day_date, (None, None))
    assert this_cycle is not None, (
        f"Expected {zero_day_date} (zero overproduction, but consumption occurred) to show a real "
        f"'this cycle' consumption value, got N/A: {cycles}"
    )
    assert abs(this_cycle - consumption_lb) <= 0.5, (
        f"Expected {zero_day_date}'s this-cycle consumption to be ~{consumption_lb} lb, got {this_cycle}"
    )


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Each day's consumption compares last cycle to this cycle correctly, including partial and missing data")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "For each day in an item's row, the 'last cycle -> this cycle' consumption comparison reflects "
        "actual recorded consumption on each side independently: both cycles with data show two real "
        "numbers, only the previous cycle having data shows 'real -> N/A', and neither cycle having data "
        "shows 'N/A -> N/A'"
    ),
    steps=(
        "1. Using the scanning device, record a Refill (consumption) scan for one menu item on Monday AND "
        "Tuesday of the week BEFORE the one you'll report on\n"
        "2. In the week you'll actually report on, record a Refill (consumption) scan for that same item "
        "on Monday only — record nothing on Tuesday, and nothing at all (either week) for a third day "
        "(e.g. Wednesday)\n"
        "3. Also record at least one overproduction (leftover) scan for that item on a different day this "
        "week, so it actually appears in the AI Ranking section\n"
        "4. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report, select the "
        "target week, click Download, and open the generated PDF\n"
        "5. In the item's day-by-day table, confirm: Monday shows real numbers on both sides of the arrow "
        "(last cycle and this cycle both had consumption), Tuesday shows a real number -> N/A (only last "
        "cycle had consumption), and Wednesday shows N/A -> N/A (neither cycle had any consumption)"
    ),
)
@pytest.mark.regression
@pytest.mark.skip(reason="Needs presetup/investigation before re-enabling")
def test_consumption_last_cycle_vs_this_cycle_per_day(logged_in_page, seed_scans):
    item = random.choice(AI_RANKING_ITEMS)
    monday_last_lb = random.randint(*AI_RANKING_WEIGHT_RANGE_LB)
    tuesday_last_lb = random.randint(*AI_RANKING_WEIGHT_RANGE_LB)
    monday_this_lb = random.randint(*AI_RANKING_WEIGHT_RANGE_LB)
    filler_overproduction_lb = random.randint(*AI_RANKING_WEIGHT_RANGE_LB)

    seed_scans([
        (item, monday_last_lb, -7, SCAN_TYPE_REFILL),   # last week Monday
        (item, tuesday_last_lb, -6, SCAN_TYPE_REFILL),  # last week Tuesday
        (item, monday_this_lb, 0, SCAN_TYPE_REFILL),    # this week Monday
        # this week Tuesday (day 1) and Wednesday (day 2): deliberately nothing
        (item, filler_overproduction_lb, 3, SCAN_TYPE_LEFTOVER_COMPOSTABLE),  # this week Thursday
    ])

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, f"AI Ranking section not found for {AI_RANKING_VENUE}"

    actual_order = _get_ranked_item_order(section, [item.name])
    assert item.name in actual_order, (
        f"Expected '{item.name}' (has real overproduction) to be in the ranking, got: {actual_order}"
    )

    week_start, _ = _target_week_range()
    monday_date = week_start
    tuesday_date = week_start + timedelta(days=1)
    wednesday_date = week_start + timedelta(days=2)

    cycles = _extract_item_daily_consumption_cycles(section, item.name, [], week_start.year)
    allure.attach(
        "\n".join(f"{d}: last={last} -> this={this}" for d, (last, this) in sorted(cycles.items())) or "(none)",
        name=f"Consumption last cycle -> this cycle for {item.name}",
        attachment_type=allure.attachment_type.TEXT,
    )

    monday_last, monday_this = cycles.get(monday_date, (None, None))
    assert monday_last is not None and abs(monday_last - monday_last_lb) <= 0.5, (
        f"Monday last cycle: expected ~{monday_last_lb} lb, got {monday_last}"
    )
    assert monday_this is not None and abs(monday_this - monday_this_lb) <= 0.5, (
        f"Monday this cycle: expected ~{monday_this_lb} lb, got {monday_this}"
    )

    tuesday_last, tuesday_this = cycles.get(tuesday_date, (None, None))
    assert tuesday_last is not None and abs(tuesday_last - tuesday_last_lb) <= 0.5, (
        f"Tuesday last cycle: expected ~{tuesday_last_lb} lb, got {tuesday_last}"
    )
    assert tuesday_this is None, (
        f"Tuesday this cycle: expected N/A (no consumption recorded this week), got {tuesday_this}"
    )

    wednesday_last, wednesday_this = cycles.get(wednesday_date, (None, None))
    assert wednesday_last is None, (
        f"Wednesday last cycle: expected N/A (no consumption recorded either week), got {wednesday_last}"
    )
    assert wednesday_this is None, (
        f"Wednesday this cycle: expected N/A (no consumption recorded either week), got {wednesday_this}"
    )


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Shifting the Report Start Day excludes data that now falls in the previous week")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When the Report Start Day is moved forward past a day that already had overproduction data, "
        "that day's data must no longer appear in the newly-computed current week's report — it now "
        "belongs to the previous week under the new boundary"
    ),
    steps=(
        "1. Using the scanning device, record an overproduction scan for a menu item on the CURRENT "
        "Report Start Day (e.g. Monday, if that's the current setting)\n"
        "2. Go to Executive Insights > Reports, generate the Weekly Service Line Report for the current "
        "week, and confirm that item appears in the AI Ranking section\n"
        "3. In Report Start Day, click Edit and change it to the NEXT day (e.g. Tuesday), moving the "
        "week boundary one day forward, past the day the scan was recorded on\n"
        "4. Re-generate the Weekly Service Line Report for whatever week is now selected by default\n"
        "5. Confirm the item scanned on the OLD start day is no longer included in this newly-computed "
        "current week — it now falls in the previous week\n"
        "6. Restore the original Report Start Day"
    ),
)
@pytest.mark.regression
def test_shifting_report_start_day_excludes_data_from_previous_week(
    logged_in_page, seed_scans, restore_report_start_day
):
    original_day = restore_report_start_day
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if original_day not in weekday_order:
        pytest.skip(f"Unrecognized current Report Start Day '{original_day}' — can't compute the next day safely")
    new_day = weekday_order[(weekday_order.index(original_day) + 1) % 7]

    item = random.choice(AI_RANKING_ITEMS)
    seed_scans([(item, random.randint(*AI_RANKING_WEIGHT_RANGE_LB), 0, SCAN_TYPE_LEFTOVER_COMPOSTABLE)])

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())

    before_download = page.download_pdf()
    before_section = _extract_ai_ranking_section(before_download.path(), AI_RANKING_VENUE)
    assert before_section, f"AI Ranking section not found for {AI_RANKING_VENUE} before shifting the start day"
    before_order = _get_ranked_item_order(before_section, [item.name])
    assert item.name in before_order, (
        f"Expected '{item.name}' (scanned on {original_day}) to appear before shifting Report Start Day, "
        f"got: {before_order}"
    )

    page.set_report_start_day(new_day)
    after_selected_week = page.get_selected_week()
    after_download = page.download_pdf()
    after_section = _extract_ai_ranking_section(after_download.path(), AI_RANKING_VENUE)

    allure.attach(
        f"Original Report Start Day: {original_day}\nNew Report Start Day: {new_day}\n"
        f"Newly selected week after shift: {after_selected_week}",
        name="Boundary shift",
        attachment_type=allure.attachment_type.TEXT,
    )

    after_order = _get_ranked_item_order(after_section or "", [item.name])
    assert item.name not in after_order, (
        f"Expected '{item.name}' (scanned on the OLD start day, {original_day}) to be excluded from the "
        f"newly-computed current week ({after_selected_week}) after moving the boundary forward to "
        f"{new_day}, but it still appears: {after_order}"
    )


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("A tied cost-impact score is broken by CostPerLb, not raw weight")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When two items land on the exact same overproduction_lb x CostPerLb score via different "
        "weight/cost combinations, the item with the higher CostPerLb ranks above the one with the "
        "higher raw overproduction weight"
    ),
    steps=(
        "1. In Menu Items management, pick two menu items with different, known Cost Per Lb values\n"
        "2. Using the scanning device, record overproduction scans for each item across the week so that "
        "(Item A's total weight x its Cost Per Lb) exactly equals (Item B's total weight x its Cost Per "
        "Lb) — give the lower-cost item more weight and the higher-cost item less, so both reach the same "
        "total dollar impact\n"
        "3. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "4. Select that week, click Download, and open the generated PDF\n"
        "5. In the AI Ranking section, confirm the item with the HIGHER Cost Per Lb is ranked above the "
        "item with the higher raw weight, even though their overall scores are equal\n"
        "6. Compare the higher-ranked item's day-by-day overproduction shown in the PDF against what was "
        "actually scanned"
    ),
)
@pytest.mark.regression
def test_tie_score_broken_by_cost_per_lb(logged_in_page, seeded_tie_break_scores):
    inserted, higher_cost_item, lower_cost_item, cost_a, cost_b, weight_a, _weight_b = seeded_tie_break_scores

    allure.attach(
        f"{higher_cost_item.name}: cost/lb={max(cost_a, cost_b):.2f}\n"
        f"{lower_cost_item.name}: cost/lb={min(cost_a, cost_b):.2f}\n"
        f"Both scores: {weight_a * cost_a:,.2f}",
        name="Engineered tie",
        attachment_type=allure.attachment_type.TEXT,
    )

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, f"AI Ranking section not found for {AI_RANKING_VENUE}"

    actual_order = _get_ranked_item_order(section, [higher_cost_item.name, lower_cost_item.name])
    allure.attach(
        "\n".join(actual_order),
        name="Actual order shown in PDF",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert actual_order == [higher_cost_item.name, lower_cost_item.name], (
        f"Expected the higher-CostPerLb item ({higher_cost_item.name}) to rank above "
        f"{lower_cost_item.name} on a tied score, got: {actual_order}"
    )

    week_start, _ = _target_week_range()
    _assert_daily_breakdown_matches(section, higher_cost_item.name, [lower_cost_item.name], inserted, week_start.year)


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("An exact cost-and-weight tie right at the rank 5/6 boundary shows exactly one of the tied items")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When two different items have the exact same Cost Per Lb AND the exact same total overproduction "
        "weight for the week, and both would otherwise land at rank 5/6, the ranking shows exactly one of "
        "them — not both, not neither"
    ),
    steps=(
        "1. In Menu Items management, find two different menu items that already share the exact same "
        "Cost Per Lb\n"
        "2. Using the scanning device, record overproduction scans for those two items so they end up "
        "with the exact same total weight for the week too (a full tie — same cost, same weight)\n"
        "3. Also record overproduction for at least 4 other items with a clearly higher cost-impact "
        "score than the tied pair, so those 4 occupy ranks 1-4 and the tied pair competes for the "
        "single remaining (5th) slot\n"
        "4. Go to Executive Insights > Reports, set Report Type = Weekly Service Line Report\n"
        "5. Select that week, click Download, and open the generated PDF\n"
        "6. Confirm the AI Ranking section shows all 4 higher-scoring items plus exactly ONE of the two "
        "tied items — 5 total, not 6, not 4"
    ),
)
@pytest.mark.regression
def test_exact_tie_at_rank_boundary_shows_exactly_one(logged_in_page, seeded_boundary_tie_pair):
    inserted, item_a, item_b, filler_names = seeded_boundary_tie_pair

    page = Page(logged_in_page)
    page.open_via_nav()
    page.set_report_type(Page.REPORT_TYPE_WEEKLY_SERVICE_LINE)
    page.set_week(_target_week_label())
    download = page.download_pdf()

    section = _extract_ai_ranking_section(download.path(), AI_RANKING_VENUE)
    assert section, f"AI Ranking section not found for {AI_RANKING_VENUE}"

    allure.attach(
        f"Tied pair (same cost, same weight): {item_a.name} vs {item_b.name}\n"
        f"Filler items (ranks 1-4): {', '.join(filler_names)}",
        name="Engineered tie",
        attachment_type=allure.attachment_type.TEXT,
    )

    all_candidates = [item_a.name, item_b.name] + filler_names
    actual_order = _get_ranked_item_order(section, all_candidates)
    allure.attach(
        "\n".join(actual_order),
        name="Actual top 5 shown in PDF",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert len(actual_order) == 5, (
        f"Expected exactly 5 items shown (4 fillers + one of the tied pair), got {len(actual_order)}: {actual_order}"
    )
    assert set(actual_order[:4]) == set(filler_names), (
        f"Expected the 4 clearly higher-scoring filler items at ranks 1-4, got: {actual_order[:4]}"
    )

    fifth_place = actual_order[4]
    assert fifth_place in (item_a.name, item_b.name), (
        f"Expected rank 5 to be one of the exactly-tied items ({item_a.name}, {item_b.name}), "
        f"got: {fifth_place}"
    )

    other_tied_item = item_b.name if fifth_place == item_a.name else item_a.name
    allure.attach(
        f"Selected for rank 5: {fifth_place}\nExcluded (would-be rank 6): {other_tied_item}",
        name="Tie-break outcome",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert other_tied_item not in actual_order, (
        f"'{other_tied_item}' is tied with '{fifth_place}' on cost and weight — since '{fifth_place}' "
        f"already took rank 5, '{other_tied_item}' must not also appear, but it does: {actual_order}"
    )

    # Broader check across the full known pool (not just our 6 candidates) —
    # confirms no other item, tied or not, sneaks in as an unexpected 6th.
    full_pool_order = _get_ranked_item_order(section, [item.name for item in AI_RANKING_ITEMS])
    assert len(full_pool_order) == 5, (
        f"Expected exactly 5 items total across the whole known pool (no unexpected 6th item), "
        f"got {len(full_pool_order)}: {full_pool_order}"
    )

    week_start, _ = _target_week_range()
    other_names = [name for name in actual_order if name != filler_names[0]]
    _assert_daily_breakdown_matches(section, filler_names[0], other_names, inserted, week_start.year)


# ---------------------------------------------------------------------------
# B-01 / B-02 / B-03  Manual only — none of these are observable from the
#       API or UI. There's no way to see which cost source (User/DB/AI) was
#       actually used for a given item, and no way to see whether the AI
#       generation step was invoked or skipped — that's purely internal
#       backend behavior with no external signal. Documented per the same
#       convention as the other manual/skip cases in this file.
# ---------------------------------------------------------------------------


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("Cost source priority follows User-set > cached DB value > AI-generated")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When an item's cost could come from more than one source (a user-set CostPerLb, a cached "
        "MenuItemCostByWeek value, or a live AI-generated estimate), the report uses them in priority "
        "order: User-set first, then cached DB value, then AI-generated"
    ),
    steps=(
        "1. Set up menu items so their cost could come from different sources: one with a user-set Cost "
        "Per Lb, one with only a cached cost from a previous week's AI generation, one with neither\n"
        "2. Generate the Weekly Service Line Report for a week covering these items\n"
        "3. Confirm the user-set item uses its user-set cost, the cached-only item uses its cached DB "
        "value, and the item with neither triggers a fresh AI-generated cost"
    ),
)
@pytest.mark.skip(
    reason="Which cost source was actually used for a given item is not exposed anywhere observable "
    "(API or UI) — the report only ever shows the final cost value, never which source it came from"
)
def test_cost_source_priority_user_over_db_over_ai():
    pass


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("AI cost generation is only invoked for items actually missing a cost")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When generating a report, the AI cost-generation step is only called for items that have no "
        "User-set or cached DB cost available — items that already have a usable cost never trigger it"
    ),
    steps=(
        "1. Set up a mix of menu items: some with an existing cost (user-set or cached), some with none "
        "at all\n"
        "2. Generate the Weekly Service Line Report for a week covering all of them\n"
        "3. Confirm AI generation was triggered only for the items that had no existing cost, and not for "
        "the ones that already had one"
    ),
)
@pytest.mark.skip(
    reason="Whether the AI generation step was invoked for a given item is not exposed anywhere "
    "observable (API, UI, or logs available to this suite) — there's no external signal to check against"
)
def test_ai_generation_only_called_for_missing_costs():
    pass


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("Regenerating the same week's report reuses the already-generated AI cost, without recalling AI")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "Once an AI-generated cost has been produced for an item for a given week, regenerating that "
        "same week's report reuses the stored cost instead of calling AI generation again"
    ),
    steps=(
        "1. Generate the Weekly Service Line Report for a week that includes an item with no user-set or "
        "cached cost, so AI generation is triggered for it\n"
        "2. Generate the SAME week's report again\n"
        "3. Confirm the second generation reuses the same AI-generated cost from step 1, and does not "
        "invoke AI generation a second time"
    ),
)
@pytest.mark.skip(
    reason="Whether AI generation was invoked again on a second run is not exposed anywhere observable "
    "(API, UI, or logs available to this suite) — only the resulting cost value can be checked, and it "
    "should be identical either way, which doesn't distinguish 'reused' from 'coincidentally regenerated "
    "the same value'"
)
def test_same_week_reuses_ai_cost_without_recalling_ai():
    pass


# ---------------------------------------------------------------------------
# H-01 / H-02 / H-03  Manual only, for now — Menu Cycle setup for a venue
#       hasn't been investigated yet (unclear if it's settable via API or
#       only through the dashboard UI). Documented per the same convention
#       as the other manual/skip cases in this file; revisit once that's
#       figured out.
# ---------------------------------------------------------------------------


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("When a menu cycle is set for this week and next, next cycle details are visible")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When a venue has a Menu Cycle configured for both the current report week and the week after, "
        "the next cycle's details are shown on the report"
    ),
    steps=(
        "1. For a venue, set up a Menu Cycle covering this week AND set a second Menu Cycle covering next "
        "week too\n"
        "2. Generate the Weekly Service Line Report for this week\n"
        "3. Confirm the next week's Menu Cycle details are visible on the report"
    ),
)
@pytest.mark.skip(reason="Menu Cycle setup for a venue not yet investigated (API vs dashboard-only) — revisit later")
def test_next_menu_cycle_visible_when_configured():
    pass


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("When a new menu cycle starts midweek, next cycle details are not shown early")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When a Menu Cycle ends midweek and a new one starts midweek (within the same report week), the "
        "next cycle's details should NOT be shown on the report"
    ),
    steps=(
        "1. For a venue, create a Menu Cycle that ends midweek, then set a new Menu Cycle starting midweek "
        "(same week)\n"
        "2. Generate the Weekly Service Line Report for that week\n"
        "3. Confirm the next Menu Cycle's details are NOT visible on the report"
    ),
)
@pytest.mark.skip(reason="Menu Cycle setup for a venue not yet investigated (API vs dashboard-only) — revisit later")
def test_next_menu_cycle_not_shown_when_current_cycle_changes_midweek():
    pass


@allure.epic("Reports")
@allure.feature("Weekly Service Line Report — AI Ranking (Data)")
@allure.severity(allure.severity_level.MINOR)
@allure.title("When no menu cycle exists at the start of the week but one is applied midweek, next cycle details are not shown")
@pytest.mark.testcase(
    component="reports",
    type="regression",
    description=(
        "When a venue has no Menu Cycle at the start of the report week, but one is created midweek, the "
        "next cycle's details should NOT be shown on the report"
    ),
    steps=(
        "1. Select a venue with no Menu Cycle configured at the start of the week\n"
        "2. Midweek, create a new Menu Cycle for that venue\n"
        "3. Generate the Weekly Service Line Report for that week\n"
        "4. Confirm the next Menu Cycle's details are NOT visible on the report"
    ),
)
@pytest.mark.skip(reason="Menu Cycle setup for a venue not yet investigated (API vs dashboard-only) — revisit later")
def test_next_menu_cycle_not_shown_when_none_existed_at_week_start():
    pass

