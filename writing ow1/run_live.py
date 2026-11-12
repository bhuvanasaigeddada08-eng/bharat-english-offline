import io
import os
import sys
import time

# Ensure Windows terminal never crashes on UTF-8 / charmap characters
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from browser_manager import BrowserManager
from activity_extractor import ActivityExtractor
from answer_generator import AnswerGenerator
from progress_tracker import ProgressTracker

WRITING_SKILL_URL = "https://corporate.bharatenglish.org/#/adaptive-learning/skill/Writing"

def ensure_logged_in(page, target_url):
    """Checks if the user needs to log in, prompts in terminal, and waits until logged in."""
    LOGIN_URL = "https://corporate.bharatenglish.org/#/user/login"
    
    # 1. Close extra blank tabs and bring page to front
    for p in page.context.pages:
        if p != page and (p.url == "about:blank" or not p.url.startswith("http")):
            try:
                p.close()
            except Exception:
                pass
    page.bring_to_front()

    # 2. Fresh login requested for a friend
    if os.getenv("BHARAT_FORCE_LOGOUT") == "1":
        print("[Account Switch] Fresh Login requested -> Loading login page for new friend...")
        os.environ["BHARAT_FORCE_LOGOUT"] = "0"
        try:
            page.context.clear_cookies()
        except Exception:
            pass
        page.goto(LOGIN_URL)
        page.wait_for_timeout(3000)
        try:
            page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
            page.goto(LOGIN_URL)
            page.wait_for_timeout(3000)
        except Exception:
            pass
    else:
        print(f"[Nav] Checking login state at: {target_url}")
        page.goto(target_url)
        page.wait_for_timeout(3500)
        if page.url == "about:blank":
            page.goto(target_url)
            page.wait_for_timeout(3500)

    # 3. Detect if currently on login screen
    is_login_page = ("login" in page.url or 
                     page.locator("input[type='password']").count() > 0 or 
                     page.locator("button:has-text('Sign In'), button:has-text('Log In'), button:has-text('Login')").count() > 0)

    if is_login_page:
        print("\n" + "=" * 70)
        print(" [ACTION REQUIRED] Please Log In to Bharat English in the Chrome window.")
        print(" Enter credentials for your account or your friend's account.")
        print(" Waiting for you to complete login... (Auto-starting after login)")
        print("=" * 70)

        while True:
            page.wait_for_timeout(2500)
            current_url = page.url
            has_password = page.locator("input[type='password']").count() > 0
            if "login" not in current_url and not has_password and ("adaptive-learning" in current_url or "dashboard" in current_url or "skill" in current_url):
                print("\n[Success] Login detected! Proceeding to course modules...\n")
                page.wait_for_timeout(2000)
                page.goto(target_url)
                page.wait_for_timeout(4000)
                break

def dismiss_overlays(page):
    """Dismiss any modal guide or informational popup, but handle confirmation dialogs specifically."""
    try:
        overlays = page.locator(".cdk-overlay-container")
        if overlays.count() > 0:
            # 1. "Ready to submit?" confirmation dialog -> CLICK SUBMIT!
            submit_dialog_btn = page.locator(".cdk-overlay-container button:has-text('Submit')").first
            if submit_dialog_btn.count() > 0 and submit_dialog_btn.is_visible():
                print("  [Dialog] 'Ready to submit?' dialog detected -> Clicking SUBMIT!")
                submit_dialog_btn.click()
                page.wait_for_timeout(2500)
                return True

            # 2. "Go to practice" dialog -> CLICK "Go to practice ->"
            go_practice_btn = page.locator(".cdk-overlay-container button:has-text('Go to practice')").first
            if go_practice_btn.count() > 0 and go_practice_btn.is_visible():
                print("  [Dialog] Found 'Go to practice' dialog -> Clicking 'Go to practice ->'...")
                go_practice_btn.click()
                page.wait_for_timeout(3000)
                return True

            # 3. "Hold It Right There!" alert -> Click Continue Learning
            hold_btn = page.locator(".cdk-overlay-container button:has-text('Continue Learning')").first
            if hold_btn.count() > 0 and hold_btn.is_visible():
                print("  [Dialog] 'Hold It Right There!' detected -> Clicking 'Continue Learning'...")
                hold_btn.click()
                page.wait_for_timeout(800)
                return True

            # 4. Informational guides (Skip guide, Got it, etc.)
            skip_btn = page.locator(".cdk-overlay-container button:has-text('Skip for now'), .cdk-overlay-container button:has-text('Skip guide'), .cdk-overlay-container button:has-text('Got it')").first
            if skip_btn.count() > 0 and skip_btn.is_visible():
                skip_btn.click()
                page.wait_for_timeout(800)
                return True
    except Exception:
        pass
    return False

