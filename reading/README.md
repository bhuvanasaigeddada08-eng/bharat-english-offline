# Bharat English Reading Practice Assistant (Dry-Run Prototype)

A modular, local browser-automation assistant built with Python and Playwright for the **Reading** practice modules on Bharat English (`corporate.bharatenglish.org`).

---

## 1. Inspection Findings & Structure

The platform uses an Angular SPA architecture (`bet-apps-root`, `bet-learn-test`, `bet-lessons`) with client-side routing and token-based state stored in local persistent storage.

### Reading Hierarchy
1. **Course Level**: `/#/adaptive-learning/skill/Reading`
2. **Topic Level**: e.g., `01. Reading Company Policies`
3. **Lesson Units**: `01. Identifying Key Rules in an Employee Handbook`
   - **Step 1**: Video (interactive guide / primer)
   - **Step 2**: Learn notes (reading passage, guidelines, and vocabulary)
   - **Step 3**: Practice exercises (5 untimed practice questions per lesson with instant feedback)

### Real Locators Observed
- **Informational Guides/Modals**: `.cdk-overlay-container` (dismissible via `button:has-text('Skip for now')` or `'Skip guide'`).
- **Passage Container**: `div.text-sm.text-base-content.leading-relaxed`.
- **Question Header**: `div[role='radiogroup']` preceding sibling element or `.!text-base.font-medium.text-base-content`.
- **Progress Counter**: `span.font-medium.shrink-0:has-text('/')` (e.g., `(0/5)`).
- **Multiple Choice Radio Options**: `div[role='radiogroup'] div[role='radio']` with labels inside `span.flex-1`.
- **Action Buttons**:
  - `button:has-text('Check')` (`btn btn-primary rounded-full min-w-[120px]`)
  - `button:has-text('Skip')` (`btn bg-base-100 border border-primary text-primary`)

---

## 2. Architecture & Modular Layout

```
reading/
├── .browser_profile/     # Persistent browser session storage (kept in .gitignore)
├── .env.example          # Environment variables template
├── .gitignore            # Excludes credentials, profiles, sessions, and logs
├── browser_manager.py    # Manages Playwright lifecycle with session persistence
├── activity_extractor.py # DOM parsing for passages, questions, progress, and options
├── answer_generator.py   # Solution engine (heuristics / Gemini LLM API)
├── progress_tracker.py   # Local JSON history logging for dry-runs
├── main.py               # Main CLI runner in dry-run mode
└── README.md             # Documentation and usage guide
```

---

## 3. Setup and Execution

### Prerequisites
- Python 3.10+
- Playwright (`python -m pip install playwright && python -m playwright install chromium`)

### Quick Start (Dry-Run)
Run the dry-run script to inspect the active activity, extract questions/options, and generate proposed solutions without submitting answers:

```bash
python main.py
```

### Stopping the Agent
- You can stop the runner at any moment by pressing **`Ctrl + C`** in your terminal.
- The manager gracefully closes the browser context and releases all locks cleanly.

---

## 4. Safety & Compliance Controls
- **Dry-Run Mode Active**: The `main.py` runner only reads the DOM and logs proposed answers locally to `reading_progress.json`. It will never click `Check` or `Skip`.
- **No Hardcoded Credentials**: Passwords, OTPs, and authentication tokens are never recorded in code. Session state is kept strictly in local storage directories ignored by `.gitignore`.
- **Failure Halting**: Unknown activity types, modal dialogs, expired logins, or DOM changes cleanly halt execution rather than making blind submissions.

