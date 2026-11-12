# Bharat English Autonomous Suite (100% Offline AI Edition)

An autonomous, offline-first desktop suite built with Python, Playwright, and local Ollama LLMs to run and complete **Listening**, **Reading**, and **Writing** course modules on the Bharat English platform (`corporate.bharatenglish.org`).

---

## 🌟 Key Features

- **100% Offline AI Engine**: Powered by your local [Ollama](https://ollama.com) models (`qwen2.5-coder:1.5b`, `gemma3:4b`, `llama3.2`, etc.) with zero internet API dependency and no paid API keys.
- **Unified Graphical Launcher (`launcher.py`)**: A modern desktop control panel to trigger individual modules or the full course with real-time logs and stop controls.
- **Smart Login Detection**: Automatically detects if you need to log in, pauses and prompts you in the terminal, saves your cookies to `.browser_profile`, and automatically proceeds once you are logged in.
- **Autonomous Multi-Stage Execution**:
  - **Video**: Automatically clears the prerequisite primer.
  - **Learn**: Automatically scrolls the reading container to unlock the practice button.
  - **Practice**: Intercepts questions and explanations, queries local Ollama, selects the 100% correct options, and clicks Submit.
  - **Writing**: Generates rubric-compliant emails matching the target word count and scenarios.
  - **Auto-Unlock**: Automatically clicks *Unlock Now* to advance through all 30 lessons across Topic 1 & Topic 2.

---

## 📂 Project Architecture

```
offline Ai Bet Extenstion - Copy/
├── launcher.py               # Modern Graphical Desktop Launcher
├── start_launcher.bat        # 1-Click GUI Launcher for Windows
├── run_full_course.py        # Sequential Runner: Listening (30) -> Reading (30) -> Writing (30)
├── start_full_course.bat     # 1-Click Sequential Pipeline Runner
├── listening/                # Listening module (Topics 1 & 2 -> 30 Lessons)
│   ├── run_live.py
│   ├── answer_generator.py   # Offline Ollama + transcript matching
│   └── start_live_listening.bat
├── reading/                  # Reading module (Topics 1 & 2 -> 30 Lessons)
│   ├── run_live.py
│   ├── answer_generator.py   # Offline Ollama + passage matching
│   └── start_live_reading.bat
├── writing ow1/              # Writing module (Topics 1 & 2 -> 30 Lessons)
│   ├── run_live.py
│   ├── answer_generator.py   # Offline Ollama email generator + synthesis
│   └── start_live_writing.bat
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+** installed on Windows.
- **Ollama** installed and running locally with at least one model:
  ```bash
  ollama run qwen2.5-coder:1.5b
  # or
  ollama run gemma3:4b
  ```
- **Install Python Dependencies**:
  ```bash
  pip install playwright python-dotenv
  playwright install chromium
  ```

---

## 🎮 How to Run

### Option 1: Desktop GUI Launcher (Recommended)
Double-click **`start_launcher.bat`** (or run `python launcher.py`):
- Click **⚡ Run All 3 (Full Course)** to run everything end-to-end.
- Or select **🎧 Listening (30)**, **📖 Reading (30)**, or **✍️ Writing (30)** individually.

### Option 2: Sequential Command-Line Runner
Double-click **`start_full_course.bat`**:
Runs Listening (30 lessons), then Reading (30 lessons), then Writing (30 lessons) in sequence.

---

## 🔐 Login Flow
1. On first run, Chrome will launch.
2. If you are not logged in, the runner will notify you:
   `[ACTION REQUIRED] Please Log In to Bharat English in the Chrome window.`
3. Enter your credentials and sign in.
4. The runner will detect your login immediately, save the session, and start the lessons automatically!
