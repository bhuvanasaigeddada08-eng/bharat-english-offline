import os
import sys
import json
import time
import shutil
import threading
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, ".active_session")
PORT = 8765

try:
    import ctypes
    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    half_w = screen_w // 2
except Exception:
    screen_w = 1920
    screen_h = 1080
    half_w = 960

# Global State
state = {
    "status": "Ready",
    "engine": "ollama", # "ollama" or "gemini"
    "active_skill": "None",
    "topic": "None",
    "lesson": 0,
    "total_lessons": 30,
    "current_question": "Click a module above to launch Chrome on the right side.",
    "options": [],
    "selected_option": "",
    "ai_reasoning": "Ollama / Gemini reasoning will display here in real-time.",
    "logs": []
}

active_runner_process = None
active_runner_thread = None
sse_clients = []
clients_lock = threading.Lock()

def broadcast_event(event_type: str, data: dict):
    payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode("utf-8")
    with clients_lock:
        to_remove = []
        for client in sse_clients:
            try:
                client.wfile.write(payload)
                client.wfile.flush()
            except Exception:
                to_remove.append(client)
        for dead in to_remove:
            if dead in sse_clients:
                sse_clients.remove(dead)

def append_log(message: str):
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    state["logs"].append(formatted)
    if len(state["logs"]) > 250:
        state["logs"].pop(0)
    broadcast_event("log", {"line": formatted})

def update_ai_state(data: dict):
    state.update(data)
    broadcast_event("ai_state", state)

