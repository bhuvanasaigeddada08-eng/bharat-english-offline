import os
import sys
import time
from browser_manager import BrowserManager
from activity_extractor import ActivityExtractor
from answer_generator import AnswerGenerator
from progress_tracker import ProgressTracker

# Target practice activity URL inspected
PRACTICE_URL = "https://corporate.bharatenglish.org/#/practice/exam/9111318?title=Practice&adaptiveFlow=1&returnUrl=%2Fadaptive-learning%2Fskill%2FReading"

def run_dry_run():
    print("=" * 65)
    print(" BHARAT ENGLISH - READING AUTOMATION PROTOTYPE (DRY-RUN)")
    print("=" * 65)
    print("[Safety Rule] Dry-run mode active. No answers will be submitted.")
    print("Press Ctrl+C at any time in terminal to immediately stop the agent.")
    print("-" * 65)

    browser = BrowserManager(headless=True)
    try:
        page = browser.start()
        print(f"[1/4] Navigating to Reading Activity: {PRACTICE_URL}")
        page.goto(PRACTICE_URL)
        page.wait_for_timeout(4000)

        # Security & State check
        if "login" in page.url:
            print("[Error] Session expired or not logged in. Please run login first.")
            return

        extractor = ActivityExtractor(page)
        generator = AnswerGenerator()
        tracker = ProgressTracker()

        print("[2/4] Extracting Reading Activity elements...")
        activity = extractor.extract_current_question()

        print("\n" + "="*30 + " EXTRACTED ACTIVITY " + "="*30)
        print(f"Progress Indicator : {activity['progress']}")
        print(f"\nPassage Preview    :\n{activity['passage'][:300]}...")
        print(f"\nQuestion           : {activity['question']}")
        print("\nAvailable Options  :")
        for opt in activity["options"]:
            print(f"  [{opt['index']}] {opt['text']}")

        print("\n[3/4] Generating Solution (Dry-Run)...")
        solution = generator.solve(
            passage=activity["passage"],
            question=activity["question"],
            options=activity["options"]
        )

        print("-" * 65)
        print(f"PROPOSED ANSWER   : [{solution['recommended_index']}] {solution.get('recommended_text')}")
        print(f"CONFIDENCE        : {solution['confidence']*100:.1f}%")
        print(f"REASONING         : {solution['reasoning']}")
        print("-" * 65)

        print("[4/4] Logging progress safely without altering completion status...")
        tracker.record_dry_run(
            question=activity["question"],
            recommended_answer=solution.get("recommended_text"),
            reasoning=solution["reasoning"]
        )

        print("\n[Complete] Dry-run executed successfully! Zero network submissions made.")
    except KeyboardInterrupt:
        print("\n[Interrupted] Stopped by user.")
    except Exception as e:
        print(f"\n[Error] Encountered unexpected state: {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    run_dry_run()

