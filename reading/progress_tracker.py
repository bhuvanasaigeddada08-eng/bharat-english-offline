import json
import os
from datetime import datetime

class ProgressTracker:
    def __init__(self, log_path="reading_progress.json"):
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

    def record_dry_run(self, question, recommended_answer, reasoning):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "mode": "dry-run",
            "question": question,
            "proposed_answer": recommended_answer,
            "reasoning": reasoning
        }
        self.history.append(entry)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)
        print(f"[Tracker] Logged activity analysis to {self.log_path}")

