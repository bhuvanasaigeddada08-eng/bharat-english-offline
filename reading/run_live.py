import os
import sys
import time
from browser_manager import BrowserManager
from activity_extractor import ActivityExtractor
from answer_generator import AnswerGenerator
from progress_tracker import ProgressTracker

READING_SKILL_URL = "https://corporate.bharatenglish.org/#/adaptive-learning/skill/Reading"

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
    is_login_page = ("login" in page.url.lower() or 
                     page.locator("button:has-text('Send OTP'), button:has-text('Sign In'), button:has-text('Log In')").count() > 0)

    if is_login_page:
        print("\n" + "=" * 70)
        print(" [ACTION REQUIRED] Please Log In to Bharat English in the Chrome window.")
        print(" (Enter mobile number/OTP or email credentials for you or your friend)")
        print(" Waiting for you to complete login... (Auto-starting after login)")
        print("=" * 70)

        while True:
            page.wait_for_timeout(2000)
            current_url = page.url
            
            # If still on blank page, push to login URL
            if current_url == "about:blank" or not current_url.startswith("http"):
                page.goto(LOGIN_URL)
                page.wait_for_timeout(2500)
                continue

            has_login_btn = page.locator("button:has-text('Send OTP'), button:has-text('Sign In'), button:has-text('Log In')").count() > 0
            if "login" not in current_url.lower() and not has_login_btn:
                print("\n[Success] Login detected! Proceeding to course modules...\n")
                page.wait_for_timeout(2000)
                page.goto(target_url)
                page.wait_for_timeout(4000)
                break

def dismiss_overlays(page):
    """Dismiss any modal guide or informational popup, but handle confirmation dialogs specifically."""
    try:
        overlays = page.locator(".cdk-overlay-container")
        if overlays.count() > 0 and overlays.is_visible():
            # 1. "Reading complete" -> CLICK "Go to practice ->"
            go_practice_btn = page.locator("button:has-text('Go to practice')").first
            if go_practice_btn.count() > 0 and go_practice_btn.is_visible():
                print("  [Dialog] 'Reading complete' dialog -> Clicking 'Go to practice ->'...")
                go_practice_btn.click()
                page.wait_for_timeout(3000)
                return True

            # 2. "Ready to submit?" confirmation dialog -> CLICK SUBMIT!
            submit_dialog_btn = page.locator(".cdk-overlay-container button:has-text('Submit')").first
            if submit_dialog_btn.count() > 0 and submit_dialog_btn.is_visible():
                print("  [Dialog] 'Ready to submit?' dialog detected -> Clicking SUBMIT!")
                submit_dialog_btn.click()
                page.wait_for_timeout(2500)
                return True

            # 3. "Hold It Right There!" alert -> Click Continue Learning
            hold_btn = page.locator("button:has-text('Continue Learning')")
            if hold_btn.count() > 0 and hold_btn.first.is_visible():
                print("  [Dialog] 'Hold It Right There!' detected -> Clicking 'Continue Learning'...")
                hold_btn.first.click()
                page.wait_for_timeout(800)
                return True

            # 4. Informational guides
            skip_btn = page.locator("button:has-text('Skip for now'), button:has-text('Skip guide'), button:has-text('Got it')")
            if skip_btn.count() > 0 and skip_btn.first.is_visible():
                skip_btn.first.click()
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
            page.wait_for_timeout(1800)
            
            close_btn = page.locator("button[aria-label='Close video dialog'], button.close")
            if close_btn.count() > 0 and close_btn.first.is_visible():
                print("  [Video] Closed instantly -> Video Done.")
                close_btn.first.click()
                page.wait_for_timeout(1500)
    except Exception as e:
        print(f"  [Video] Error: {e}")

