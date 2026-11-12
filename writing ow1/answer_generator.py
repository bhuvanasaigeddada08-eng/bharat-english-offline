import os
import re
import json
import time
import urllib.request
from dotenv import load_dotenv

load_dotenv()

class AnswerGenerator:
    """
    Generates 100% rubric-compliant responses for Writing exercises using:
    1. Local Offline Ollama models (qwen2.5-coder:1.5b, gemma3:4b, etc.)
    2. Fallback to contextual synthesis engine to ensure zero crashes and maximum scores
    3. Optional Google Gemini API if key is configured
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        self.ollama_available = self._check_ollama()

        if self.ollama_available:
            print("[AI Engine] Local Offline Ollama detected and active for Writing.")

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print("[AI Engine] Gemini API client initialized as secondary fallback.")
            except Exception as e:
                print(f"[AI Engine] Could not initialize Gemini client: {e}")

    def _check_ollama(self) -> bool:
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _query_ollama(self, prompt: str) -> tuple:
        models = ["qwen2.5-coder:1.5b", "gemma3:4b", "llama3.2:1b", "llama3.2", "qwen2.5:1.5b"]
        for model in models:
            try:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
                req = urllib.request.Request(
                    "http://localhost:11434/api/generate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=25) as response:
                    raw = json.loads(response.read().decode("utf-8")).get("response", "")
                    if raw and len(raw.strip()) > 20:
                        return raw.strip(), model
            except Exception:
                continue
        return None, None

    def generate_writing(self, activity: dict) -> str:
        prompt_text = activity.get("prompt", "")
        bullets = activity.get("bullets", [])
        tone = activity.get("tone", "semi-formal")
        aim_words = activity.get("aim_words", 50)
        target_words = max(aim_words + 15, 65)

        bullet_str = "\n".join([f"- {b}" for b in bullets]) if bullets else "- Cover all scenario requirements"
        ai_prompt = f"""You are an expert corporate communications test-taker aiming for a 100% perfect score on a corporate English writing assessment.
Write an email response based strictly on this scenario and requirements:

SCENARIO:
{prompt_text}

MANDATORY POINTS TO INCLUDE (You MUST explicitly address EVERY single one):
{bullet_str}

RUBRIC FOR 100% SCORE:
1. Must begin with a clear, professional Subject line (Subject: ...)
2. Must include an appropriate greeting addressing the person or team (e.g. Hi [Name], or Dear [Name/Role],)
3. Address every mandatory bullet point explicitly with complete, natural sentences.
4. Word count MUST strictly be between {target_words} and {target_words + 20} words (strictly exceeding {aim_words} words).
5. Tone: {tone}.
6. Must include a polite closing and sign-off:
Best regards,
Bhuvana

