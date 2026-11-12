# Bharat English Listening Course Autonomous Runner

A modular, automated browser assistant built with Python and Playwright for the **Listening** modules on Bharat English (`corporate.bharatenglish.org`).

---

## 1. Course Architecture & Structure

### Listening Hierarchy
1. **Course Level**: `/#/adaptive-learning/skill/Listening`
2. **Topic 1**: `01. Scheduling Meetings` (15 lessons)
3. **Topic 2**: `02. Email Follow-ups` (15 lessons)
4. **Lesson Units**:
   - **Step 1**: Video (interactive guide / primer)
   - **Step 2**: Learn notes (listening guidelines, transcript excerpts, key phrases)
   - **Step 3**: Practice exercises (audio-based multiple-choice comprehension questions)

---

## 2. Directory Layout

```
listening/
├── .browser_profile/     # Persistent browser session storage (kept in .gitignore)
├── .env                  # API key configuration (GEMINI_API_KEY)
├── activity_extractor.py # DOM parsing for questions, radio options, and progress counters
├── answer_generator.py   # Solution engine (API Transcript Interception + Gemini 3.5)
├── browser_manager.py    # Manages Playwright lifecycle with session persistence
├── check_progress.py     # Inspects current progress across topics and lessons
├── progress_tracker.py   # Local JSON history logging (listening_progress.json)
├── run_live.py           # Full autonomous runner across Topics 1 & 2 (30 lessons)
├── start_live_listening.bat # One-click Windows batch runner for Listening
└── README.md             # Documentation and usage guide
```

---

## 3. How to Run

Double-click **`start_live_listening.bat`** or run in terminal:

```bash
python run_live.py
```

To check current progress without running lessons:
```bash
python check_progress.py
```

### Stopping the Agent
- Press **`Ctrl + C`** in your command window at any time to pause or stop.

