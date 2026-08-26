"""Locators for the Executive Insights > Reports page (report generator form).

This page is NOT built on form.ant-form + Ant Table like the other Executive
Insights pages — each field is a plain <div class="content-div"> containing a
label <div class="content-span"> and an Ant Select/DatePicker, all outside any
<form>. Field order/visibility changes depending on the selected Report Type.
"""

REPORT_TITLE = ".report-title"
CONTENT_DIV = ".content-div"
CONTENT_SPAN = ".content-span"

DOWNLOAD_BUTTON_TEXT = "Download"

OPTIONS_TOGGLE_MORE = "See More Options"
OPTIONS_TOGGLE_LESS = "See Less Options"

# Long-date-range warning banner (shown when the selected range exceeds ~4 months)
WARNING_BANNER = ".warning"

# Calendar panel opened by clicking a (readonly) DatePicker input — there is no
# RangePicker here, just two independent DatePickers with a swap-right icon between.
CALENDAR_DROPDOWN = ".ant-picker-dropdown"
CALENDAR_HEADER_VIEW = ".ant-picker-header-view"
CALENDAR_PREV_BTN = ".ant-picker-header-prev-btn"
CALENDAR_NEXT_BTN = ".ant-picker-header-next-btn"
CALENDAR_CELL_IN_VIEW = ".ant-picker-cell-in-view"

# PDF generation modal (GenerateModal.jsx) — shown instead of an immediate
# download when Report Format = PDF.
PDF_MODAL = ".custom-modal"
PDF_MODAL_BODY = ".ant-modal-body"
PDF_MODAL_ERROR_DIV = ".error-div"
PDF_MODAL_CANCEL_BUTTON_TEXT = "Cancel"
PDF_MODAL_RETRY_BUTTON_TEXT = "Retry"
PDF_MODAL_ERROR_TEXT = "Something went wrong while generating the report"

# Ant Design global message toast (message.error / message.success)
MESSAGE_TOAST = ".ant-message"

# Baseline Rate config modal (BaselineConfigModal.jsx) — a plain antd Modal (no
# custom className), opened via the gear-icon button next to the Baseline Rate
# field on the Sustainability Report form. ':not(.custom-modal)' excludes the
# PDF generation modal (GenerateModal.jsx), which carries that extra class.
BASELINE_MODAL = ".ant-modal:not(.custom-modal)"
BASELINE_MODAL_TITLE = ".ant-modal-title"
BASELINE_CUSTOM_RATE_SWITCH = ".ant-switch"
BASELINE_VALIDATION_ERROR = ".ant-form-item-explain-error"
BASELINE_CANCEL_BUTTON_TEXT = "Cancel"
BASELINE_UPDATE_BUTTON_TEXT = "Update"

# Weekly Service Line Report — 'Report Start Day' field (plain text value +
# Edit button, not an Ant Select like the other fields). Edit opens a modal
# with 7 day buttons (Sun-Sat) plus Cancel/Save.
REPORT_START_DAY_EDIT_BUTTON_TEXT = "Edit"
REPORT_START_DAY_MODAL_TITLE = "Select Report Start Day"
REPORT_START_DAY_MODAL = ".ant-modal:not(.custom-modal)"
REPORT_START_DAY_SAVE_BUTTON_TEXT = "Save"
REPORT_START_DAY_CANCEL_BUTTON_TEXT = "Cancel"