def handle_video(page, section):
    """Opens video dialog and immediately closes it to satisfy prerequisite if video exists."""
    try:
        btns = section.locator("button").all()
        sec_text = section.inner_text()
        if "Watch the video" in sec_text or "Video" in sec_text and len(btns) >= 1:
            print("  [Video] Triggering video prerequisite...")
            btns[0].click()
            page.wait_for_timeout(2000)
            
            close_btn = page.locator("button[aria-label='Close video dialog'], button.close")
            if close_btn.count() > 0 and close_btn.first.is_visible():
                print("  [Video] Closed instantly -> Video Done.")
                close_btn.first.click()
                page.wait_for_timeout(1500)
    except Exception as e:
        print(f"  [Video] Error: {e}")

def handle_learn(page, section):
    """Clicks Learn button, scrolls container to bottom, and clicks 'Go to practice'."""
    try:
        learn_btn = section.locator("button:has-text('Learn')").first
        if learn_btn.count() == 0:
            btns = section.locator("button").all()
            sec_text = section.inner_text()
            if "Watch the video" in sec_text and len(btns) >= 2:
                learn_btn = btns[1]
            elif len(btns) >= 1:
                learn_btn = btns[0]

        if learn_btn and learn_btn.count() > 0:
            print("  [Learn] Opening Learn notes...")
            learn_btn.click()
            page.wait_for_timeout(3500)
            
            page.evaluate("""() => {
                const m = document.querySelector('main');
                if (m) m.scrollTop = m.scrollHeight;
            }""")
            page.wait_for_timeout(1500)
            
            finish_btn = page.locator("button:has-text('finished reading')").first
            if finish_btn.count() > 0 and finish_btn.is_visible():
                print("  [Learn] Clicking 'I\\'ve finished reading'...")
                finish_btn.click()
                page.wait_for_timeout(1500)
                
                go_practice = page.locator("button:has-text('Go to practice')").first
                back_btn = page.locator("button:has-text('Back to lessons')").first
                
                if go_practice.count() > 0 and go_practice.is_visible():
                    print("  [Learn] Clicking 'Go to practice ->'...")
                    go_practice.click()
                    page.wait_for_timeout(3500)
                elif back_btn.count() > 0 and back_btn.is_visible():
                    print("  [Learn] Clicking 'Back to lessons'...")
                    back_btn.click()
                    page.wait_for_timeout(2500)
    except Exception as e:
        print(f"  [Learn] Error: {e}")

