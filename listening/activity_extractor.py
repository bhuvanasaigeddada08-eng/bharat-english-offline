import re
import time

def clean_text(s: str) -> str:
    if not s:
        return ""
    return (s.replace('\ufffd', "'")
             .replace('“', '"')
             .replace('”', '"')
             .replace('’', "'")
             .replace('‘', "'")
             .replace('—', "-")
             .replace('–', "-"))

class ActivityExtractor:
    """
    Extracts Listening multiple-choice questions, options, and progress on Bharat English.
    """
    def __init__(self, page):
        self.page = page

    def extract_current_question(self):
        # 1. Dismiss any overlay guides
        try:
            overlay = self.page.locator(".cdk-overlay-container")
            if overlay.count() > 0 and overlay.is_visible():
                skip_btn = overlay.locator("button:has-text('Skip for now'), button:has-text('Skip guide'), button:has-text('Got it')").first
                if skip_btn.count() > 0 and skip_btn.is_visible():
                    skip_btn.click()
                    self.page.wait_for_timeout(600)
        except Exception:
            pass

        # 2. Extract Question text
        question_text = ""
        try:
            q_loc = self.page.locator("div[role='radiogroup']").locator("xpath=preceding-sibling::div[1]")
            if q_loc.count() > 0 and q_loc.first.is_visible():
                question_text = clean_text(q_loc.first.inner_text().strip())
            else:
                fallback_q = self.page.locator("div[class*='leading-relaxed']:has-text('?'), div:has-text('?')").first
                if fallback_q.count() > 0:
                    question_text = clean_text(fallback_q.inner_text().strip())
        except Exception:
            pass

        # 3. Extract Progress indicator (e.g. 0/5)
        progress = "N/A"
        try:
            prog_el = self.page.locator("span.font-medium.shrink-0:has-text('/')").first
            if prog_el.count() > 0:
                progress = prog_el.inner_text().strip()
            else:
                body_txt = self.page.locator("main").inner_text()
                m_prog = re.search(r'(\d+/\d+)', body_txt)
                if m_prog:
                    progress = m_prog.group(1)
        except Exception:
            pass

        # 4. Extract Options
        options = []
        try:
            option_cards = self.page.locator("div[role='radiogroup'] div[role='radio']").all()
            for idx, card in enumerate(option_cards):
                label_el = card.locator("span.flex-1")
                raw_text = label_el.inner_text().strip() if label_el.count() > 0 else card.inner_text().strip()
                # Remove number prefixes like "1\nThursday morning" -> "Thursday morning"
                lines = raw_text.splitlines()
                clean_opt = lines[-1].strip() if len(lines) > 1 else raw_text.strip()
                options.append({
                    "index": idx + 1,
                    "text": clean_text(clean_opt),
                    "full_text": clean_text(raw_text),
                    "element": card
                })
        except Exception:
            pass

        check_btn = self.page.locator("button:has-text('Check')").first
        skip_btn = self.page.locator("button:has-text('Skip')").first

        return {
            "type": "listening_mcq" if options else "unknown",
            "progress": progress,
            "question": question_text,
            "options": options,
            "can_check": check_btn.is_enabled() if check_btn.count() > 0 else False,
            "has_skip": skip_btn.count() > 0
        }

