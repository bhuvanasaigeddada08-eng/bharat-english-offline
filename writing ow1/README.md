# Bharat English Writing Course Autonomous Runner

A modular, automated browser assistant built with Python and Playwright for the **Writing** modules on Bharat English (`corporate.bharatenglish.org`).

---

## 1. Course Architecture & Structure

The platform uses an Angular SPA architecture (`bet-apps-root`, `bet-learn-test`, `bet-lessons`) with client-side routing and token-based state stored in local persistent storage.

### Writing Hierarchy
1. **Course Level**: `/#/adaptive-learning/skill/Writing`
2. **Topic 1**: `01. Writing Follow-Up Emails` (15 lessons)
3. **Topic 2**: `02. Summarizing Workplace Tasks` (15 lessons)
4. **Lesson Units**:
   - **Step 1**: Video (interactive guide / primer)
   - **Step 2**: Learn notes (writing guidelines, samples, key vocabulary)
   - **Step 3**: Practice exercises (written responses or multiple-choice questions)

---

## 2. Directory Layout

```
writing ow1/
├── .browser_profile/     # Persistent browser session storage (kept in .gitignore)
├── .env                  # API key configuration (GEMINI_API_KEY)
├── .gitignore            # Excludes credentials, profiles, sessions, and logs
├── activity_extractor.py # DOM parsing for writing prompts, requirements, word targets, textareas
├── answer_generator.py   # Solution engine (Gemini AI + Contextual Rule-Based Synthesizer)
├── browser_manager.py    # Manages Playwright lifecycle with session persistence
├── check_progress.py     # Inspects current progress across topics and lessons
├── progress_tracker.py   # Local JSON history logging (writing_progress.json)
├── run_live.py           # Full autonomous runner across Topics 1 & 2 (30 lessons)
├── start_live_writing.bat# One-click Windows batch runner for Writing
└── README.md             # Documentation and usage guide
```

---

## 3. How to Run

Double-click **`start_live_writing.bat`** or run in terminal:

```bash
python run_live.py
```

To check current progress without running lessons:
```bash
python check_progress.py
```

### Stopping the Agent
- Press **`Ctrl + C`** in your command window at any time to pause or stop.
