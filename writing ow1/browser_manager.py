import os
from playwright.sync_api import sync_playwright

SESSION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".active_session"))

try:
    import ctypes
    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    half_w = screen_w // 2
    right_w = screen_w - half_w
except Exception:
    half_w = 960
    right_w = 960
    screen_h = 1080

class BrowserManager:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.context = None
        self.page = None

    def start(self):
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            channel="chrome",
            headless=self.headless,
            viewport=None,
            args=[
                f"--window-position={half_w},0",
                f"--window-size={right_w},{screen_h}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
        )
        
        pages = self.context.pages
        self.page = pages[0] if pages else self.context.new_page()
        for p in pages[1:]:
            try:
                p.close()
            except Exception:
                pass
        self.page.bring_to_front()
        return self.page

    def close(self):
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
