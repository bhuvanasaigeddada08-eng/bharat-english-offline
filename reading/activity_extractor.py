import time

class ActivityExtractor:
    """
    Extracts reading material, passages, question text, and options
    using verified DOM selectors on Bharat English.
    """
    def __init__(self, page):
        self.page = page

    def extract_current_question(self):
        # 1. Check for unexpected dialogs or overlays
        try:
            overlay = self.page.locator(".cdk-overlay-container")
            if overlay.count() > 0 and overlay.is_visible():
                skip_btn = overlay.locator("button:has-text('Skip for now'), button:has-text('Skip guide'), button:has-text('Got it')")
                if skip_btn.count() > 0 and skip_btn.first.is_visible():
                    skip_btn.first.click()
                    self.page.wait_for_timeout(600)
        except Exception:
            pass

        # 2. Extract passage text
        passage_locator = self.page.locator("div.text-sm.text-base-content.leading-relaxed").first
        passage = ""
        if passage_locator.count() > 0:
            passage = passage_locator.inner_text().strip()

        # 3. Extract question text (using clean, standard CSS/XPath)
        question_text = ""
        try:
            # Sibling immediately before the options radiogroup
            question_locator = self.page.locator("div[role='radiogroup']").locator("xpath=preceding-sibling::div[1]")
            if question_locator.count() > 0 and question_locator.first.is_visible():
                question_text = question_locator.first.inner_text().strip()
            else:
                # Fallback to any question text element
                fallback_q = self.page.locator("div[class*='leading-relaxed']:has-text('?')").first
                if fallback_q.count() > 0:
                    question_text = fallback_q.inner_text().strip()
        except Exception:
            pass

        # 4. Extract progress indicator (e.g., "(0/5)")
        progress = "N/A"
        try:
            prog_el = self.page.locator("span.font-medium.shrink-0:has-text('/')").first
            if prog_el.count() > 0:
                progress = prog_el.inner_text().strip()
        except Exception:
            pass

        # 5. Extract available options
        options = []
        try:
            option_cards = self.page.locator("div[role='radiogroup'] div[role='radio']").all()
            for idx, card in enumerate(option_cards):
                label_el = card.locator("span.flex-1")
                text = label_el.inner_text().strip() if label_el.count() > 0 else card.inner_text().strip()
                options.append({
                    "index": idx + 1,
                    "text": text,
                    "element": card
                })
        except Exception:
            pass

        # 6. Check button controls
        check_btn = self.page.locator("button:has-text('Check')").first
        skip_btn = self.page.locator("button:has-text('Skip')").first

        return {
            "progress": progress,
            "passage": passage,
            "question": question_text,
            "options": options,
            "can_check": check_btn.is_enabled() if check_btn.count() > 0 else False,
            "has_skip": skip_btn.count() > 0
        }
