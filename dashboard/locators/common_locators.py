"""Locators shared across pages — built on Ant Design's stable class names."""

# Sidebar navigation
SIDEBAR_SUBMENU_TITLE = ".ant-menu-submenu-title"
SIDEBAR_MENU_ITEM = ".ant-menu-item"

# Current View dropdown (top-right of every dashboard page)
CURRENT_VIEW_LABEL = "p:has-text('Current View:')"

# Ant Table
TABLE_LOADED_MARKER = ".ant-table"
TABLE_BODY_ROW = "table tbody tr.ant-table-row"

# Filter chip pattern (kept for reference; no longer used by navigate_back)
SEARCH_ICON = ".anticon-search"
FILTER_CHIP_REMOVE = ".ant-select-selection-item-remove"

# Loading state (Ant Spin + "Loading data" text in empty cell)
LOADING_TEXT = "Loading data"

# Day-view toggle button — immediate next button after the date range picker.
# From PortionTable.jsx, dayRange is buttons[0], rendered first after RangePicker.
DAY_TOGGLE_BUTTON = ".ant-picker-range + button.ant-btn"

# Breadcrumb page-name crumb — always "Consumption/Overproduction Summary".
# It's the SECOND li: BreadCrumbs always renders a hidden, empty home crumb (<Link to="/">) first.
# Renders as plain text normally, or as an <a> when drilled into an item (see below).
# Anchored to .custom-breadcrumb (Header.jsx wrapper) to scope away from sidebar links.
BREADCRUMB_PAGE_LINK = ".custom-breadcrumb li:nth-child(2)"

# Breadcrumb reset link — only rendered as a real <a href="#"> while drilled into an
# item; onClick calls closeMenuItemDrillDown to clear just the drill-down selection.
# Use this (not BREADCRUMB_PAGE_LINK) to click back out of a drill-down.
BREADCRUMB_RESET_LINK = ".custom-breadcrumb a[href='#']"

# Breadcrumb item text nodes (span.ant-breadcrumb-link inside .custom-breadcrumb).
BREADCRUMB_ITEM_LINK = ".custom-breadcrumb .ant-breadcrumb-link"

# Breadcrumb venue crumb (3rd li) — plain-text venue name (breadCrumbParent2), only
# rendered while drilled into a menu item. Never wrapped in <a> — see BreadCrumbs
# component: breadCrumbParent2 is always rendered as raw children, never a Link.
BREADCRUMB_VENUE_ITEM = ".custom-breadcrumb li:nth-child(3)"

# Breadcrumb item-name crumb (4th li) — plain-text menu item name (breadCrumbActive),
# only rendered while drilled into a menu item. Never wrapped in <a>, same as above.
BREADCRUMB_ITEM_CRUMB = ".custom-breadcrumb li:nth-child(4)"

# Filter dropdown selection item (shows the currently selected value in any filter select).
FILTER_SELECTION_ITEM = "form.ant-form .ant-select-selection-item"

# Date range picker (Ant RangePicker — uses MM/DD/YYYY format in this app)
DATE_RANGE_PICKER = ".ant-picker.ant-picker-range"

# All action buttons rendered after the date range picker, in order:
# 0 = day-toggle, 1 = cost-toggle ($/lb), 2 = export (download)
FILTER_ACTION_BUTTONS = ".ant-picker-range ~ button.ant-btn"

# Search/Minimize toggle button (rendered BEFORE the RangePicker in Header.jsx)
SEARCH_BUTTON = "form.ant-form button:has(.anticon-search)"
SEARCH_MINIMIZE_BUTTON = "form.ant-form button:has(.anticon-arrow-right)"

# Menu Items multi-select — only visible when search is active.
# Ant Design renders placeholder as a <span>, not input[placeholder],
# so match by .ant-select-multiple (only multi-select in this form).
MENU_ITEM_SEARCH_SELECT = "form.ant-form .ant-select-multiple"

# --- Menu Item Drill Down — scan gallery (ScanLogDrillDown component) ---

# 'View' button per data-by-dates row — only rendered inside a standard
# (non-catering) menu-item drill-down, scoped within a single row.
SCAN_GALLERY_VIEW_BUTTON = "button:has-text('View')"

# Root container of the expanded scan gallery. At most one is ever mounted,
# since expandedRowKeys holds a single key (one row expanded at a time).
SCAN_GALLERY = ".scan-log-drilldown"

# "No data" message shown inside an expanded gallery when no scans match the
# current Service/Leftover selection — distinct from the outer table's own
# "No data" text (that one lives outside .scan-log-drilldown).
SCAN_GALLERY_EMPTY = ".scan-log-drilldown-empty"

# Service/Leftover dropdown — only rendered when mode="consumption" (Consumption Summary).
SCAN_GALLERY_TOGGLE = ".scan-log-drilldown-type"

# Static "Scan For Leftover" label — rendered instead of the toggle in every
# other mode (e.g. Overproduction Summary, mode="leftover").
SCAN_GALLERY_STATIC_TITLE = ".scan-log-drilldown-title"

# Individual scan thumbnail card within the gallery, and its content pieces.
SCAN_GALLERY_CARD = ".scan-image-thumbnail-refill-div, .scan-image-thumbnail-leftover-div"
SCAN_CARD_NAME = ".scan-menu-label-overflow"
SCAN_CARD_WEIGHT = ".weight-label"
SCAN_CARD_TEMPERATURE = ".temperature-label"
SCAN_CARD_TIME = ".capturedAt-label"

# --- Menu Item Drill Down — scan preview modal (PreviewModal component) ---

# Root of the open Ant Design modal. Scoped narrowly enough for this file's
# use — only ever one scan-preview-shaped modal is open during these flows.
SCAN_PREVIEW_MODAL = ".ant-modal-content"
SCAN_PREVIEW_CLOSE = ".ant-modal-close"
SCAN_PREVIEW_PREV_BUTTON = ".scanPrevBtn"
SCAN_PREVIEW_NEXT_BUTTON = ".scanNextBtn"

# Each detail field is a label (<p class="panPreviewTitle">) followed by one
# or more sibling value divs within the same wrapper.
SCAN_PREVIEW_FIELD_LABEL = ".panPreviewTitle"
SCAN_PREVIEW_FIELD_VALUE = ".scan-thumbnail-info-label.preview-label"