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

# Breadcrumb page link (href='#' calls reloadPage to clear filter).
# Anchored to .custom-breadcrumb (Header.jsx wrapper) to scope away from sidebar links.
BREADCRUMB_PAGE_LINK = ".custom-breadcrumb a[href='#']"

# Breadcrumb item text nodes (span.ant-breadcrumb-link inside .custom-breadcrumb).
BREADCRUMB_ITEM_LINK = ".custom-breadcrumb .ant-breadcrumb-link"

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