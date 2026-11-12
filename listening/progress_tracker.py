import json
import os
from datetime import datetime

class ProgressTracker:
    def __init__(self, log_path="listening_progress.json"):
        self.log_path = log_path
        self.history = self.load()

    def load(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def record_question(self, question, selected_option, reasoning=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "listening",
            "question": question,
            "selected_option": selected_option,
            "reasoning": reasoning
        }
        self.history.append(entry)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)
        print(f"[Tracker] Logged activity to {self.log_path}")

