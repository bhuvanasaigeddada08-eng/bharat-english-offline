import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODULES = {
    "Full Course (All 3 Skills)": os.path.join(BASE_DIR, "run_full_course.py"),
    "Listening (30 Lessons)": os.path.join(BASE_DIR, "listening", "run_live.py"),
    "Reading (30 Lessons)": os.path.join(BASE_DIR, "reading", "run_live.py"),
    "Writing (30 Lessons)": os.path.join(BASE_DIR, "writing ow1", "run_live.py"),
}

class BharatEnglishLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Bharat English Autonomous Assistant")
        self.root.geometry("820x620")
        self.root.configure(bg="#181825")
        self.process = None

        # Header Title
        title = tk.Label(
            root,
            text="Bharat English Autonomous Platform Runner",
            font=("Segoe UI", 16, "bold"),
            fg="#cdd6f4",
            bg="#181825"
        )
        title.pack(pady=(16, 4))

        subtitle = tk.Label(
            root,
            text="Automatic Login Detection | 30 Modules per Skill | Auto Next Advancing",
            font=("Segoe UI", 10),
            fg="#a6adc8",
            bg="#181825"
        )
        subtitle.pack(pady=(0, 16))

        # Action Buttons Grid Frame
        btn_frame = tk.Frame(root, bg="#181825")
        btn_frame.pack(pady=4)

        self.btn_full = tk.Button(
            btn_frame,
            text="⚡ Run All 3 (Full Course)",
            font=("Segoe UI", 11, "bold"),
            bg="#fab387",
            fg="#11111b",
            width=22,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.launch_script("Full Course (All 3 Skills)")
        )
        self.btn_full.grid(row=0, column=0, padx=6, pady=4)

        self.btn_listening = tk.Button(
            btn_frame,
            text="🎧 Listening (30)",
            font=("Segoe UI", 11, "bold"),
            bg="#89b4fa",
            fg="#11111b",
            width=16,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.launch_script("Listening (30 Lessons)")
        )
        self.btn_listening.grid(row=0, column=1, padx=6, pady=4)

        self.btn_reading = tk.Button(
            btn_frame,
            text="📖 Reading (30)",
            font=("Segoe UI", 11, "bold"),
            bg="#a6e3a1",
            fg="#11111b",
            width=16,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.launch_script("Reading (30 Lessons)")
        )
        self.btn_reading.grid(row=0, column=2, padx=6, pady=4)

        self.btn_writing = tk.Button(
            btn_frame,
            text="✍️ Writing (30)",
            font=("Segoe UI", 11, "bold"),
            bg="#f9e2af",
            fg="#11111b",
            width=16,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.launch_script("Writing (30 Lessons)")
        )
        self.btn_writing.grid(row=0, column=3, padx=6, pady=4)

        # Stop Button & Status Bar
        ctrl_frame = tk.Frame(root, bg="#181825")
        ctrl_frame.pack(pady=10, fill=tk.X, padx=25)

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
            font=("Segoe UI", 10, "bold"),
            bg="#f38ba8",
            fg="#11111b",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=4,
            command=self.stop_current
        )
        self.btn_stop.pack(side=tk.RIGHT)

        # Output Terminal Screen
        self.terminal = scrolledtext.ScrolledText(
            root,
            bg="#11111b",
            fg="#a6e3a1",
            font=("Consolas", 10),
            insertbackground="white",
            relief=tk.FLAT
        )
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 20))

    def append_log(self, text):
        self.terminal.insert(tk.END, text + "\n")
        self.terminal.see(tk.END)

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
        self.append_log(f" >>> LAUNCHING: {label} <<<")
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
            self.append_log(f"\n[Finished] Execution completed with status code {ret}\n")

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
    app = BharatEnglishLauncher(root)
    root.mainloop()