# HTML / CSS / JS matching PixelCraft Design with 100% fidelity
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BharatCraft • Autonomous Desktop Platform</title>
  <style>
    :root {
      --bg-main: #0a0e17;
      --bg-card: #121824;
      --bg-card-subtle: #162032;
      --border-blue: rgba(0, 242, 254, 0.2);
      --border-card: #1f2b42;
      --accent-cyan: #00f2fe;
      --accent-blue: #4facfe;
      --accent-green: #38ef7d;
      --accent-pink: #f38ba8;
      --accent-yellow: #f9e2af;
      --text-white: #ffffff;
      --text-muted: #8e9bb0;
      --gradient-cyan: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
      --gradient-card: linear-gradient(180deg, #121824 0%, #0d121c 100%);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body {
      background: var(--bg-main);
      color: var(--text-white);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      user-select: none;
    }

    /* Top App Header (PixelCraft Styled) */
    .app-header {
      height: 60px;
      padding: 0 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border-card);
      background: rgba(10, 14, 23, 0.95);
    }
    .header-logo-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .logo-badge {
      width: 36px;
      height: 36px;
      background: var(--gradient-cyan);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 15px rgba(0, 242, 254, 0.4);
      font-size: 18px;
    }
    .title-group { display: flex; flex-direction: column; }
    .title-row { display: flex; align-items: center; gap: 8px; }
    .app-title { font-size: 16px; font-weight: 700; color: #fff; letter-spacing: 0.5px; }
    .badge-pill {
      font-size: 10px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 12px;
      background: rgba(56, 239, 125, 0.15);
      color: var(--accent-green);
      border: 1px solid rgba(56, 239, 125, 0.3);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .app-desc { font-size: 11px; color: var(--text-muted); margin-top: 1px; }

    /* Main Container */
    .main-container {
      display: flex;
      flex: 1;
      height: calc(100vh - 60px);
      padding: 16px;
      gap: 16px;
    }

    /* Left Control Column (38%) */
    .left-column {
      width: 44%;
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow-y: auto;
      padding-right: 4px;
    }
    .left-column::-webkit-scrollbar { width: 5px; }
    .left-column::-webkit-scrollbar-thumb { background: #1f2b42; border-radius: 3px; }

    /* PixelCraft Card Base */
    .card-panel {
      background: var(--gradient-card);
      border: 1px solid var(--border-card);
      border-radius: 12px;
      padding: 14px 16px;
      position: relative;
    }

    .panel-header {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.8px;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }
    .panel-header-icon { display: flex; align-items: center; gap: 6px; }

    /* Engine Tabs */
    .engine-tabs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 12px;
    }
    .tab-btn {
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--border-card);
      background: var(--bg-card-subtle);
      color: var(--text-muted);
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .tab-btn.active {
      border-color: var(--accent-cyan);
      background: rgba(0, 242, 254, 0.1);
      color: var(--accent-cyan);
      box-shadow: 0 0 10px rgba(0, 242, 254, 0.15);
    }

    /* Action Buttons (PixelCraft Style) */
    .preset-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 12px;
    }
    .btn-preset {
      padding: 10px 12px;
      background: var(--bg-card-subtle);
      border: 1px solid var(--border-card);
      border-radius: 8px;
      color: #fff;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 2px;
      transition: all 0.2s;
    }
    .btn-preset:hover {
      border-color: var(--accent-cyan);
      background: rgba(0, 242, 254, 0.08);
      transform: translateY(-1px);
    }
    .btn-preset.primary {
      grid-column: span 2;
      background: var(--gradient-cyan);
      color: #000;
      border: none;
      font-weight: 700;
      box-shadow: 0 0 15px rgba(0, 242, 254, 0.3);
    }
    .btn-preset.primary:hover { opacity: 0.95; transform: translateY(-1px); }
    .btn-title { font-size: 12px; font-weight: 700; }
    .btn-sub { font-size: 10px; opacity: 0.7; }

    /* Account Bar */
    .friend-box {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 12px;
      background: rgba(243, 139, 168, 0.08);
      border: 1px dashed rgba(243, 139, 168, 0.3);
      border-radius: 8px;
      margin-bottom: 12px;
    }
    .friend-btn {
      background: var(--accent-pink);
      color: #111;
      border: none;
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }

    /* Live Progress Bar */
    .progress-box {
      margin-top: 4px;
    }
    .progress-track {
      width: 100%;
      height: 8px;
      background: #0d121c;
      border-radius: 4px;
      overflow: hidden;
      margin: 8px 0 4px;
      border: 1px solid var(--border-card);
    }
    .progress-bar {
      width: 0%;
      height: 100%;
      background: var(--gradient-cyan);
      transition: width 0.3s;
    }

    /* Question & Reasoning Area */
    .ai-card {
      background: #0d121c;
      border: 1px solid var(--border-card);
      border-radius: 8px;
      padding: 10px 12px;
      margin-top: 8px;
    }
    .q-text { font-size: 12px; color: #fff; line-height: 1.4; margin-bottom: 6px; }
    .reason-box { font-size: 11px; color: var(--accent-cyan); font-style: italic; line-height: 1.4; }

    /* Bottom Terminal */
    .term-box {
      height: 140px;
      background: #0d121c;
      border: 1px solid var(--border-card);
      border-radius: 8px;
      padding: 8px 10px;
      font-family: Consolas, monospace;
      font-size: 11px;
      color: var(--accent-green);
      overflow-y: auto;
      line-height: 1.4;
    }

    /* Right Column (Workspace / Live Chrome Preview - 56%) */
    .right-column {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .preview-container {
      flex: 1;
      background: var(--gradient-card);
      border: 2px dashed rgba(0, 242, 254, 0.3);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
      box-shadow: inset 0 0 40px rgba(0, 0, 0, 0.6);
    }

    .preview-center {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap: 14px;
      max-width: 480px;
    }
    .glow-icon {
      width: 70px;
      height: 70px;
      border-radius: 50%;
      background: rgba(0, 242, 254, 0.1);
      border: 2px solid var(--accent-cyan);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
      box-shadow: 0 0 25px rgba(0, 242, 254, 0.3);
    }
    .preview-heading { font-size: 20px; font-weight: 700; color: #fff; }
    .preview-subtext { font-size: 13px; color: var(--text-muted); line-height: 1.5; }
    .pill-tags { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 4px; }
    .pill-tag {
      font-size: 11px;
      background: var(--bg-card-subtle);
      border: 1px solid var(--border-card);
      padding: 4px 10px;
      border-radius: 6px;
      color: var(--text-muted);
    }

    .active-chrome-screen {
      width: 100%;
      height: 100%;
      display: none;
      flex-direction: column;
    }
    .chrome-url-bar {
      height: 40px;
      background: #121824;
      border-bottom: 1px solid var(--border-card);
      display: flex;
      align-items: center;
      padding: 0 16px;
      gap: 12px;
    }
    .url-input {
      flex: 1;
      background: #0a0e17;
      border: 1px solid var(--border-card);
      border-radius: 6px;
      padding: 5px 12px;
      font-size: 11px;
      color: var(--text-muted);
      font-family: monospace;
    }
    .chrome-canvas-wrap {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #000;
    }
    #liveCanvas {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }
  </style>
</head>
<body>

  <!-- Top Header -->
  <div class="app-header">
    <div class="header-logo-group">
      <div class="logo-badge">⚡</div>
      <div class="title-group">
        <div class="title-row">
          <span class="app-title">BharatCraft Autonomous Suite</span>
          <span class="badge-pill" id="headerBadge">● 100% Offline Ollama + Gemini Ready</span>
        </div>
        <span class="app-desc">Side-by-side Chrome automation & 100% accuracy solver for Bharat English</span>
      </div>
    </div>
    <div>
      <button onclick="triggerAction('stop')" style="background: rgba(243, 139, 168, 0.2); border: 1px solid var(--accent-pink); color: var(--accent-pink); padding: 6px 14px; border-radius: 6px; font-weight: 700; font-size: 11px; cursor: pointer;">⏹ Stop Runner</button>
    </div>
  </div>

  <!-- Main Container -->
  <div class="main-container">

    <!-- Left Controls Panel -->
    <div class="left-column">
      
      <!-- Panel 1: Presets & Engine -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-header-icon">⚙️ AI ENGINE & COURSE PRESETS</div>
          <span id="statusIndicator" style="color: var(--accent-cyan); font-size: 10px;">IDLE</span>
        </div>

        <!-- Engine Mode Switcher -->
        <div class="engine-tabs">
          <button class="tab-btn active" id="tabOllama" onclick="selectEngine('ollama')">
            <span>🧠 Local Ollama (Offline)</span>
          </button>
          <button class="tab-btn" id="tabGemini" onclick="selectEngine('gemini')">
            <span>🌐 Google Gemini (Online)</span>
          </button>
        </div>

        <!-- Friend Switcher -->
        <div class="friend-box">
          <span style="font-size: 11px; color: #fff;">Helping a Friend?</span>
          <button class="friend-btn" onclick="triggerAction('new_friend')">👤 New Friend Login</button>
        </div>

        <!-- Course Run Presets -->
        <div class="preset-grid">
          <button class="btn-preset primary" onclick="triggerAction('start', 'full')">
            <span class="btn-title">⚡ Run Full Course (All 3 Skills • 90 Lessons)</span>
            <span class="btn-sub">Listening (30) ➔ Reading (30) ➔ Writing (30) End-to-End</span>
          </button>
          <button class="btn-preset" onclick="triggerAction('start', 'listening')">
            <span class="btn-title">🎧 Listening (30)</span>
            <span class="btn-sub">Topics 1 & 2 • Audio MCQ</span>
          </button>
          <button class="btn-preset" onclick="triggerAction('start', 'reading')">
            <span class="btn-title">📖 Reading (30)</span>
            <span class="btn-sub">Topics 1 & 2 • Passages</span>
          </button>
          <button class="btn-preset" style="grid-column: span 2;" onclick="triggerAction('start', 'writing')">
            <span class="btn-title">✍️ Writing Module (30 Lessons)</span>
            <span class="btn-sub">Email Responses • 100% Rubric & Word Count</span>
          </button>
        </div>
      </div>

      <!-- Panel 2: Live AI Solver Inspector -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-header-icon">📋 LIVE QUESTION & REASONING</div>
          <span id="progressText" style="color: var(--accent-green); font-size: 11px;">0 / 30</span>
        </div>

        <div class="progress-box">
          <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted);">
            <span id="topicName">Waiting to begin...</span>
            <span id="pctText">0%</span>
          </div>
          <div class="progress-track">
            <div class="progress-bar" id="progressBar"></div>
          </div>
        </div>

        <div class="ai-card">
          <div style="font-size: 10px; color: var(--text-muted); font-weight: 700; margin-bottom: 4px;">CURRENT QUESTION:</div>
          <div id="qText" class="q-text">Click a preset above to launch Chrome and begin.</div>
          <div id="aiReason" class="reason-box">Ollama / Gemini will evaluate the 100% correct answer here.</div>
        </div>
      </div>

      <!-- Panel 3: Runner Console -->
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-header-icon">💻 RUNNER CONSOLE</div>
        </div>
        <div class="term-box" id="termLogs"></div>
      </div>

    </div>

    <!-- Right Workspace Column (Chrome Live Preview) -->
    <div class="right-column">
      <div class="preview-container">
        
        <!-- Idle Placeholder -->
        <div class="preview-center" id="idleCenter">
          <div class="glow-icon">🌐</div>
          <div class="preview-heading">Live Chrome Workspace Ready</div>
          <div class="preview-subtext">
            When you click any course button on the left, <strong>Google Chrome will launch on your right screen</strong>.
            You can log in for yourself or your friend, and watch the AI solve 100% of the lessons in real time.
          </div>
          <div class="pill-tags">
            <div class="pill-tag">✔ 100% Score Guaranteed</div>
            <div class="pill-tag">✔ Multi-Account Friend Support</div>
            <div class="pill-tag">✔ Auto Video Dismiss</div>
            <div class="pill-tag">✔ Auto Learn Scroll</div>
          </div>
        </div>

        <!-- Live Browser Stream when Active -->
        <div class="active-chrome-screen" id="activeScreen">
          <div class="chrome-url-bar">
            <span style="font-size: 11px; font-weight: 700; color: var(--accent-cyan);">CHROME:</span>
            <div class="url-input" id="currentUrl">https://corporate.bharatenglish.org</div>
            <span style="font-size: 11px; color: var(--accent-green); font-weight: 600;">● AUTOMATION ACTIVE</span>
          </div>
          <div class="chrome-canvas-wrap">
            <img id="liveCanvas" alt="Live Chrome Preview" />
          </div>
        </div>

      </div>
    </div>

  </div>

  <script>
    let activeEngine = 'ollama';

    function selectEngine(eng) {
      activeEngine = eng;
      document.getElementById('tabOllama').className = eng === 'ollama' ? 'tab-btn active' : 'tab-btn';
      document.getElementById('tabGemini').className = eng === 'gemini' ? 'tab-btn active' : 'tab-btn';
      document.getElementById('headerBadge').textContent = eng === 'ollama' ? '● 100% Local Ollama Active' : '● Online Google Gemini Active';
      fetch('/api/engine', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ engine: eng })
      });
    }

    const evtSource = new EventSource('/api/stream');

    evtSource.addEventListener('log', (e) => {
      const data = JSON.parse(e.data);
      const term = document.getElementById('termLogs');
      const div = document.createElement('div');
      div.textContent = data.line;
      term.appendChild(div);
      term.scrollTop = term.scrollHeight;
    });

    evtSource.addEventListener('frame', (e) => {
      const data = JSON.parse(e.data);
      if (data.image) {
        document.getElementById('idleCenter').style.display = 'none';
        document.getElementById('activeScreen').style.display = 'flex';
        document.getElementById('liveCanvas').src = 'data:image/jpeg;base64,' + data.image;
      }
    });

    evtSource.addEventListener('ai_state', (e) => {
      const data = JSON.parse(e.data);
      if (data.status) document.getElementById('statusIndicator').textContent = data.status.toUpperCase();
      if (data.topic) document.getElementById('topicName').textContent = data.topic;
      if (data.current_question) document.getElementById('qText').textContent = data.current_question;
      if (data.ai_reasoning) document.getElementById('aiReason').textContent = data.ai_reasoning;

      if (data.lesson !== undefined && data.total_lessons) {
        document.getElementById('progressText').textContent = `${data.lesson} / ${data.total_lessons}`;
        const pct = Math.round((data.lesson / data.total_lessons) * 100);
        document.getElementById('pctText').textContent = pct + '%';
        document.getElementById('progressBar').style.width = pct + '%';
      }
    });

    function triggerAction(action, mode = '') {
      fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action, mode: mode, engine: activeEngine })
      }).catch(err => console.error(err));
    }
  </script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif parsed.path == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            with clients_lock:
                sse_clients.append(self)
            while True:
                time.sleep(1)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        data = json.loads(body)

        if parsed.path == "/api/engine":
            eng = data.get("engine", "ollama")
            state["engine"] = eng
            append_log(f"[Engine Config] Active AI Engine switched to: {eng.upper()}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))

        elif parsed.path == "/api/action":
            action = data.get("action")
            mode = data.get("mode")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))

            if action == "start":
                start_runner(mode)
            elif action == "stop":
                stop_runner()
            elif action == "new_friend":
                clear_friend_session()

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def clear_friend_session():
    if os.path.exists(SESSION_DIR):
        try:
            shutil.rmtree(SESSION_DIR, ignore_errors=True)
        except Exception:
            pass
    os.environ["BHARAT_FORCE_LOGOUT"] = "1"
    append_log("[Account Switch] Previous session wiped! Ready for new friend's login.")
    update_ai_state({"status": "Ready for Friend", "current_question": "Click a module above to launch login for your friend."})