def handle_practice_questions(page, extractor, generator, tracker):
    """Answers writing questions or MCQs until practice is officially completed and submitted."""
    step = 0

    while "practice/exam" in page.url and "lessons" not in page.url:
        step += 1
        dismiss_overlays(page)
        page.wait_for_timeout(800)

        # 1. Check for confirmation dialog ("Ready to submit?")
        confirm_submit = page.locator(".cdk-overlay-container button:has-text('Submit')").first
        if confirm_submit.count() > 0 and confirm_submit.is_visible():
            print("  [Confirm] Confirmation 'Ready to submit?' detected -> Submitting!")
            confirm_submit.click()
            page.wait_for_timeout(3500)
            break

        # 2. Check for results / complete screen
        finish_indicator = page.locator("text='Lesson Complete', text='Practice Complete', text='Congratulations', text='Well done', text='Results', text='YOUR SCORE', text='Bravo!', text='Submitted'")
        if finish_indicator.count() > 0 and finish_indicator.first.is_visible():
            print("\n  [Success] Practice completed! Returning to lessons dashboard...")
            done_btn = page.locator("button:has-text('Continue'), button:has-text('Next lesson'), button:has-text('Done'), button:has-text('Back to lessons')").first
            if done_btn.count() > 0 and done_btn.is_visible():
                done_btn.click()
                page.wait_for_timeout(2500)
            break

        # 3. Extract question activity
        activity = extractor.extract_current_question()

        if activity["type"] == "writing":
            prog = activity.get("progress", f"Step {step}")
            clean_prompt = activity['prompt'][:80].encode('ascii', errors='replace').decode('ascii')
            print(f"\n  [Writing {prog}] Scenario: {clean_prompt}...")
            if activity.get("bullets"):
                print(f"  -> Requirements: {len(activity['bullets'])} key points")

            response_text = generator.generate_writing(activity)
            word_count = len(response_text.split())
            print(f"  -> Typing response ({word_count} words)...")

            ta = activity["textarea"]
            ta.scroll_into_view_if_needed()
            ta.click()
            ta.fill("")
            page.wait_for_timeout(200)
            ta.fill(response_text)
            page.wait_for_timeout(1500)

            tracker.record_writing(
                prompt=activity.get("prompt"),
                bullets=activity.get("bullets", []),
                written_response=response_text
            )

            # Advance with Continue (or Submit if present)
            submit_btn = page.locator("button:has-text('Submit')").first
            cont_btn = page.locator("button:has-text('Continue')").first

            if submit_btn.count() > 0 and submit_btn.is_visible() and submit_btn.is_enabled():
                print("  -> Clicking Submit...")
                submit_btn.click()
                page.wait_for_timeout(2000)
            elif cont_btn.count() > 0 and cont_btn.is_visible():
                for _ in range(6):
                    if cont_btn.is_enabled():
                        break
                    time.sleep(0.5)
                print("  -> Clicking Continue to advance...")
                cont_btn.click()
                page.wait_for_timeout(3000)

            # Check if confirmation dialog appeared immediately after Continue
            confirm_submit = page.locator(".cdk-overlay-container button:has-text('Submit')").first
            if confirm_submit.count() > 0 and confirm_submit.is_visible():
                print("  [Confirm] Confirmation 'Ready to submit?' detected -> Submitting!")
                confirm_submit.click()
                page.wait_for_timeout(3500)
                break

        elif activity["type"] == "multiple_choice":
            current_q = activity["question"].encode('ascii', errors='replace').decode('ascii')
            print(f"\n  [MCQ] {current_q}")
            
            solution = generator.solve(
                passage=activity["passage"],
                question=activity["question"],
                options=activity["options"]
            )
            
            chosen_idx = solution["recommended_index"] - 1
            if chosen_idx < 0 or chosen_idx >= len(activity["options"]):
                chosen_idx = 0
            chosen_opt = activity["options"][chosen_idx]
            opt_txt = chosen_opt['text'].encode('ascii', errors='replace').decode('ascii')
            print(f"  -> Selected: [{solution['recommended_index']}] {opt_txt}")

            chosen_opt["element"].scroll_into_view_if_needed()
            chosen_opt["element"].click()
            page.wait_for_timeout(600)

            tracker.record_dry_run(
                question=activity["question"],
                recommended_answer=chosen_opt["text"],
                reasoning=solution["reasoning"]
            )

            check_btn = page.locator("button:has-text('Check')").first
            if check_btn.count() > 0 and check_btn.is_visible():
                print("  -> Clicking Check...")
                check_btn.click()
                page.wait_for_timeout(1000)

            after_cont = page.locator("button.g-btn, button:has-text('Continue')").filter(has_text="Continue")
            if after_cont.count() > 0 and after_cont.first.is_visible():
                print("  -> Advancing with Continue...")
                after_cont.first.click()
                page.wait_for_timeout(1500)

        else:
            time.sleep(1)

        if step >= 10:
            break

