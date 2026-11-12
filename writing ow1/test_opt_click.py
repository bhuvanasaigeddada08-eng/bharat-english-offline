from browser_manager import BrowserManager

PRACTICE_URL = 'https://corporate.bharatenglish.org/#/practice/exam/9111320?title=Practice&adaptiveFlow=1&returnUrl=%2Fadaptive-learning%2Fskill%2FReading'

def test_option_selection():
    browser = BrowserManager(headless=True)
    page = browser.start()
    page.goto(PRACTICE_URL)
    page.wait_for_timeout(3000)

    options = page.locator("div[role='radiogroup'] div[role='radio']").all()
    print("Options count:", len(options))
    for i, o in enumerate(options):
        print(f"Option {i+1}: {repr(o.inner_text().strip())}")

    # Test click on Option 3 (T-shirts)
    target_opt = options[2]
    print("\nClicking Option 3...")
    target_opt.click()
    page.wait_for_timeout(800)

    check_btn = page.locator("button:has-text('Check')").first
    print("Check disabled after click:", check_btn.get_attribute("disabled"))
    print("Check class:", check_btn.get_attribute("class"))

    # If disabled, try dispatching click or clicking span
    if check_btn.get_attribute("disabled") is not None:
        print("Standard click did not enable Check! Trying span child click...")
        span = target_opt.locator("span.flex-1")
        span.click()
        page.wait_for_timeout(800)
        print("Check disabled after span click:", check_btn.get_attribute("disabled"))

    browser.close()

if __name__ == "__main__":
    test_option_selection()

