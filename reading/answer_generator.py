import os
import json
import re
import urllib.request
from dotenv import load_dotenv

load_dotenv()

class AnswerGenerator:
    """
    Solves reading comprehension questions using:
    1. Local Offline Ollama models (qwen2.5-coder:1.5b, gemma3:4b, etc.)
    2. Smart contextual heuristics based on passage keyword density
    3. Google Gemini API (optional fallback if key provided)
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        self.ollama_available = self._check_ollama()

        if self.ollama_available:
            print("[AI Engine] Local Offline Ollama detected and active for Reading.")

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print("[AI Engine] Gemini API client initialized as secondary fallback.")
            except Exception:
                pass

    def _check_ollama(self) -> bool:
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _query_ollama(self, prompt: str) -> dict:
        models = ["qwen2.5-coder:1.5b", "gemma3:4b", "llama3.2:1b", "llama3.2", "qwen2.5:1.5b"]
        for model in models:
            try:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
                req = urllib.request.Request(
                    "http://localhost:11434/api/generate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    raw = json.loads(response.read().decode("utf-8")).get("response", "")
                    return json.loads(raw), model
            except Exception:
                continue
        return None, None

    def solve(self, passage: str, question: str, options: list) -> dict:
        if not options:
            return {"recommended_index": None, "confidence": 0.0, "reasoning": "No options available"}

        opt_str = "\n".join([f"[{o['index']}] {o['text']}" for o in options])
        prompt = f"""You are an expert reading comprehension test-taker.
Read the passage and select the 100% correct option for the question.

PASSAGE:
\"\"\"{passage}\"\"\"

QUESTION:
{question}

OPTIONS:
{opt_str}

Respond strictly in pure JSON with:
{{
  "recommended_index": <int, exactly 1, 2, 3, or 4>,
  "reasoning": "<very concise 1-sentence reasoning from the passage>"
}}
"""

        # 1. Primary Priority: Local Offline Ollama
        if self.ollama_available:
            res_data, model_name = self._query_ollama(prompt)
            if res_data and "recommended_index" in res_data:
                try:
                    idx = int(res_data["recommended_index"])
                    if 1 <= idx <= len(options):
                        text = next((o["text"] for o in options if o["index"] == idx), options[0]["text"])
                        return {
                            "recommended_index": idx,
                            "recommended_text": text,
                            "confidence": 1.0,
                            "reasoning": f"Offline Ollama ({model_name}): {res_data.get('reasoning', '')}"
                        }
                except Exception:
                    pass

        # 2. Smart contextual heuristics fallback
        best_match = None
        best_score = -1

        for opt in options:
            opt_text = opt["text"].lower().strip()
            # Direct match
            if opt_text in passage.lower():
                score = len(opt_text) + 20
                if score > best_score:
                    best_score = score
                    best_match = opt
            # Sub-word overlap
            words = [w for w in re.split(r'\W+', opt_text) if len(w) > 2]
            overlap = sum(1 for w in words if w in passage.lower())
            if overlap > best_score:
                best_score = overlap
                best_match = opt

        if best_match:
            return {
                "recommended_index": best_match["index"],
                "recommended_text": best_match["text"],
                "confidence": 0.90,
                "reasoning": f"Heuristic: Matched key terms '{best_match['text']}' directly in passage."
            }

        # 3. Optional Gemini LLM Fallback
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                res_data = json.loads(response.text)
                idx = int(res_data["recommended_index"])
                text = next((o["text"] for o in options if o["index"] == idx), options[0]["text"])
                return {
                    "recommended_index": idx,
                    "recommended_text": text,
                    "confidence": 0.99,
                    "reasoning": f"Gemini: {res_data.get('reasoning', 'Extracted directly from passage.')}"
                }
            except Exception as e:
                print(f"[AI Engine] Gemini API call exception: {e}")

        return {
            "recommended_index": 1,
            "recommended_text": options[0]["text"],
            "confidence": 0.50,
            "reasoning": "Fallback to first option"
        }
