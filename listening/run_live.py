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

LISTENING_SKILL_URL = "https://corporate.bharatenglish.org/#/adaptive-learning/skill/Listening"

def ensure_logged_in(page, target_url):
    """Checks if the user needs to log in, prompts in terminal, and waits until logged in."""
    print(f"[Nav] Checking login state at: {target_url}")
    page.goto(target_url)
    page.wait_for_timeout(3500)
    
    is_login_page = ("login" in page.url or 
                     page.locator("input[type='password']").count() > 0 or 
                     page.locator("button:has-text('Sign In'), button:has-text('Log In'), button:has-text('Login')").count() > 0)
    
    if is_login_page:
        print("\n" + "=" * 70)
        print(" [ACTION REQUIRED] Please Log In to Bharat English in the Chrome window.")
        print(" Waiting for you to complete login... (Session will be saved)")
        print("=" * 70)
        
        while True:
            page.wait_for_timeout(3000)
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

            # 4. Informational guides
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

def handle_practice_questions(page, extractor, generator, tracker, exam_db):
    """Solves and submits listening practice questions using transcript context and Gemini."""
    q_index = 0
    consecutive_waits = 0
    last_question = ""

    while "practice/exam" in page.url and "lessons" not in page.url:
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
        finish_indicator = page.locator("text='Lesson Complete', text='Practice Complete', text='Congratulations', text='Well done', text='Results', text='YOUR SCORE', text='Bravo!', text='Submitted'")
        if finish_indicator.count() > 0 and finish_indicator.first.is_visible():
            print("\n  [Success] Practice completed! Returning to lessons dashboard...")
            done_btn = page.locator("button:has-text('Continue'), button:has-text('Next lesson'), button:has-text('Done'), button:has-text('Back to lessons')").first
            if done_btn.count() > 0 and done_btn.is_visible():
                done_btn.click()
                page.wait_for_timeout(2500)
            break

        # 3. If Continue button is already visible after feedback
        cont_btn = page.locator("button.g-btn, button:has-text('Continue')").filter(has_text="Continue")
        if cont_btn.count() > 0 and cont_btn.first.is_visible() and cont_btn.first.is_enabled():
            print("  -> Advancing with Continue...")
            cont_btn.first.click()
            page.wait_for_timeout(1200)
            continue

        # 4. Extract Question and Options
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
            print(f"\n  [Q{q_index} {activity['progress']}] {current_q}")

            # Lookup intercepted explanation if available
            explanation = ""
            for k, val in exam_db.items():
                if k.lower() in current_q.lower() or current_q.lower() in k.lower():
                    explanation = val.get("explanation", "")
                    break

            if explanation:
                print(f"  [Context] Found transcript explanation for question.")

            solution = generator.solve(
                question=current_q,
                options=activity["options"],
                explanation=explanation
            )

            chosen_idx = solution["recommended_index"] - 1
            if chosen_idx < 0 or chosen_idx >= len(activity["options"]):
                chosen_idx = 0
            chosen_opt = activity["options"][chosen_idx]
            print(f"  -> Selected: [{solution['recommended_index']}] {chosen_opt['text']}")
            if solution.get("reasoning"):
                print(f"  -> Reasoning: {solution['reasoning']}")

            chosen_opt["element"].scroll_into_view_if_needed()
            chosen_opt["element"].click()
            page.wait_for_timeout(600)

            tracker.record_question(
                question=current_q,
                selected_option=chosen_opt["text"],
                reasoning=solution.get("reasoning")
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

def run_listening_course(total_target=30):
    print("=" * 75)
    print(" BHARAT ENGLISH - AUTONOMOUS LISTENING COURSE RUNNER (TOPICS 1 & 2 -> 30 LESSONS)")
    print(" Press Ctrl+C in terminal at any time to pause.")
    print("=" * 75)

    browser = BrowserManager(headless=False)
    exam_db = {}

    def on_response(response):
        if "questions" in response.url and "api" in response.url:
            try:
                data = response.json()
                if "test_definition_section" in data:
                    sections = data["test_definition_section"]
                    for s in sections:
                        for q in s.get("questions", []):
                            q_txt = q.get("question", "").strip()
                            exp = q.get("explanation", "").strip()
                            amcq = q.get("amcq") or {}
                            opts = [amcq.get(f"option{k}") for k in range(1, 5) if amcq.get(f"option{k}")]
                            exam_db[q_txt] = {
                                "explanation": exp,
                                "options": opts
                            }
            except Exception:
                pass

    try:
        page = browser.start()
        page.on("response", on_response)
        extractor = ActivityExtractor(page)
        generator = AnswerGenerator()
        tracker = ProgressTracker()

        ensure_logged_in(page, LISTENING_SKILL_URL)

        while True:
            # Step A: Navigate to Listening Skills Overview
            print(f"\n[Nav] Opening Listening Skill Overview: {LISTENING_SKILL_URL}")
            page.goto(LISTENING_SKILL_URL)
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
                ensure_logged_in(page, LISTENING_SKILL_URL)
                topic_cards = page.locator(".card").filter(has_text="lessons").all()
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
                clean_title = topic_title.strip().encode('ascii', errors='replace').decode('ascii')
                print(f"\n========================================================")
                print(f" ENTERING LISTENING TOPIC: {clean_title}")
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
                    
                    if "practice/exam" in page.url and "lessons" not in page.url:
                        handle_practice_questions(page, extractor, generator, tracker, exam_db)
                        page.goto(current_topic_url)
                        page.wait_for_timeout(4000)

                    if "lessons" not in page.url:
                        page.goto(current_topic_url)
                        page.wait_for_timeout(4000)

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

                    done_count = sum(1 for sec in sections if "Done" in sec.inner_text() or "View Result" in sec.inner_text())
                    print(f"\n[Topic Status] {done_count} / {len(sections)} lessons completed in this topic.")

                    if len(sections) >= 15 and done_count >= 15:
                        print(f"\n[Success] ALL 15 LESSONS IN TOPIC {t_idx+1} ARE 100% COMPLETED!")
                        break

                    target_sec = None
                    for sec in sections:
                        sec_text = sec.inner_text()
                        
                        if "View Result" in sec_text or "Done" in sec_text and ("80%" in sec_text or "100%" in sec_text or "Bravo!" in sec_text or "YOUR SCORE" in sec_text):
                            continue
                            
                        unlock_btn = sec.locator("button:has-text('Unlock Now')")
                        if unlock_btn.count() > 0 and unlock_btn.first.is_visible():
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
                            handle_practice_questions(page, extractor, generator, tracker, exam_db)
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
                        handle_practice_questions(page, extractor, generator, tracker, exam_db)
                        page.goto(current_topic_url)
                        page.wait_for_timeout(3500)

                # Advances to next topic automatically

            if not active_topic_found:
                print("\n" + "="*70)
                print(" ALL 30 LESSONS ACROSS BOTH LISTENING TOPICS ARE 100% COMPLETE! ")
                print("="*70)
                break

    except KeyboardInterrupt:
        print("\n[Halt] Stopped by user.")
    except Exception as e:
        print(f"\n[Error] {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    run_listening_course(total_target=30)

