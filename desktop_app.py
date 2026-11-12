import os
import sys
import json
import time
import base64
import threading
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, ".active_session")
PORT = 8765

# Global Shared State
state = {
    "status": "Idle",
    "active_skill": "None",
    "topic": "None",
    "lesson": 0,
    "total_lessons": 30,
    "current_question": "",
    "options": [],
    "selected_option": "",
    "ai_reasoning": "",
    "logs": []
}

active_runner = None
active_runner_stop_event = threading.Event()
sse_clients = []
clients_lock = threading.Lock()
latest_frame = None

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
    if len(state["logs"]) > 200:
        state["logs"].pop(0)
    broadcast_event("log", {"line": formatted})

def update_ai_state(data: dict):
    state.update(data)
    broadcast_event("ai_state", state)

# HTML / CSS / JS for VS Code Styled Platform
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bharat English Autonomous Platform (VS Code Edition)</title>
  <style>
    :root {
      --bg-dark: #181825;
      --bg-sidebar: #1e1e2e;
      --bg-card: #252538;
      --bg-preview: #11111b;
      --text-main: #cdd6f4;
      --text-dim: #a6adc8;
      --accent-blue: #89b4fa;
      --accent-green: #a6e3a1;
      --accent-yellow: #f9e2af;
      --accent-peach: #fab387;
      --accent-red: #f38ba8;
      --border-color: #313244;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
      background: var(--bg-dark);
      color: var(--text-main);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    /* Title Bar */
    .titlebar {
      height: 38px;
      background: #11111b;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      border-bottom: 1px solid var(--border-color);
      font-size: 12px;
      user-select: none;
    }
    .titlebar-left { display: flex; align-items: center; gap: 8px; font-weight: 600; }
    .badge-status {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 3px 10px;
      border-radius: 12px;
      background: #252538;
      font-size: 11px;
      color: var(--text-dim);
    }
    .badge-dot { width: 8px; height: 8px; border-radius: 50%; background: #6c7086; }
    .badge-dot.active { background: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }

    /* Main Workspace Layout */
    .workspace {
      display: flex;
      flex: 1;
      height: calc(100vh - 38px);
    }

    /* Left Side: Controller & Logs */
    .left-panel {
      width: 48%;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    /* Action Control Toolbar */
    .toolbar {
      padding: 12px 16px;
      background: var(--bg-dark);
      border-bottom: 1px solid var(--border-color);
    }
    .account-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px dashed var(--border-color);
    }
    .btn-friend {
      background: #313244;
      border: 1px solid var(--accent-peach);
      color: var(--accent-peach);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-friend:hover { background: var(--accent-peach); color: #11111b; }

    .btn-grid {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
      gap: 6px;
    }
    .btn {
      padding: 8px 10px;
      border: none;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      transition: opacity 0.2s, transform 0.1s;
    }
    .btn:active { transform: scale(0.97); }
    .btn-run-all { background: var(--accent-peach); color: #11111b; }
    .btn-listening { background: var(--accent-blue); color: #11111b; }
    .btn-reading { background: var(--accent-green); color: #11111b; }
    .btn-writing { background: var(--accent-yellow); color: #11111b; }
    .btn-stop { background: var(--accent-red); color: #11111b; }

    /* Middle Area: AI State Cards */
    .ai-dashboard {
      padding: 14px 16px;
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px 14px;
    }
    .card-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--accent-blue);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .progress-bar-container {
      width: 100%;
      height: 8px;
      background: #1e1e2e;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 6px;
    }
    .progress-bar-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
      transition: width 0.3s;
    }
    .question-box {
      font-size: 13px;
      color: #fff;
      margin-bottom: 8px;
      line-height: 1.4;
    }
    .options-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .option-item {
      font-size: 12px;
      padding: 5px 8px;
      border-radius: 4px;
      background: #1e1e2e;
      color: var(--text-dim);
      border-left: 3px solid transparent;
    }
    .option-item.selected {
      background: #2b392b;
      color: var(--accent-green);
      font-weight: 600;
      border-left: 3px solid var(--accent-green);
    }
    .reasoning-text {
      font-size: 12px;
      color: var(--accent-yellow);
      line-height: 1.4;
      font-style: italic;
    }

    /* Terminal Console */
    .terminal-container {
      height: 160px;
      background: #11111b;
      border-top: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
    }
    .terminal-header {
      height: 26px;
      background: #181825;
      padding: 0 12px;
      font-size: 11px;
      color: var(--text-dim);
      display: flex;
      align-items: center;
      font-weight: 600;
      border-bottom: 1px solid var(--border-color);
    }
    .terminal-body {
      flex: 1;
      padding: 8px 12px;
      overflow-y: auto;
      font-family: "Consolas", "Courier New", monospace;
      font-size: 11px;
      color: var(--accent-green);
      line-height: 1.5;
    }

    /* Right Side: Chrome Live Preview */
    .right-panel {
      width: 52%;
      background: var(--bg-preview);
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .preview-bar {
      height: 38px;
      background: #1e1e2e;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      padding: 0 12px;
      gap: 10px;
    }
    .preview-url {
      flex: 1;
      background: #11111b;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      padding: 4px 10px;
      font-size: 11px;
      color: var(--text-dim);
      font-family: monospace;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .preview-status {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: var(--accent-green);
      font-weight: 600;
    }
    .canvas-container {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      background: #000;
      overflow: hidden;
    }
    #screencastCanvas {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      cursor: crosshair;
    }
    .placeholder-overlay {
      position: absolute;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      color: var(--text-dim);
    }
    .spinner {
      width: 32px;
      height: 32px;
      border: 3px solid #313244;
      border-top-color: var(--accent-blue);
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

  <!-- Title Bar -->
  <div class="titlebar">
    <div class="titlebar-left">
      <span>🚀 Bharat English Autonomous IDE</span>
      <span style="color: var(--text-dim);">|</span>
      <span style="color: var(--accent-blue);">100% Offline Ollama Engine</span>
    </div>
    <div class="badge-status">
      <div id="statusDot" class="badge-dot"></div>
      <span id="statusText">Idle</span>
    </div>
  </div>

  <!-- Workspace -->
  <div class="workspace">

    <!-- Left Panel: Controls, AI Thoughts & Logs -->
    <div class="left-panel">
      
      <!-- Toolbar -->
      <div class="toolbar">
        <div class="account-bar">
          <span style="font-size: 11px; color: var(--text-dim);">Account: <strong>Multiple Friends Active</strong></span>
          <button class="btn-friend" onclick="triggerAction('new_friend')">👤 New Friend Login</button>
        </div>
        <div class="btn-grid">
          <button class="btn btn-run-all" onclick="triggerAction('start', 'full')">⚡ Run All (90)</button>
          <button class="btn btn-listening" onclick="triggerAction('start', 'listening')">🎧 Listening</button>
          <button class="btn btn-reading" onclick="triggerAction('start', 'reading')">📖 Reading</button>
          <button class="btn btn-writing" onclick="triggerAction('start', 'writing')">✍️ Writing</button>
          <button class="btn btn-stop" onclick="triggerAction('stop')">⏹ Stop</button>
        </div>
      </div>

      <!-- AI Cards -->
      <div class="ai-dashboard">
        
        <!-- Progress Card -->
        <div class="card">
          <div class="card-title">
            <span id="skillBadge">Course Progress</span>
            <span id="progressRatio">0 / 30</span>
          </div>
          <div id="topicTitle" style="font-size: 12px; font-weight: 600; color: #fff;">Select a skill to start automation</div>
          <div class="progress-bar-container">
            <div id="progressBar" class="progress-bar-fill"></div>
          </div>
        </div>

        <!-- Question Card -->
        <div class="card">
          <div class="card-title">Active Test Question</div>
          <div id="questionText" class="question-box">Waiting for question from live Chrome...</div>
          <div id="optionsContainer" class="options-list"></div>
        </div>

        <!-- Ollama Reasoning Card -->
        <div class="card">
          <div class="card-title">🧠 Ollama Offline Thought Process</div>
          <div id="reasoningText" class="reasoning-text">Local model reasoning will appear here when evaluating answers.</div>
        </div>

      </div>

      <!-- Terminal Output -->
      <div class="terminal-container">
        <div class="terminal-header">Integrated Runner Terminal</div>
        <div id="terminalBody" class="terminal-body"></div>
      </div>

    </div>

    <!-- Right Panel: Live Chrome Preview -->
    <div class="right-panel">
      <div class="preview-bar">
        <div class="preview-url" id="liveUrl">https://corporate.bharatenglish.org</div>
        <div class="preview-status">
          <div class="badge-dot active"></div>
          <span>LIVE CHROME</span>
        </div>
      </div>
      <div class="canvas-container">
        <div id="previewPlaceholder" class="placeholder-overlay">
          <div class="spinner"></div>
          <p>Connecting to Live Chrome Browser Engine...</p>
        </div>
        <img id="screencastCanvas" style="display: none;" alt="Chrome Preview" />
      </div>
    </div>

  </div>

  <script>
    const canvas = document.getElementById('screencastCanvas');
    const placeholder = document.getElementById('previewPlaceholder');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const skillBadge = document.getElementById('skillBadge');
    const progressRatio = document.getElementById('progressRatio');
    const topicTitle = document.getElementById('topicTitle');
    const progressBar = document.getElementById('progressBar');
    const questionText = document.getElementById('questionText');
    const optionsContainer = document.getElementById('optionsContainer');
    const reasoningText = document.getElementById('reasoningText');
    const terminalBody = document.getElementById('terminalBody');

    // Server-Sent Events (SSE) Listener
    const evtSource = new EventSource('/api/stream');

    evtSource.addEventListener('frame', (e) => {
      const data = JSON.parse(e.data);
      if (data.image) {
        canvas.src = "data:image/jpeg;base64," + data.image;
        if (canvas.style.display === 'none') {
          canvas.style.display = 'block';
          placeholder.style.display = 'none';
        }
      }
    });

    evtSource.addEventListener('log', (e) => {
      const data = JSON.parse(e.data);
      const line = document.createElement('div');
      line.textContent = data.line;
      terminalBody.appendChild(line);
      terminalBody.scrollTop = terminalBody.scrollHeight;
    });

    evtSource.addEventListener('ai_state', (e) => {
      const data = JSON.parse(e.data);
      statusText.textContent = data.status || 'Active';
      statusDot.className = data.status && data.status !== 'Idle' ? 'badge-dot active' : 'badge-dot';
      
      if (data.active_skill) skillBadge.textContent = data.active_skill;
      if (data.topic) topicTitle.textContent = data.topic;
      if (data.lesson !== undefined && data.total_lessons) {
        progressRatio.textContent = `${data.lesson} / ${data.total_lessons}`;
        const pct = Math.round((data.lesson / data.total_lessons) * 100);
        progressBar.style.width = pct + '%';
      }

      if (data.current_question) {
        questionText.textContent = data.current_question;
      }

      if (data.options && data.options.length > 0) {
        optionsContainer.innerHTML = '';
        data.options.forEach(opt => {
          const div = document.createElement('div');
          div.className = 'option-item' + (data.selected_option === opt.text ? ' selected' : '');
          div.textContent = `[${opt.index}] ${opt.text}`;
          optionsContainer.appendChild(div);
        });
      }

      if (data.ai_reasoning) {
        reasoningText.textContent = data.ai_reasoning;
      }
    });

    function triggerAction(action, mode = '') {
      fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action, mode: mode })
      }).catch(err => console.error(err));
    }
  </script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
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
        if parsed.path == "/api/action":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
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
                clear_session()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def clear_session():
    import shutil
    if os.path.exists(SESSION_DIR):
        try:
            shutil.rmtree(SESSION_DIR, ignore_errors=True)
        except Exception:
            pass
    os.environ["BHARAT_FORCE_LOGOUT"] = "1"
    append_log("[Account Switch] Active session wiped! Starting next runner will prompt fresh friend login.")
    update_ai_state({"status": "Ready for Friend Login", "current_question": "Click a skill to open login for your friend."})

def start_runner(mode):
    global active_runner
    if active_runner and active_runner.is_alive():
        append_log("[!] A course module is already running. Please Stop it first.")
        return

    append_log(f"Starting {mode.upper()} runner...")
    update_ai_state({"status": f"Running {mode.upper()}", "active_skill": mode.capitalize()})

    def run_worker():
        script_map = {
            "full": os.path.join(BASE_DIR, "run_full_course.py"),
            "listening": os.path.join(BASE_DIR, "listening", "run_live.py"),
            "reading": os.path.join(BASE_DIR, "reading", "run_live.py"),
            "writing": os.path.join(BASE_DIR, "writing ow1", "run_live.py"),
        }
        script_path = script_map.get(mode, script_map["full"])
        proc = subprocess.Popen(
            [sys.executable, "-u", script_path],
            cwd=os.path.dirname(script_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )
        for line in iter(proc.stdout.readline, ""):
            if line:
                append_log(line.rstrip())
        proc.stdout.close()
        proc.wait()
        update_ai_state({"status": "Completed / Idle"})
        append_log(f"{mode.upper()} completed!")

    active_runner = threading.Thread(target=run_worker, daemon=True)
    active_runner.start()

def stop_runner():
    append_log("[User Request] Stopping runners...")
    update_ai_state({"status": "Stopped"})

def launch_desktop():
    # 1. Start HTTP Server in background thread
    server = ThreadedHTTPServer(("127.0.0.1", PORT), RequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[Platform Server] Listening on http://127.0.0.1:{PORT}")

    # 2. Launch Chrome in Frameless Desktop App Mode (VS Code feel)
    time.sleep(1)
    app_url = f"http://127.0.0.1:{PORT}"
    try:
        subprocess.Popen([
            "chrome.exe",
            f"--app={app_url}",
            "--start-maximized",
            "--window-name=BharatEnglishIDE"
        ])
    except Exception:
        import webbrowser
        webbrowser.open(app_url)

    # Keep server alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Exiting] Platform closed.")

if __name__ == "__main__":
    launch_desktop()
