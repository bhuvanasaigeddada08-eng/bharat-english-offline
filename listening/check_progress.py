import sys
import io

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from browser_manager import BrowserManager

LISTENING_URL = "https://corporate.bharatenglish.org/#/adaptive-learning/skill/Listening"

def inspect_progress():
    browser = BrowserManager(headless=True)
    page = browser.start()
    page.goto(LISTENING_URL)
    page.wait_for_timeout(4000)

    topic_cards = page.locator(".card").filter(has_text="lessons").all()
    print(f"Total Course Topics: {len(topic_cards)}")
    for t_idx, topic in enumerate(topic_cards):
        txt = topic.inner_text().strip().replace("\n", " | ")
        print(f"Topic {t_idx+1}: {txt}")

    if topic_cards:
        topic_cards[0].click()
        page.wait_for_timeout(4000)
        try:
            page.wait_for_selector("section.card", timeout=10000)
        except Exception:
            pass
        sections = page.locator("section.card").all()
        print(f"\nTotal lessons in Topic 1: {len(sections)}")
        completed = 0
        for i, s in enumerate(sections):
            text = s.inner_text().replace("\n", " | ")
            is_done = "View Result" in text or "Done" in text and ("80%" in text or "100%" in text or "Bravo!" in text or "YOUR SCORE" in text)
            if is_done:
                completed += 1
            print(f"Lesson {i+1:02d} [{'DONE' if is_done else 'PENDING'}]: {text[:80]}")
        print(f"\nTopic 1 Completed: {completed} / {len(sections)}")

    browser.close()

if __name__ == "__main__":
    inspect_progress()