def run_writing_course(total_target=30):
    print("=" * 75)
    print(" BHARAT ENGLISH - AUTONOMOUS WRITING COURSE RUNNER (TOPICS 1 & 2 -> 30 LESSONS)")
    print(" Press Ctrl+C in terminal at any time to pause.")
    print("=" * 75)

    browser = BrowserManager(headless=False)
    try:
        page = browser.start()
        extractor = ActivityExtractor(page)
        generator = AnswerGenerator()
        tracker = ProgressTracker()

        ensure_logged_in(page, WRITING_SKILL_URL)

        while True:
            # Step A: Navigate to Writing Skills Overview
            print(f"\n[Nav] Opening Writing Skill Overview: {WRITING_SKILL_URL}")
            page.goto(WRITING_SKILL_URL)
            page.wait_for_timeout(4000)
            dismiss_overlays(page)

            try:
                page.wait_for_selector(".card", timeout=8000)
            except Exception:
                pass

            topic_cards = page.locator(".card").filter(has_text="lessons").all()
            print(f"[Dashboard] Found {len(topic_cards)} Course Topics on your account.")

            if len(topic_cards) == 0:
                print("  [Notice] No course topic cards found. Checking if page requires re-login or refresh...")
                ensure_logged_in(page, WRITING_SKILL_URL)
                topic_cards = page.locator(".card").filter(has_text="lessons").all()
                if len(topic_cards) == 0:
                    print("  [Notice] Still no topic cards found. Retrying in 5 seconds...")
                    page.wait_for_timeout(5000)
                    continue

            active_topic_found = False

            for t_idx, topic in enumerate(topic_cards):
                topic_text = topic.inner_text()
                
                # If topic already 100% completed (15/15), skip it
                if "15 of 15" in topic_text and "100%" in topic_text:
                    print(f"  [Topic {t_idx+1}] ALREADY 100% COMPLETED -> Skipping to next topic!")
                    continue

                active_topic_found = True
                topic_title = topic.locator("h2, h3, div.font-semibold, .card-title, span").first.inner_text() if topic.locator("h2, h3, div.font-semibold, .card-title, span").count() > 0 else f"Topic {t_idx+1}"
                clean_topic_title = topic_title.strip().encode('ascii', errors='replace').decode('ascii')
                print(f"\n========================================================")
                print(f" ENTERING WRITING TOPIC: {clean_topic_title}")
                print(f"========================================================")
                
                start_btn = topic.locator("button, a").filter(has_text="Start")
                cont_btn = topic.locator("button, a").filter(has_text="Continue")
                if start_btn.count() > 0 and start_btn.first.is_visible():
                    start_btn.first.click()
                elif cont_btn.count() > 0 and cont_btn.first.is_visible():
                    cont_btn.first.click()
                else:
                    topic.click()
                page.wait_for_timeout(4000)

                current_topic_url = page.url
                
                # Loop through all lessons of this topic until topic is 100% complete
                while True:
                    dismiss_overlays(page)
                    
                    # If on practice exam page, handle questions immediately
                    if "practice/exam" in page.url and "lessons" not in page.url:
                        handle_practice_questions(page, extractor, generator, tracker)
                        page.goto(current_topic_url)
                        page.wait_for_timeout(4000)

                    # Ensure we are on the lessons dashboard
                    if "lessons" not in page.url:
                        page.goto(current_topic_url)
                        page.wait_for_timeout(4000)

                    # Wait for Angular to render the lesson sections
                    try:
                        page.wait_for_selector("section.card", timeout=12000)
                    except Exception:
                        page.reload()
                        page.wait_for_timeout(4000)

                    sections = page.locator("section.card").all()
                    if not sections:
                        print("  [Wait] Waiting for lessons list to render...")
                        page.wait_for_timeout(3000)
                        sections = page.locator("section.card").all()

                    # Check overall topic completion
                    done_count = sum(1 for sec in sections if "Done" in sec.inner_text() or "View Result" in sec.inner_text())
                    print(f"\n[Topic Status] {done_count} / {len(sections)} lessons completed in this topic.")
                    
                    if len(sections) >= 15 and done_count >= 15:
                        print(f"\n[Success] ALL 15 LESSONS IN TOPIC {t_idx+1} ARE 100% COMPLETED!")
                        break

                    target_sec = None
                    for sec in sections:
                        sec_text = sec.inner_text()
                        
                        # Skip if already completed
                        if "View Result" in sec_text or "Done" in sec_text and ("80%" in sec_text or "100%" in sec_text or "Bravo!" in sec_text or "YOUR SCORE" in sec_text):
                            continue
                            
                        unlock_btn = sec.locator("button:has-text('Unlock Now')")
                        if unlock_btn.count() > 0 and unlock_btn.is_visible():
                            print("  [Unlock] Unlocking next course lesson...")
                            unlock_btn.first.click()
                            page.wait_for_timeout(2000)
                            
                        target_sec = sec
                        break

                    if not target_sec:
                        if done_count >= len(sections) and len(sections) > 0:
                            print(f"\n[Success] All lessons in this topic are 100% complete!")
                            break
                        else:
                            page.reload()
                            page.wait_for_timeout(4000)
                            continue

                    sec_title = target_sec.locator("h2, h3, div.font-semibold").first.inner_text() if target_sec.locator("h2, h3, div.font-semibold").count() > 0 else "Lesson"
                    clean_sec_title = sec_title.encode('ascii', errors='replace').decode('ascii')
                    print(f"\n>>> PROCESSING: {clean_sec_title} <<<")
                    sec_text = target_sec.inner_text()
                    btns = target_sec.locator("button").all()

                    # 1. Video Check
                    has_video = "Watch the video" in sec_text or ("Video" in sec_text and "To do" in sec_text)
                    if has_video:
                        handle_video(page, target_sec)
                        page.wait_for_timeout(2000)
                        sec_text = target_sec.inner_text()
                        btns = target_sec.locator("button").all()

                    # 2. Learn Check
                    has_learn = "Read Learn" in sec_text or ("Learn" in sec_text and "To do" in sec_text)
                    if has_learn:
                        handle_learn(page, target_sec)
                        page.wait_for_timeout(2000)
                        
                        if "practice/exam" in page.url and "lessons" not in page.url:
                            handle_practice_questions(page, extractor, generator, tracker)
                            page.goto(current_topic_url)
                            page.wait_for_timeout(3500)
                            continue

                        sec_text = target_sec.inner_text()
                        btns = target_sec.locator("button").all()

                    # 3. Practice Check
                    practice_btn = target_sec.locator("button:has-text('Practice')").first
                    if practice_btn.count() > 0 and practice_btn.get_attribute("aria-disabled") != "true":
                        print("  [Practice] Opening Practice module...")
                        practice_btn.click()
                        page.wait_for_timeout(4000)
                    elif len(btns) >= 1:
                        last_btn = btns[-1]
                        if last_btn.get_attribute("aria-disabled") != "true":
                            print("  [Practice] Clicking Practice button...")
                            last_btn.click()
                            page.wait_for_timeout(4000)

                    # 4. Answer Practice Questions
                    if "practice/exam" in page.url and "lessons" not in page.url:
                        handle_practice_questions(page, extractor, generator, tracker)
                        page.goto(current_topic_url)
                        page.wait_for_timeout(3500)

                # Continue to next topic! (No premature break)

            if not active_topic_found:
                print("\n" + "="*70)
                print(" ALL 30 LESSONS ACROSS BOTH WRITING TOPICS ARE 100% COMPLETE! ")
                print("="*70)
                break

    except KeyboardInterrupt:
        print("\n[Halt] Stopped by user.")
    except Exception as e:
        print(f"\n[Error] {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    run_writing_course(total_target=30)