def handle_learn(page, section):
    """Clicks Learn button, scrolls the <main> container to bottom, and clicks 'Go to practice'."""
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
                
                # Check for "Go to practice ->" or "Back to lessons"
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
    """Answers all questions, clicks Check, clicks Continue, and confirms Submit dialog."""
    q_index = 0
    consecutive_waits = 0
    last_question = ""

    while "practice/exam/" in page.url or "practice/adaptive/" in page.url:
        dismiss_overlays(page)
        page.wait_for_timeout(800)

        # 1. Check for SUBMIT button
        submit_btn = page.locator("button:has-text('Submit'), button:has-text('Finish')").filter(has_text="Submit")
        if submit_btn.count() > 0 and submit_btn.first.is_visible():
            print("\n  [Submit] Found SUBMIT button -> Submitting!")
            submit_btn.first.click()
            page.wait_for_timeout(2000)
            
            confirm_submit = page.locator(".cdk-overlay-container button:has-text('Submit')").first
            if confirm_submit.count() > 0 and confirm_submit.is_visible():
                print("  [Confirm] Confirming 'Ready to submit?' -> Clicked Submit!")
                confirm_submit.click()
                page.wait_for_timeout(3000)
            break

        # 2. Check for results / complete screen
        finish_indicator = page.locator("text='Lesson Complete', text='Practice Complete', text='Congratulations', text='Well done', text='Results', text='YOUR SCORE', text='Bravo!'")
        if finish_indicator.count() > 0 and finish_indicator.first.is_visible():
            print("\n  [Success] Practice completed! Returning to lessons dashboard...")
            done_btn = page.locator("button:has-text('Continue'), button:has-text('Next lesson'), button:has-text('Done'), button:has-text('Back to lessons')")
            if done_btn.count() > 0 and done_btn.first.is_visible():
                done_btn.first.click()
                page.wait_for_timeout(2500)
            break

        # 3. If Continue button is visible after Check/feedback
        cont_btn = page.locator("button.g-btn, button:has-text('Continue')").filter(has_text="Continue")
        if cont_btn.count() > 0 and cont_btn.first.is_visible():
            print("  -> Clicking Continue to advance...")
            cont_btn.first.click()
            page.wait_for_timeout(1200)
            continue

        # 4. Extract question
        activity = extractor.extract_current_question()
        if not activity["question"] or not activity["options"]:
            consecutive_waits += 1
            if consecutive_waits > 6:
                break
            time.sleep(1)
            continue

        consecutive_waits = 0
        current_q = activity["question"]

        if current_q != last_question:
            q_index += 1
            last_question = current_q
            print(f"\n  [Q{q_index}] {current_q}")
            
            solution = generator.solve(
                passage=activity["passage"],
                question=current_q,
                options=activity["options"]
            )
            
            chosen_idx = solution["recommended_index"] - 1
            if chosen_idx < 0 or chosen_idx >= len(activity["options"]):
                chosen_idx = 0
            chosen_opt = activity["options"][chosen_idx]
            print(f"  -> Selected: [{solution['recommended_index']}] {chosen_opt['text']}")
            print(f"  -> Reasoning: {solution['reasoning']}")

            chosen_opt["element"].scroll_into_view_if_needed()
            chosen_opt["element"].click()
            page.wait_for_timeout(600)

            tracker.record_dry_run(
                question=current_q,
                recommended_answer=chosen_opt["text"],
                reasoning=solution["reasoning"]
            )

        # 5. Click Check
        check_btn = page.locator("button:has-text('Check')").first
        if check_btn.count() > 0 and check_btn.is_visible():
            print("  -> Clicking Check...")
            check_btn.click()
            page.wait_for_timeout(1000)

        # 6. Check if Submit or Continue appeared immediately
        submit_after = page.locator("button:has-text('Submit')").first
        if submit_after.count() > 0 and submit_after.is_visible():
            print("  -> Clicking Submit to officially record completion...")
            submit_after.click()
            page.wait_for_timeout(1500)
            
            confirm_submit = page.locator(".cdk-overlay-container button:has-text('Submit')").first
            if confirm_submit.count() > 0 and confirm_submit.is_visible():
                print("  [Confirm] Confirming 'Ready to submit?' -> Clicked Submit!")
                confirm_submit.click()
                page.wait_for_timeout(3000)
            break

        after_cont = page.locator("button.g-btn, button:has-text('Continue')").filter(has_text="Continue")
        if after_cont.count() > 0 and after_cont.first.is_visible():
            print("  -> Advancing with Continue...")
            after_cont.first.click()
            page.wait_for_timeout(1200)

        if q_index >= 12:
            break

