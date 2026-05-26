"""Ant Design widget helpers."""
import re

from playwright.sync_api import Page
from config.settings import settings

DROPDOWN_VISIBLE = ".ant-select-dropdown:not(.ant-select-dropdown-hidden)"
VIRTUAL_LIST_HOLDER = ".rc-virtual-list-holder"
SCROLL_STEP_PX = 300


def select_dropdown_option(
    page: Page,
    option_text: str,
    exact: bool = False,
    max_attempts: int | None = None,
    step_pause_ms: int | None = None,
) -> None:
    """Click an option in an open Ant Design dropdown.

    Works for both simple and virtual-scroll dropdowns. Scrolls only if the
    dropdown actually has a virtual list.

    Args:
        option_text: Visible text of the option to click.
        exact: If True, match text exactly. Default False = substring match.
    """
    max_attempts = max_attempts or settings.timeouts.scroll_max_attempts
    step_pause_ms = step_pause_ms or settings.timeouts.scroll_step_pause

    dropdown = page.locator(DROPDOWN_VISIBLE).last
    holder = dropdown.locator(VIRTUAL_LIST_HOLDER)
    has_virtual_list = holder.count() > 0

    matcher = (
        re.compile(rf"^\s*{re.escape(option_text)}\s*$")
        if exact else option_text
    )

    for _ in range(max_attempts):
        option = dropdown.locator(".ant-select-item-option").filter(has_text=matcher)
        if option.count() > 0:
            option.first.dispatch_event("click")
            return
        if not has_virtual_list:
            break
        holder.evaluate(f"(el) => el.scrollTop += {SCROLL_STEP_PX}")
        page.wait_for_timeout(step_pause_ms)

    visible = dropdown.locator(".ant-select-item-option").all_inner_texts()
    raise TimeoutError(
        f"Option '{option_text}' not found in dropdown. Visible options: {visible[:10]}"
    )