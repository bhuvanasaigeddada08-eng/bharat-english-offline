import os
from playwright.sync_api import sync_playwright

USER_DATA_DIR = os.path.abspath("./.browser_profile")

class BrowserManager:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.context = None
        self.page = None

    def start(self):
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
            args=["--start-maximized"]
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        return self.page

    def close(self):
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()

