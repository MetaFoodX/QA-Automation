"""Login page actions."""
from shared.config.settings import settings
from dashboard.pages.base_page import BasePage
from dashboard.locators import login_locators as L


class LoginPage(BasePage):
    def open(self):
        self.page.goto(settings.base_url + "/login")

    def login(self, email: str, password: str):
            self.page.locator(L.EMAIL_INPUT).fill(email)
            self.page.locator(L.PASSWORD_INPUT).fill(password)
            self.page.get_by_role("button", name=L.SIGN_IN_BUTTON_TEXT).click()
            self.page.wait_for_selector(L.LOGGED_IN_MARKER)