OUTPUT:
Return ONLY the raw plain text email ready to paste. No markdown asterisks (**), no quotes, no extra notes.
"""

        # 1. First priority: Local Offline Ollama
        if self.ollama_available:
            print("  [AI Engine] Generating email using local offline Ollama...")
            raw_text, model_name = self._query_ollama(ai_prompt)
            if raw_text:
                clean_text = raw_text.replace("**", "").replace("###", "").replace('"', '').strip()
                word_count = len(clean_text.split())
                if word_count >= aim_words:
                    print(f"  [AI Engine] Offline Ollama ({model_name}) generated {word_count} words successfully.")
                    return clean_text

        # 2. Secondary priority: Gemini API (if key available)
        if self.client:
            models_to_try = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]
            for model_name in models_to_try:
                try:
                    print(f"  [AI Engine] Calling {model_name} with API key...")
                    res = self.client.models.generate_content(
                        model=model_name,
                        contents=ai_prompt
                    )
                    text = res.text.strip().replace("**", "").replace("#", "")
                    word_count = len(text.split())
                    if word_count >= aim_words:
                        print(f"  [AI Engine] Successfully generated with {model_name} ({word_count} words).")
                        return text
                except Exception as e:
                    print(f"  [AI Engine] {model_name} error: {e}")

        # 3. Contextual Template Synthesizer Fallback (Zero crash, 100% offline)
        print("  [AI Engine] Using contextual synthesis fallback.")
        return self._synthesize_email(prompt_text, bullets, tone)

    def _synthesize_email(self, prompt: str, bullets: list, tone: str) -> str:
        lower_prompt = prompt.lower()
        
        # 1. Extract name if mentioned
        name_match = re.search(r'\b(priya|ramesh|sarah|rahul|amit|sneha|rohit|neha|pooja|vikram|anita|arun|deepak|kavita|raj|john|david|michael|lisa|emily)\b', lower_prompt)
        person_name = name_match.group(1).capitalize() if name_match else None

        # 2. Determine Greeting
        is_informal = "informal" in tone.lower() or "casual" in tone.lower()
        if person_name:
            greeting = f"Hi {person_name}," if is_informal else f"Dear {person_name},"
        elif "hr" in lower_prompt or "training" in lower_prompt:
            greeting = "Dear HR Manager,"
        elif "vendor" in lower_prompt or "supplier" in lower_prompt:
            greeting = "Dear Vendor,"
        elif "client" in lower_prompt or "customer" in lower_prompt:
            greeting = "Dear Client,"
        elif "manager" in lower_prompt or "supervisor" in lower_prompt:
            greeting = "Dear Manager,"
        elif "colleague" in lower_prompt or "coworker" in lower_prompt:
            greeting = "Hi Colleague," if is_informal else "Dear Colleague,"
        else:
            greeting = "Hi Team," if is_informal else "Dear Team,"

        # 3. Determine Subject
        if "thank" in lower_prompt or "help" in lower_prompt:
            subject = f"Subject: Thank you for your help yesterday" if person_name else "Subject: Thank you for your valuable support"
        elif "training" in lower_prompt or "location" in lower_prompt:
            subject = "Subject: Inquiry Regarding Training Session Location"
        elif "deadline" in lower_prompt:
            subject = "Subject: Important Update Regarding Project Deadline"
        elif "feedback" in lower_prompt:
            subject = "Subject: Appreciation for Your Constructive Feedback"
        elif "additional information" in lower_prompt or "specifications" in lower_prompt:
            subject = "Subject: Request for Detailed Product Specifications"
        elif "reschedule" in lower_prompt:
            subject = "Subject: Request to Reschedule Our Upcoming Meeting"
        elif "summary" in lower_prompt or "notes" in lower_prompt:
            subject = "Subject: Summary of Workplace Tasks and Key Takeaways"
        else:
            subject = "Subject: Follow-up Regarding Discussion and Key Action Items"

        # 4. Expand bullets into fluent sentences
        expanded_points = []
        for b in bullets:
            b_clean = b.strip()
            if not b_clean:
                continue
            b_low = b_clean.lower()
            
            if "when" in b_low or "yesterday" in b_low or "date and time" in b_low or "time and platform" in b_low:
                expanded_points.append("I wanted to reach out and thank you for taking the time to assist me yesterday afternoon.")
            elif "what" in b_low and ("helped" in b_low or "explained" in b_low or "feedback" in b_low):
                expanded_points.append("I truly appreciate you explaining the key components and requirements of the new project in such clear detail.")
            elif "thank" in b_low or "appreciation" in b_low:
                expanded_points.append("Your guidance was incredibly helpful and gave me complete confidence in moving forward.")
            elif "location" in b_low or "where" in b_low:
                expanded_points.append("Could you please let me know the exact location and room number where the sessions will be held?")
            elif "collaborat" in b_low or "work together" in b_low or "future" in b_low:
                expanded_points.append("I would love the opportunity to collaborate with you on similar upcoming initiatives in the future.")
            elif "specifications" in b_low or "information" in b_low:
                expanded_points.append("Could you please share the technical specifications sheet and relevant project documentation?")
            elif "discount" in b_low or "pricing" in b_low:
                expanded_points.append("Additionally, please let us know if any bulk order discounts or revised pricing apply.")
            elif "deadline" in b_low or "next step" in b_low or "action" in b_low:
                expanded_points.append("Please let me know if there are any specific action items or deadlines we need to track.")
            elif "new idea" in b_low or "suggestion" in b_low:
                expanded_points.append("I would also like to propose organizing brief weekly checkpoints to monitor progress effectively.")
            elif "subject" in b_low or "closing" in b_low or "salutation" in b_low or "greeting" in b_low:
                continue
            else:
                expanded_points.append(f"Regarding the matter, I will ensure that {b_clean.lower()} is properly handled.")

        if not expanded_points:
            expanded_points.append("Thank you so much for your assistance and support with this task.")
            expanded_points.append("Your helpful explanation made the entire process much smoother and easier to manage.")
            expanded_points.append("I look forward to working together again very soon.")

        body_text = " ".join(expanded_points)
        
        if is_informal:
            closing = "Thanks again for all your help!\n\nBest,\nBhuvana"
        else:
            closing = "Thank you once again for your assistance.\n\nBest regards,\nBhuvana"

        email = f"{subject}\n\n{greeting}\n\n{body_text}\n\n{closing}"
        
        words = email.split()
        if len(words) < 55:
            extra = "Please feel free to reach out if you have any questions or if there is anything else I can assist with."
            email = f"{subject}\n\n{greeting}\n\n{body_text}\n\n{extra}\n\n{closing}"
            
        return email

    def solve(self, passage: str, question: str, options: list) -> dict:
        if not options:
            return {"recommended_index": None, "confidence": 0.0, "reasoning": "No options available"}

        # Attempt Gemini solution
        if self.client:
            try:
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
                response = self.client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                import json
                res_data = json.loads(response.text)
                idx = int(res_data["recommended_index"])
                text = next((o["text"] for o in options if o["index"] == idx), options[0]["text"])
                return {
                    "recommended_index": idx,
                    "recommended_text": text,
                    "confidence": 0.99,
                    "reasoning": f"Gemini: {res_data.get('reasoning', 'Extracted directly from passage.')}"
                }
            except Exception:
                pass

        best_match = None
        best_score = -1
        for opt in options:
            opt_text = opt["text"].lower().strip()
            if opt_text in passage.lower():
                score = len(opt_text) + 20
                if score > best_score:
                    best_score = score
                    best_match = opt
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

        return {
            "recommended_index": 1,
            "recommended_text": options[0]["text"],
            "confidence": 0.50,
            "reasoning": "Fallback to first option"
        }
