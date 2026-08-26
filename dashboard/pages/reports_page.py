"""Executive Insights > Reports — report generator form (ReportType/date/venue/format -> CSV or PDF).

Field order and visibility change depending on the selected Report Type (see
reports_locators.py for why fields are looked up by label instead of position).
"""
import re
from datetime import date

from playwright.sync_api import expect

from shared.config.settings import settings
from shared.utils.antd_helpers import DROPDOWN_VISIBLE, select_dropdown_option
from dashboard.locators import reports_locators as L
from dashboard.pages.base_page import BasePage

_MONTH_ORDER = {
    m: i + 1
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
}


class ReportsPage(BasePage):
    SIDEBAR_GROUP = "Executive Insights"
    SIDEBAR_ITEM = "Reports"

    REPORT_TYPE_CONSUMPTION_SUMMARY = "Consumption Summary"
    REPORT_TYPE_WEEKLY_SERVICE_LINE = "Weekly Service Line Report"
    REPORT_TYPE_SUSTAINABILITY = "Sustainability Report"

    DATE_MODE_ACROSS_DATES = "View across dates"
    DATE_MODE_BY_DATES = "View by dates"

    FORMAT_CSV = "CSV"
    FORMAT_PDF = "PDF"

    # Consumption Summary CSV headers. The server can add a 'HasServiceLine'
    # variant, but the UI never sends that field, so these are the only two
    # header sets reachable from the Reports page.
    CSV_HEADERS_ACROSS_DATES = [
        "Menu Item", "Venue", "Number of Pan",
        "Production (lb)", "Consumption (lb)", "Overproduction (lb)",
        "Production ($)", "Consumption ($)", "Overproduction ($)",
        "Days Served",
    ]
    CSV_HEADERS_BY_DATES = [
        "Date", "Weekday", "MenuItem", "Venue", "Number of Pan",
        "Production (lb)", "Consumption (lb)", "Overproduction (lb)",
        "Production ($)", "Consumption ($)", "Overproduction ($)",
    ]

    def open_via_nav(self, restaurant: str = "Test Kitchen"):
        self.select_current_view(restaurant)
        self.navigate_via_sidebar(self.SIDEBAR_GROUP, self.SIDEBAR_ITEM)
        self.page.locator(L.REPORT_TITLE).wait_for(state="visible")

    # ------------------------------------------------------------------
    # Field visibility / labels
    # ------------------------------------------------------------------

    def get_visible_field_labels(self) -> list[str]:
        """Ordered list of field labels currently rendered (content-span texts)."""
        return [t.strip() for t in self.page.locator(L.CONTENT_SPAN).all_inner_texts() if t.strip()]

    def is_field_visible(self, label: str) -> bool:
        return self._field(label).count() > 0

    def _field(self, label: str):
        """The .content-div wrapping the given field label (exact text match)."""
        return self.page.locator(L.CONTENT_DIV).filter(
            has=self.page.locator(L.CONTENT_SPAN, has_text=re.compile(rf"^{re.escape(label)}$"))
        )

    def _select_in_field(self, label: str, option_text: str, exact: bool = True):
        self._field(label).locator(".ant-select").first.click()
        select_dropdown_option(self.page, option_text, exact=exact)
        self.page.wait_for_timeout(settings.timeouts.short)

    def get_selected_value(self, label: str) -> str:
        """Currently displayed value text for a given field's Select."""
        return self._field(label).locator(".ant-select-selection-item").inner_text().strip()

    def get_dropdown_options(self, label: str) -> list[str]:
        """Open a field's Select, read its visible option labels, close without selecting."""
        self._field(label).locator(".ant-select").first.click()
        dropdown = self.page.locator(DROPDOWN_VISIBLE).last
        dropdown.locator(".ant-select-item-option").first.wait_for(state="visible")
        options = dropdown.locator(".ant-select-item-option").all_inner_texts()
        self.page.keyboard.press("Escape")
        return [o.strip() for o in options]

    # ------------------------------------------------------------------
    # Field setters
    # ------------------------------------------------------------------

    def set_report_type(self, report_type: str):
        self._select_in_field("Report Type", report_type)
        self.page.wait_for_timeout(settings.timeouts.short)  # field set re-renders

    def set_venue(self, venue_name: str):
        self._select_in_field("Venue", venue_name)

    def set_meal_period(self, meal_period: str):
        self._select_in_field("Meal Period", meal_period)

    def set_date_mode(self, mode: str):
        self._select_in_field("Date Mode", mode)

    def set_report_format(self, fmt: str):
        self._select_in_field("Report Format", fmt)

    def set_category(self, category: str):
        if not self.is_options_expanded():
            self.toggle_more_options()
        self._select_in_field("Category", category)

    def set_menu_item(self, menu_item_name: str):
        if not self.is_options_expanded():
            self.toggle_more_options()
        self._select_in_field("Menu Item", menu_item_name)

    def is_options_expanded(self) -> bool:
        return L.OPTIONS_TOGGLE_LESS in self.get_visible_field_labels()

    def toggle_more_options(self):
        label = L.OPTIONS_TOGGLE_LESS if self.is_options_expanded() else L.OPTIONS_TOGGLE_MORE
        self.page.locator(L.CONTENT_SPAN, has_text=label).click()
        self.page.wait_for_timeout(settings.timeouts.short)

    # ------------------------------------------------------------------
    # Date range (two independent, readonly DatePickers — not a RangePicker)
    # ------------------------------------------------------------------

    def set_date_range(self, start: date, end: date):
        self.set_start_date(start)
        self.set_end_date(end)
        self.page.wait_for_timeout(settings.timeouts.short)

    def set_start_date(self, target: date):
        self._select_date(self._field("Date").locator("input").nth(0), target)

    def set_end_date(self, target: date):
        self._select_date(self._field("Date").locator("input").nth(1), target)

    def get_date_input_values(self) -> tuple[str, str]:
        """Currently displayed (start, end) date input values, as 'MM/DD/YYYY' strings."""
        inputs = self._field("Date").locator("input")
        return inputs.nth(0).get_attribute("value"), inputs.nth(1).get_attribute("value")

    def _select_date(self, picker_input, target: date):
        """Open the calendar panel and click the target day, navigating months as needed."""
        cell = self._open_calendar_to_day(picker_input, target)
        cell.click()

    def is_date_disabled(self, which: str, target: date) -> bool:
        """Open the start/end DatePicker, navigate to target's month, report whether that
        day is disabled (per disabledStartDate/disabledEndDate), without clicking it."""
        inputs = self._field("Date").locator("input")
        picker_input = inputs.nth(0 if which == "start" else 1)
        cell = self._open_calendar_to_day(picker_input, target)
        classes = cell.get_attribute("class") or ""
        self.page.keyboard.press("Escape")
        return "ant-picker-cell-disabled" in classes

    def _open_calendar_to_day(self, picker_input, target: date):
        """Open picker_input's calendar, navigate month-by-month to target, return its day cell."""
        picker_input.click()
        self.page.wait_for_timeout(300)
        panel = self.page.locator(L.CALENDAR_DROPDOWN).last
        title = target.isoformat()
        for _ in range(36):  # ~3 years of month-nav headroom
            cell = panel.locator(f'{L.CALENDAR_CELL_IN_VIEW}[title="{title}"]')
            if cell.count():
                return cell.first
            header = panel.locator(L.CALENDAR_HEADER_VIEW).inner_text()
            match = re.match(r"([A-Za-z]{3})(\d{4})", header)
            current_ord = int(match.group(2)) * 12 + _MONTH_ORDER[match.group(1)]
            target_ord = target.year * 12 + target.month
            button = L.CALENDAR_PREV_BTN if target_ord < current_ord else L.CALENDAR_NEXT_BTN
            panel.locator(button).click()
            self.page.wait_for_timeout(150)
        raise TimeoutError(f"Could not find calendar cell for {title}")

    def is_warning_banner_visible(self) -> bool:
        return self.page.locator(L.WARNING_BANNER).is_visible()

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def click_download(self):
        self.page.get_by_role("button", name=L.DOWNLOAD_BUTTON_TEXT).click()

    def download_csv(self):
        """Click Download and return the Playwright Download object. Report Format must be CSV."""
        with self.page.expect_download() as dl_info:
            self.click_download()
        return dl_info.value

    def download_pdf(self):
        """Click Download and wait through the generation modal for the PDF. Report Format must be PDF."""
        with self.page.expect_download(timeout=settings.timeouts.navigation) as dl_info:
            self.click_download()
        return dl_info.value

    # ------------------------------------------------------------------
    # PDF generation modal (GenerateModal.jsx)
    # ------------------------------------------------------------------

    def is_pdf_modal_visible(self) -> bool:
        return self.page.locator(L.PDF_MODAL).is_visible()

    def wait_for_pdf_modal(self):
        self.page.locator(L.PDF_MODAL).wait_for(state="visible")

    def get_pdf_modal_text(self) -> str:
        """GenerateModal.jsx types this text out one character every 60ms
        via setInterval, starting from '' -- read right after the modal
        opens, it can genuinely still be empty. Poll briefly for non-empty
        text instead of reading once mid-animation."""
        locator = self.page.locator(L.PDF_MODAL_BODY)
        expect(locator).not_to_have_text("", timeout=2000)
        return locator.inner_text().strip()

    def click_pdf_cancel(self):
        self.page.get_by_role("button", name=L.PDF_MODAL_CANCEL_BUTTON_TEXT).click()
        self.page.locator(L.PDF_MODAL).wait_for(state="hidden")

    def is_pdf_modal_error_visible(self) -> bool:
        return self.page.locator(L.PDF_MODAL_ERROR_DIV).is_visible()

    def wait_for_pdf_modal_error(self):
        self.page.locator(L.PDF_MODAL_ERROR_DIV).wait_for(state="visible", timeout=settings.timeouts.default)

    def click_pdf_retry(self):
        self.page.get_by_role("button", name=L.PDF_MODAL_RETRY_BUTTON_TEXT).click()

    # ------------------------------------------------------------------
    # Global message toast (message.error / message.success)
    # ------------------------------------------------------------------

    def wait_for_message(self, text: str):
        self.page.locator(L.MESSAGE_TOAST, has_text=text).wait_for(state="visible")

    def is_message_visible(self, text: str) -> bool:
        return self.page.locator(L.MESSAGE_TOAST, has_text=text).is_visible()

    # ------------------------------------------------------------------
    # Weekly Service Line Report — 'Date' is a single week-picker Select here,
    # not the two DatePickers used by every other report type.
    # ------------------------------------------------------------------

    def set_week(self, week_label: str):
        self._select_in_field("Date", week_label)

    def get_selected_week(self) -> str:
        return self.get_selected_value("Date")

    def get_week_options(self) -> list[str]:
        return self.get_dropdown_options("Date")

    # ------------------------------------------------------------------
    # Weekly Service Line Report — 'Report Start Day' (plain text + Edit
    # button, opens a modal with 7 day buttons, not an Ant Select field)
    # ------------------------------------------------------------------

    def get_report_start_day(self) -> str:
        """Currently configured Report Start Day, e.g. 'Monday'. Reads the
        field's full text and strips the known label/button text rather than
        relying on exact DOM structure between the value and the Edit button.
        """
        full_text = self._field("Report Start Day").inner_text()
        value = full_text.replace("Report Start Day", "").replace(L.REPORT_START_DAY_EDIT_BUTTON_TEXT, "")
        return value.strip()

    def open_report_start_day_modal(self):
        self._field("Report Start Day").get_by_role(
            "button", name=L.REPORT_START_DAY_EDIT_BUTTON_TEXT
        ).click()
        self.page.locator(L.REPORT_START_DAY_MODAL, has_text=L.REPORT_START_DAY_MODAL_TITLE).wait_for(state="visible")

    _DAY_ABBREVIATIONS = {
        "Sunday": "Sun", "Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed",
        "Thursday": "Thu", "Friday": "Fri", "Saturday": "Sat",
    }

    def set_report_start_day(self, day_name: str):
        """Full flow: open the modal, pick a day (full name, e.g. 'Tuesday' —
        mapped internally to the modal's 3-letter button label), Save.

        Waits for the field's displayed value to actually update afterward,
        since this triggers a server round-trip (and re-renders the Date
        field's week options).
        """
        abbreviation = self._DAY_ABBREVIATIONS[day_name]
        self.open_report_start_day_modal()
        modal = self.page.locator(L.REPORT_START_DAY_MODAL, has_text=L.REPORT_START_DAY_MODAL_TITLE)
        modal.get_by_role("button", name=abbreviation, exact=True).click()
        modal.get_by_role("button", name=L.REPORT_START_DAY_SAVE_BUTTON_TEXT).click()
        modal.wait_for(state="hidden")
        self.page.wait_for_timeout(settings.timeouts.short)

    def cancel_report_start_day_modal(self):
        modal = self.page.locator(L.REPORT_START_DAY_MODAL, has_text=L.REPORT_START_DAY_MODAL_TITLE)
        modal.get_by_role("button", name=L.REPORT_START_DAY_CANCEL_BUTTON_TEXT).click()
        modal.wait_for(state="hidden")

    # ------------------------------------------------------------------
    # Sustainability Report — Time Range + (role-gated) Baseline Rate
    # ------------------------------------------------------------------

    def set_time_range(self, label: str):
        self._select_in_field("Time Range", label)

    def get_selected_time_range(self) -> str:
        return self.get_selected_value("Time Range")

    def get_time_range_options(self) -> list[str]:
        return self.get_dropdown_options("Time Range")

    def get_baseline_rate_value(self) -> str:
        """The read-only Baseline Rate input's current value (numeric string, no '%')."""
        return self._field("Baseline Rate").locator("input").get_attribute("value")

    def open_baseline_config_modal(self):
        self._field("Baseline Rate").locator("button").click()
        self.page.locator(L.BASELINE_MODAL).wait_for(state="visible")

    # ------------------------------------------------------------------
    # Baseline Rate config modal (BaselineConfigModal.jsx)
    # ------------------------------------------------------------------

    def is_baseline_modal_visible(self) -> bool:
        return self.page.locator(L.BASELINE_MODAL).is_visible()

    def get_baseline_modal_title(self) -> str:
        return self.page.locator(L.BASELINE_MODAL).locator(L.BASELINE_MODAL_TITLE).inner_text().strip()

    def _baseline_form_item(self, label: str):
        """The .ant-form-item wrapping a given Form.Item label inside the Baseline modal.

        Substring match (not anchored) since AntD may render a trailing colon on
        the label text ('Custom Rate:') — the three labels here don't collide.
        """
        return self.page.locator(L.BASELINE_MODAL).locator(".ant-form-item").filter(
            has=self.page.locator(".ant-form-item-label", has_text=label)
        )

    def get_baseline_default_value(self) -> str:
        return self._baseline_form_item("Default Value").locator("input").get_attribute("value")

    def is_baseline_custom_rate_on(self) -> bool:
        switch = self._baseline_form_item("Custom Rate").locator(L.BASELINE_CUSTOM_RATE_SWITCH)
        return "ant-switch-checked" in (switch.get_attribute("class") or "")

    def toggle_baseline_custom_rate(self):
        self._baseline_form_item("Custom Rate").locator(L.BASELINE_CUSTOM_RATE_SWITCH).click()

    def set_baseline_custom_value(self, value: str):
        self._baseline_form_item("Custom Value").locator("input").fill(value)

    def is_baseline_custom_value_input_visible(self) -> bool:
        return self._baseline_form_item("Custom Value").locator("input").is_visible()

    def get_baseline_validation_error(self) -> str:
        return self.page.locator(L.BASELINE_MODAL).locator(L.BASELINE_VALIDATION_ERROR).inner_text().strip()

    def click_baseline_update(self):
        self.page.locator(L.BASELINE_MODAL).get_by_role(
            "button", name=L.BASELINE_UPDATE_BUTTON_TEXT
        ).click()

    def click_baseline_cancel(self):
        self.page.locator(L.BASELINE_MODAL).get_by_role(
            "button", name=L.BASELINE_CANCEL_BUTTON_TEXT
        ).click()
        self.page.locator(L.BASELINE_MODAL).wait_for(state="hidden")