def start_runner(mode):
    global active_runner_process, active_runner_thread
    if active_runner_process and active_runner_process.poll() is None:
        append_log("[!] A course module is already running. Please Stop it first.")
        return

    append_log(f"Starting {mode.upper()} runner...")
    update_ai_state({"status": f"Running {mode.upper()}", "active_skill": mode.capitalize()})

    def run_worker():
        global active_runner_process
        script_map = {
            "full": os.path.join(BASE_DIR, "run_full_course.py"),
            "listening": os.path.join(BASE_DIR, "listening", "run_live.py"),
            "reading": os.path.join(BASE_DIR, "reading", "run_live.py"),
            "writing": os.path.join(BASE_DIR, "writing ow1", "run_live.py"),
        }
        script_path = script_map.get(mode, script_map["full"])
        env = os.environ.copy()
        env["BHARAT_AI_ENGINE"] = state["engine"]

        active_runner_process = subprocess.Popen(
            [sys.executable, "-u", script_path],
            cwd=os.path.dirname(script_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env
        )
        for line in iter(active_runner_process.stdout.readline, ""):
            if line:
                cleaned = line.rstrip()
                append_log(cleaned)
                # Parse lines for dashboard updates
                if "PROCESSING:" in cleaned or "ENTERING" in cleaned:
                    update_ai_state({"topic": cleaned.split(":")[-1].strip()})
                elif "QUESTION:" in cleaned:
                    update_ai_state({"current_question": cleaned})
                elif "Selected Option" in cleaned or "Heuristic:" in cleaned or "Offline Ollama" in cleaned or "Gemini" in cleaned:
                    update_ai_state({"ai_reasoning": cleaned})

        active_runner_process.stdout.close()
        ret = active_runner_process.wait()
        update_ai_state({"status": "Completed / Idle"})
        append_log(f"{mode.upper()} finished with code {ret}")

    active_runner_thread = threading.Thread(target=run_worker, daemon=True)
    active_runner_thread.start()

def stop_runner():
    global active_runner_process
    if active_runner_process and active_runner_process.poll() is None:
        active_runner_process.terminate()
        append_log("[Stopped] User stopped current runner.")
        update_ai_state({"status": "Stopped"})
    else:
        append_log("[!] No active runner to stop.")

def launch_desktop():
    # 1. Start HTTP Server in background thread
    server = ThreadedHTTPServer(("127.0.0.1", PORT), RequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[BharatCraft Server] Listening on http://127.0.0.1:{PORT}")

    time.sleep(0.8)
    app_url = f"http://127.0.0.1:{PORT}"

    # Dock BharatCraft app on the LEFT HALF of the screen (0 to half_w)
    try:
        subprocess.Popen([
            "chrome.exe",
            f"--app={app_url}",
            f"--window-position=0,0",
            f"--window-size={half_w},{screen_h}",
            "--window-name=BharatCraftAI"
        ])
    except Exception:
        import webbrowser
        webbrowser.open(app_url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Exiting] Platform closed.")

if __name__ == "__main__":
    launch_desktop()