def run_reading_course(total_target=30):
    print("=" * 75)
    print(" BHARAT ENGLISH - DUAL-TOPIC AUTONOMOUS RUNNER (TOPICS 1 & 2 -> 30 LESSONS)")
    print(" Press Ctrl+C in terminal at any time to pause.")
    print("=" * 75)

    browser = BrowserManager(headless=False)
    try:
        page = browser.start()
        extractor = ActivityExtractor(page)
        generator = AnswerGenerator()
        tracker = ProgressTracker()

        ensure_logged_in(page, READING_SKILL_URL)

        while True:
            # Step A: Navigate to Reading Skills Overview to see all Course Topics
            print(f"\n[Nav] Opening Reading Skill Overview: {READING_SKILL_URL}")
            page.goto(READING_SKILL_URL)
            page.wait_for_timeout(4000)
            dismiss_overlays(page)

            try:
                page.wait_for_selector(".card", timeout=8000)
            except Exception:
                pass

            topic_cards = page.locator(".card, div[class*='card']").filter(has_text=re.compile(r'lesson|subtopic|topic|start|continue', re.I)).all()
            if len(topic_cards) == 0:
                topic_cards = page.locator(".card").all()
            print(f"[Dashboard] Found {len(topic_cards)} Course Topics on your account.")

            if len(topic_cards) == 0:
                print("  [Notice] No course topic cards found. Checking if page requires re-login or refresh...")
                ensure_logged_in(page, READING_SKILL_URL)
                topic_cards = page.locator(".card, div[class*='card']").filter(has_text=re.compile(r'lesson|subtopic|topic|start|continue', re.I)).all()
                if len(topic_cards) == 0:
                    topic_cards = page.locator(".card").all()
                if len(topic_cards) == 0:
                    print("  [Notice] Still no topic cards found. Retrying in 5 seconds...")
                    page.wait_for_timeout(5000)
                    continue

            active_topic_found = False

            for t_idx, topic in enumerate(topic_cards):
                topic_text = topic.inner_text()
                
                # If topic already 100% completed, skip it
                if "15 of 15" in topic_text and "100%" in topic_text:
                    print(f"  [Topic {t_idx+1}] ALREADY 100% COMPLETED -> Skipping to next topic!")
                    continue

                active_topic_found = True
                topic_title = topic.locator("h2, h3, div.font-semibold, .card-title, span").first.inner_text() if topic.locator("h2, h3, div.font-semibold, .card-title, span").count() > 0 else f"Topic {t_idx+1}"
                print(f"\n========================================================")
                print(f" ENTERING COURSE TOPIC: {topic_title.strip()}")
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
                
                # Loop through all 15 lessons of this topic
                while True:
                    dismiss_overlays(page)
                    
                    # If directly in practice, answer questions
                    if "practice/exam/" in page.url or "practice/adaptive/" in page.url:
                        handle_practice_questions(page, extractor, generator, tracker)
                        page.goto(current_topic_url)
                        page.wait_for_timeout(3500)

                    if "lessons" not in page.url and "practice/exam" not in page.url:
                        page.goto(current_topic_url)
                        page.wait_for_timeout(3500)

                    sections = page.locator("section.card").all()
                    target_sec = None

                    for sec in sections:
                        sec_text = sec.inner_text()
                        
                        if "View Result" in sec_text or "Done" in sec_text and ("80%" in sec_text or "100%" in sec_text or "Bravo!" in sec_text):
                            continue
                            
                        unlock_btn = sec.locator("button:has-text('Unlock Now')")
                        if unlock_btn.count() > 0 and unlock_btn.first.is_visible():
                            print("  [Unlock] Unlocking next course lesson...")
                            unlock_btn.first.click()
                            page.wait_for_timeout(2000)
                            
                        target_sec = sec
                        break

                    if not target_sec:
                        print(f"\n[Success] All 15 lessons in this topic are 100% completed!")
                        break

                    sec_title = target_sec.locator("h2, h3, div.font-semibold").first.inner_text() if target_sec.locator("h2, h3, div.font-semibold").count() > 0 else "Lesson"
                    print(f"\n>>> PROCESSING: {sec_title} <<<")
                    sec_text = target_sec.inner_text()
                    btns = target_sec.locator("button").all()

                    # 1. Video Check: Only do video if "Watch the video" or "Video To do" is present
                    has_video = "Watch the video" in sec_text or ("Video" in sec_text and "To do" in sec_text)
                    if has_video:
                        handle_video(page, target_sec)
                        page.wait_for_timeout(2000)
                        sec_text = target_sec.inner_text()
                        btns = target_sec.locator("button").all()

                    # 2. Learn Check: If Learn is pending
                    has_learn = "Read Learn" in sec_text or ("Learn" in sec_text and "To do" in sec_text)
                    if has_learn:
                        handle_learn(page, target_sec)
                        page.wait_for_timeout(2000)
                        
                        # If handle_learn navigated directly into practice, handle questions immediately!
                        if "practice/exam/" in page.url or "practice/adaptive/" in page.url:
                            handle_practice_questions(page, extractor, generator, tracker)
                            page.goto(current_topic_url)
                            page.wait_for_timeout(3500)
                            continue

                        sec_text = target_sec.inner_text()
                        btns = target_sec.locator("button").all()

                    # 3. Practice Check: Open practice
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
                    if "practice/exam/" in page.url or "practice/adaptive/" in page.url:
                        handle_practice_questions(page, extractor, generator, tracker)
                        page.goto(current_topic_url)
                        page.wait_for_timeout(3500)

                break

            if not active_topic_found:
                print("\n" + "="*70)
                print(" ALL 30 LESSONS ACROSS BOTH TOPICS ARE 100% COMPLETE! ")
                print("="*70)
                break

    except KeyboardInterrupt:
        print("\n[Halt] Stopped by user.")
    except Exception as e:
        print(f"\n[Error] {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    run_reading_course(total_target=30)
