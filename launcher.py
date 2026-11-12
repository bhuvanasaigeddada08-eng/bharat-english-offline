import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, ".active_session")

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

MODULES = {
    "Full Course (90 Lessons)": os.path.join(BASE_DIR, "run_full_course.py"),
    "Listening (30 Lessons)": os.path.join(BASE_DIR, "listening", "run_live.py"),
    "Reading (30 Lessons)": os.path.join(BASE_DIR, "reading", "run_live.py"),
    "Writing (30 Lessons)": os.path.join(BASE_DIR, "writing ow1", "run_live.py"),
}

class BharatEnglishSplitLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Bharat English AI Controller (Split Screen)")
        
        # Snap launcher to the RIGHT HALF of the display
        right_w = screen_w - half_w
        self.root.geometry(f"{right_w}x{screen_h - 60}+{half_w}+0")
        self.root.configure(bg="#11111b")
        self.process = None

        # Title Header
        header = tk.Frame(root, bg="#181825", pady=10)
        header.pack(fill=tk.X)

        title = tk.Label(
            header,
            text="Bharat English Offline Autonomous Controller",
            font=("Segoe UI", 14, "bold"),
            fg="#cdd6f4",
            bg="#181825"
        )
        title.pack()

        subtitle = tk.Label(
            header,
            text="Left: Live Chrome Preview  |  Right: AI Solver & Live Logs",
            font=("Segoe UI", 9),
            fg="#a6adc8",
            bg="#181825"
        )
        subtitle.pack(pady=(2, 0))

        # Friend / Account Switch Bar
        acc_frame = tk.Frame(root, bg="#1e1e2e", pady=8, padx=15)
        acc_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        acc_title = tk.Label(
            acc_frame,
            text="Account Management (Multiple Friends / Accounts):",
            font=("Segoe UI", 10, "bold"),
            fg="#89b4fa",
            bg="#1e1e2e"
        )
        acc_title.pack(side=tk.LEFT)

        btn_new_friend = tk.Button(
            acc_frame,
            text="👤 Log In New Friend (Fresh Account)",
            font=("Segoe UI", 9, "bold"),
            bg="#f38ba8",
            fg="#11111b",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=3,
            command=self.clear_session_for_friend
        )
        btn_new_friend.pack(side=tk.RIGHT)

        # Primary Action Buttons
        btn_frame = tk.Frame(root, bg="#11111b")
        btn_frame.pack(pady=8, padx=15, fill=tk.X)

        self.btn_full = tk.Button(
            btn_frame,
            text="⚡ Run Full Course (All 3 Skills)\nListening (30) ➔ Reading (30) ➔ Writing (30)",
            font=("Segoe UI", 11, "bold"),
            bg="#fab387",
            fg="#11111b",
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.launch_script("Full Course (90 Lessons)")
        )
        self.btn_full.pack(fill=tk.X, pady=(0, 6))

        sub_btn_frame = tk.Frame(btn_frame, bg="#11111b")
        sub_btn_frame.pack(fill=tk.X)

        self.btn_listening = tk.Button(
            sub_btn_frame,
            text="🎧 Listening (30)",
            font=("Segoe UI", 10, "bold"),
            bg="#89b4fa",
            fg="#11111b",
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.launch_script("Listening (30 Lessons)")
        )
        self.btn_listening.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        self.btn_reading = tk.Button(
            sub_btn_frame,
            text="📖 Reading (30)",
            font=("Segoe UI", 10, "bold"),
            bg="#a6e3a1",
            fg="#11111b",
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.launch_script("Reading (30 Lessons)")
        )
        self.btn_reading.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.btn_writing = tk.Button(
            sub_btn_frame,
            text="✍️ Writing (30)",
            font=("Segoe UI", 10, "bold"),
            bg="#f9e2af",
            fg="#11111b",
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.launch_script("Writing (30 Lessons)")
        )
        self.btn_writing.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        # Status & Controls Bar
        ctrl_frame = tk.Frame(root, bg="#181825", pady=6, padx=15)
        ctrl_frame.pack(fill=tk.X, padx=15, pady=(8, 4))

        self.status_lbl = tk.Label(
            ctrl_frame,
            text="Status: Ready (Select a course mode above)",
            font=("Segoe UI", 10, "bold"),
            fg="#a6adc8",
            bg="#181825"
        )
        self.status_lbl.pack(side=tk.LEFT)

        self.btn_stop = tk.Button(
            ctrl_frame,
            text="⏹ Stop Runner",
            font=("Segoe UI", 9, "bold"),
            bg="#f38ba8",
            fg="#11111b",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=3,
            command=self.stop_current
        )
        self.btn_stop.pack(side=tk.RIGHT)

        # Live Real-time Logs Console
        self.terminal = scrolledtext.ScrolledText(
            root,
            bg="#181825",
            fg="#a6e3a1",
            font=("Consolas", 10),
            insertbackground="white",
            relief=tk.FLAT
        )
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))

    def append_log(self, text):
        self.terminal.insert(tk.END, text + "\n")
        self.terminal.see(tk.END)

    def clear_session_for_friend(self):
        if self.process and self.process.poll() is None:
            messagebox.showwarning("Busy", "A runner is currently active. Stop it before switching accounts.")
            return

        if os.path.exists(SESSION_DIR):
            try:
                shutil.rmtree(SESSION_DIR, ignore_errors=True)
            except Exception:
                pass

        os.environ["BHARAT_FORCE_LOGOUT"] = "1"
        self.append_log("\n" + "=" * 65)
        self.append_log("[Account Switch] Active session cleared successfully!")
        self.append_log("Now click any button above. Chrome will open on the left half")
        self.append_log("asking for your friend's login credentials.")
        self.append_log("=" * 65 + "\n")
        self.status_lbl.config(text="Status: Ready for New Friend Login", fg="#f9e2af")
        messagebox.showinfo("Ready for New Friend", "Session cleared! Click any course button to log in for your friend.")

    def launch_script(self, label):
        if self.process and self.process.poll() is None:
            self.append_log("[!] A module is already executing. Please Stop it first before starting another.")
            return

        target_path = MODULES.get(label)
        if not target_path or not os.path.exists(target_path):
            self.append_log(f"[Error] File not found: {target_path}")
            return

        self.status_lbl.config(text=f"Status: Running {label}...", fg="#89b4fa")
        self.append_log(f"\n========================================================")
        self.append_log(f" >>> STARTING {label.upper()} <<<")
        self.append_log(f" Chrome will dock on LEFT HALF | Controller on RIGHT HALF")
        self.append_log(f"========================================================")

        def runner():
            work_dir = os.path.dirname(target_path)
            self.process = subprocess.Popen(
                [sys.executable, "-u", target_path],
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )
            for line in iter(self.process.stdout.readline, ""):
                if line:
                    self.append_log(line.rstrip())

            self.process.stdout.close()
            ret = self.process.wait()
            self.status_lbl.config(text="Status: Completed / Idle", fg="#a6e3a1")
            self.append_log(f"\n[Finished] Execution finished with status code {ret}\n")

        threading.Thread(target=runner, daemon=True).start()

    def stop_current(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status_lbl.config(text="Status: Stopped by user", fg="#f38ba8")
            self.append_log("\n[!] Process was stopped by user.\n")
        else:
            self.append_log("[!] No active runner is currently running.")

if __name__ == "__main__":
    root = tk.Tk()
    app = BharatEnglishSplitLauncher(root)
    root.mainloop()
