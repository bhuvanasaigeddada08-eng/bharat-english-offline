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
    Extracts Writing exercises (prompt, bullets, tone, word count goal, textarea)
    as well as Reading/Comprehension multiple-choice questions on Bharat English.
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

        # 2. Check for Writing Textarea
        ta = self.page.locator("textarea[placeholder*='writing your response'], textarea[aria-label='Your written response'], textarea.cdk-textarea-autosize").first
        if ta.count() > 0 and ta.is_visible():
            main_el = self.page.locator("main")
            raw_text = main_el.inner_text() if main_el.count() > 0 else self.page.locator("body").inner_text()
            full_text = clean_text(raw_text)
            
            # Extract progress (e.g. 0/3, 1/3)
            progress = "N/A"
            m_prog = re.search(r'(\d+/\d+)', full_text)
            if m_prog:
                progress = m_prog.group(1)

            # Extract tone
            tone = "semi-formal"
            m_tone = re.search(r'Tone:\s*([^\n\r]+)', full_text, re.IGNORECASE)
            if m_tone:
                tone = m_tone.group(1).strip()

            # Extract aim words
            aim_words = 50
            m_aim = re.search(r'Aim for\s*(\d+)\+?\s*words', full_text, re.IGNORECASE)
            if m_aim:
                aim_words = int(m_aim.group(1))

            # Extract bullets ("What to include:")
            bullets = []
            if "What to include:" in full_text:
                parts = full_text.split("What to include:")
                after_include = parts[1]
                end_idx = len(after_include)
                for stop_word in ["Tone:", "Aim for", "words", "Skip", "Continue"]:
                    pos = after_include.find(stop_word)
                    if pos != -1 and pos < end_idx:
                        end_idx = pos
                bullet_block = after_include[:end_idx]
                for line in bullet_block.splitlines():
                    cleaned = line.replace("→", "").replace("•", "").replace("*", "").strip()
                    cleaned = clean_text(cleaned)
                    if cleaned and len(cleaned) > 3:
                        bullets.append(cleaned)

            # Extract prompt / scenario (text before "What to include:")
            prompt_text = ""
            lines = full_text.splitlines()
            scenario_lines = []
            capture = False
            for line in lines:
                l_str = line.strip()
                if "Practice" in l_str or re.match(r'^\d+/\d+$', l_str):
                    capture = True
                    continue
                if "What to include:" in l_str:
                    break
                if capture and l_str:
                    scenario_lines.append(l_str)
            prompt_text = " ".join(scenario_lines).strip()
            prompt_text = clean_text(prompt_text)
            if not prompt_text:
                prompt_text = clean_text(full_text[:300])

            continue_btn = self.page.locator("button:has-text('Continue')").first
            submit_btn = self.page.locator("button:has-text('Submit'), button:has-text('Finish')").first

            return {
                "type": "writing",
                "progress": progress,
                "prompt": prompt_text,
                "bullets": bullets,
                "tone": tone,
                "aim_words": aim_words,
                "textarea": ta,
                "continue_btn": continue_btn,
                "submit_btn": submit_btn
            }

        # 3. Check for Multiple-Choice Questions
        option_cards = self.page.locator("div[role='radiogroup'] div[role='radio']").all()
        if len(option_cards) > 0:
            passage_locator = self.page.locator("div.text-sm.text-base-content.leading-relaxed").first
            raw_passage = passage_locator.inner_text().strip() if passage_locator.count() > 0 else ""
            passage = clean_text(raw_passage)

            question_text = ""
            try:
                question_locator = self.page.locator("div[role='radiogroup']").locator("xpath=preceding-sibling::div[1]")
                if question_locator.count() > 0 and question_locator.first.is_visible():
                    question_text = clean_text(question_locator.first.inner_text().strip())
                else:
                    fallback_q = self.page.locator("div[class*='leading-relaxed']:has-text('?')").first
                    if fallback_q.count() > 0:
                        question_text = clean_text(fallback_q.inner_text().strip())
            except Exception:
                pass

            progress = "N/A"
            try:
                prog_el = self.page.locator("span.font-medium.shrink-0:has-text('/')").first
                if prog_el.count() > 0:
                    progress = prog_el.inner_text().strip()
            except Exception:
                pass

            options = []
            for idx, card in enumerate(option_cards):
                label_el = card.locator("span.flex-1")
                raw_opt = label_el.inner_text().strip() if label_el.count() > 0 else card.inner_text().strip()
                options.append({
                    "index": idx + 1,
                    "text": clean_text(raw_opt),
                    "element": card
                })

            check_btn = self.page.locator("button:has-text('Check')").first
            skip_btn = self.page.locator("button:has-text('Skip')").first

            return {
                "type": "multiple_choice",
                "progress": progress,
                "passage": passage,
                "question": question_text,
                "options": options,
                "can_check": check_btn.is_enabled() if check_btn.count() > 0 else False,
                "has_skip": skip_btn.count() > 0
            }

        return {
            "type": "unknown",
            "progress": "N/A"
        }
