"""Gemini AI service — isolated from Flask routes for testability."""

import json
import logging

import requests

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

QUESTION_TYPES = {"technical", "behavioral", "hr", "system-design", "mcq", "coding", "conceptual"}
DIFFICULTIES = {"easy", "medium", "hard"}
CATEGORIES = {
    "python", "sql", "dsa", "oop", "dbms", "operating-systems",
    "computer-networks", "web-development", "behavioral", "system-design",
}


class AIServiceError(Exception):
    """Raised when the AI service fails."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _normalize_schema(schema):
    """Ensure all OpenAPI type values are uppercase for Google Gemini API."""
    if isinstance(schema, dict):
        new_schema = {}
        for k, v in schema.items():
            if k == "type" and isinstance(v, str):
                new_schema[k] = v.upper()
            else:
                new_schema[k] = _normalize_schema(v)
        return new_schema
    elif isinstance(schema, list):
        return [_normalize_schema(item) for item in schema]
    return schema


class AIService:
    """Wrapper around the Google Gemini generateContent REST API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str = "gemini-3.1-flash-lite"):
        if not api_key:
            raise AIServiceError(
                "AI_API_KEY is not set. Add your Google Gemini API key to .env and restart.",
                status_code=400,
            )
        self.api_key = api_key.strip()
        self.model = model.strip() if model else "gemini-3.1-flash-lite"

    # ── Low-level API call ────────────────────────────────────────────────

    def _call(self, contents: list, system_instruction: str, response_schema: dict) -> dict:
        """POST to Gemini generateContent with structured JSON output."""
        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        normalized_schema = _normalize_schema(response_schema)
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": normalized_schema,
                "temperature": 0.7,
            },
        }
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=90,
            )
        except requests.Timeout:
            raise AIServiceError("AI request timed out. Please try again.", status_code=504)
        except requests.ConnectionError:
            raise AIServiceError("Could not connect to Gemini API. Check your network.", status_code=502)

        if not resp.ok:
            error_data = {}
            try:
                error_data = resp.json().get("error", {})
            except Exception:
                pass

            error_msg = error_data.get("message", "")
            error_status = error_data.get("status", "")
            details = error_data.get("details", [])
            reasons = [d.get("reason") for d in details if isinstance(d, dict)]

            logger.error("Gemini API error %d: %s", resp.status_code, resp.text[:500])

            # Specifically detect invalid API key (Google returns HTTP 400 with API_KEY_INVALID)
            if "API_KEY_INVALID" in reasons or "API key not valid" in error_msg:
                if self.api_key.startswith("gsk_"):
                    raise AIServiceError(
                        "Invalid Gemini API key: The configured key starts with 'gsk_', which is a Groq key format. "
                        "PrepAI uses Google Gemini API. Please set a valid Google Gemini API key (starts with 'AIzaSy...') in .env (AI_API_KEY).",
                        status_code=400,
                    )
                raise AIServiceError(
                    "Invalid Google Gemini API key. Please check the AI_API_KEY in your .env file.",
                    status_code=400,
                )

            if resp.status_code == 403:
                raise AIServiceError(
                    "Gemini API permission denied: Your API key does not have access to this resource or region.",
                    status_code=403,
                )
            if resp.status_code == 404:
                raise AIServiceError(
                    f"Gemini model '{self.model}' was not found. Please set a valid model like 'gemini-3.1-flash-lite' in .env (AI_MODEL).",
                    status_code=404,
                )
            if resp.status_code == 429:
                raise AIServiceError(
                    "Gemini API rate limit reached. Please wait a moment and try again.",
                    status_code=429,
                )

            if error_msg:
                raise AIServiceError(f"Gemini API error ({resp.status_code}): {error_msg}", status_code=resp.status_code)

            raise AIServiceError(f"AI request failed (HTTP {resp.status_code}). Please try again.", status_code=resp.status_code)

        return resp.json()

    @staticmethod
    def _parse(payload: dict):
        """Extract and parse JSON text from a Gemini response."""
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (TypeError, KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.warning("Failed to parse Gemini response: %s", exc)
            return None

    # ── Public API ────────────────────────────────────────────────────────

    def generate_questions(
        self, topic: str, question_type: str = "technical", difficulty: str = "medium", count: int = 5
    ) -> list[dict]:
        """Convenience method that routes to the appropriate question generator."""
        if question_type == "mcq":
            return self.generate_mcq_questions(topic, difficulty, count)
        elif question_type == "coding":
            return self.generate_coding_questions(topic, difficulty, count)
        else:
            return self.generate_questions_with_answers(topic, question_type, difficulty, count)

    def generate_questions_with_answers(
        self, topic: str, question_type: str, difficulty: str, count: int
    ) -> list[dict]:
        """Generate interview questions with model answers."""
        system = (
            "You are an expert technical interviewer who generates high-quality, realistic interview questions. "
            "Always respond with valid JSON matching the provided schema. "
            "Each question must be unique and progressively more challenging."
        )
        prompt = (
            f'Generate {count} {difficulty} {question_type} interview questions about: "{topic}". '
            "For each, provide:\n"
            "- A clear, specific question\n"
            "- A concise model answer in 3-5 sentences\n"
            "- A brief explanation of why this answer is strong"
        )
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        schema = {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "answer": {"type": "string"},
                            "explanation": {"type": "string"},
                        },
                        "required": ["question", "answer"],
                    },
                }
            },
            "required": ["questions"],
        }
        raw = self._call(contents, system, schema)
        parsed = self._parse(raw)
        if not parsed or not isinstance(parsed.get("questions"), list) or len(parsed["questions"]) == 0:
            raise AIServiceError("AI did not return valid questions. Please try again.")

        # Validate each question has required fields
        validated = []
        for q in parsed["questions"]:
            if isinstance(q, dict) and q.get("question") and q.get("answer"):
                validated.append({
                    "question": str(q["question"]).strip(),
                    "answer": str(q["answer"]).strip(),
                    "explanation": str(q.get("explanation", "")).strip(),
                })
        if not validated:
            raise AIServiceError("AI response contained no valid questions.")
        return validated

    def generate_mcq_questions(
        self, topic: str, difficulty: str, count: int
    ) -> list[dict]:
        """Generate multiple-choice questions with options and correct answer."""
        system = (
            "You are an expert question designer. Generate multiple-choice questions with "
            "exactly 4 options labeled A, B, C, D. Exactly one option must be correct. "
            "Always respond with valid JSON matching the provided schema."
        )
        prompt = (
            f'Generate {count} {difficulty} multiple-choice questions about: "{topic}". '
            "Each question must have exactly 4 options and one correct answer."
        )
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        schema = {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "options": {
                                "type": "object",
                                "properties": {
                                    "A": {"type": "string"},
                                    "B": {"type": "string"},
                                    "C": {"type": "string"},
                                    "D": {"type": "string"},
                                },
                                "required": ["A", "B", "C", "D"],
                            },
                            "correct_answer": {"type": "string"},
                            "explanation": {"type": "string"},
                        },
                        "required": ["question", "options", "correct_answer", "explanation"],
                    },
                }
            },
            "required": ["questions"],
        }
        raw = self._call(contents, system, schema)
        parsed = self._parse(raw)
        if not parsed or not isinstance(parsed.get("questions"), list) or len(parsed["questions"]) == 0:
            raise AIServiceError("AI did not return valid MCQ questions.")

        validated = []
        for q in parsed["questions"]:
            if (
                isinstance(q, dict)
                and q.get("question")
                and isinstance(q.get("options"), dict)
                and q.get("correct_answer") in ("A", "B", "C", "D")
            ):
                validated.append(q)
        if not validated:
            raise AIServiceError("AI response contained no valid MCQ questions.")
        return validated

    def generate_coding_questions(
        self, topic: str, difficulty: str, count: int
    ) -> list[dict]:
        """Generate coding/programming questions with problem statements."""
        system = (
            "You are an expert coding interview designer. Generate coding problems with "
            "clear problem statements, constraints, examples, expected complexity, and hints. "
            "Always respond with valid JSON matching the provided schema."
        )
        prompt = (
            f'Generate {count} {difficulty} coding interview questions about: "{topic}". '
            "Include problem statement, constraints, example input/output, expected time/space complexity, "
            "a hint, and a reference solution."
        )
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        schema = {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "constraints": {"type": "string"},
                            "example": {"type": "string"},
                            "expected_complexity": {"type": "string"},
                            "hint": {"type": "string"},
                            "solution": {"type": "string"},
                            "explanation": {"type": "string"},
                        },
                        "required": ["question", "constraints", "example", "solution"],
                    },
                }
            },
            "required": ["questions"],
        }
        raw = self._call(contents, system, schema)
        parsed = self._parse(raw)
        if not parsed or not isinstance(parsed.get("questions"), list) or len(parsed["questions"]) == 0:
            raise AIServiceError("AI did not return valid coding questions.")
        return parsed["questions"]

    def generate_interview_questions(
        self, topic: str, role: str | None = None, question_type: str = "technical", difficulty: str = "medium", count: int = 5
    ) -> list[str]:
        """Generate plain-text interview questions for mock interview mode."""
        role_text = f" for a {role}" if role else ""
        system = "You are a senior interviewer. Return a clean list of interview questions only."
        prompt = (
            f'Create {count} {difficulty} {question_type} interview questions{role_text} '
            f'on: "{topic}". Make them progressive in difficulty.'
        )
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        schema = {
            "type": "object",
            "properties": {
                "questions": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["questions"],
        }
        raw = self._call(contents, system, schema)
        parsed = self._parse(raw)
        if not parsed or not isinstance(parsed.get("questions"), list) or len(parsed["questions"]) == 0:
            raise AIServiceError("AI did not return valid interview questions.")
        return [str(q).strip() for q in parsed["questions"] if str(q).strip()]

    def evaluate_answer(
        self,
        topic: str,
        difficulty: str,
        question_type: str,
        seconds_per_question: int,
        question: str,
        answer: str,
        time_taken: int,
    ) -> dict:
        """Evaluate a candidate's answer with rubric-based feedback."""
        system = (
            "You are a strict but fair interviewer. Evaluate the candidate's answer on clarity, "
            "relevance, and conciseness. Return structured feedback as JSON. "
            "The ideal_answer field must be a suitable model answer that teaches the topic "
            "clearly enough for a student who does not already know it. "
            "Note: AI-based scoring is approximate and should be treated as guidance, not ground truth."
        )
        user_prompt = (
            f"Topic: {topic}\nDifficulty: {difficulty}\nType: {question_type}\n\n"
            f"Question: {question}\n\nCandidate's answer:\n\"\"\"{answer or '(no answer provided)'}\"\"\"\n\n"
            f"Time taken: {time_taken}s of {seconds_per_question}s allowed."
        )
        contents = [{"role": "user", "parts": [{"text": user_prompt}]}]
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "clarity": {"type": "number"},
                "relevance": {"type": "number"},
                "conciseness": {"type": "number"},
                "clarity_note": {"type": "string"},
                "relevance_note": {"type": "string"},
                "conciseness_note": {"type": "string"},
                "strengths": {"type": "string"},
                "improvements": {"type": "string"},
                "ideal_answer": {"type": "string"},
            },
            "required": [
                "score", "clarity", "relevance", "conciseness",
                "clarity_note", "relevance_note", "conciseness_note",
                "strengths", "improvements", "ideal_answer",
            ],
        }
        raw = self._call(contents, system, schema)
        parsed = self._parse(raw)
        if not parsed:
            raise AIServiceError("AI did not return valid feedback.")
        return parsed


def clamp_score(value, lo=0, hi=10):
    """Clamp a numeric value to [lo, hi]."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0
    return max(lo, min(hi, number))


# ── Backward-compatible helper functions ─────────────────────────────────

def generate_ai_question_answers(topic: str, question_type: str = "technical", difficulty: str = "medium", count: int = 5):
    """Generate interview questions with model answers using current app config."""
    import os
    api_key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "gemini-3.1-flash-lite")
    service = AIService(api_key=api_key, model=model)
    return service.generate_questions_with_answers(topic, question_type, difficulty, count)


def generate_ai_interview_questions(topic: str, role: str | None = None, question_type: str = "technical", difficulty: str = "medium", count: int = 5):
    """Generate mock interview question list using current app config."""
    import os
    api_key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "gemini-3.1-flash-lite")
    service = AIService(api_key=api_key, model=model)
    return service.generate_interview_questions(topic, role, question_type, difficulty, count)


def evaluate_ai_answer(topic: str, question: str, answer: str, time_taken: int = 0, difficulty: str = "medium", question_type: str = "technical", seconds_per_question: int = 120):
    """Evaluate candidate answer using current app config."""
    import os
    api_key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "gemini-3.1-flash-lite")
    service = AIService(api_key=api_key, model=model)
    return service.evaluate_answer(
        topic=topic,
        difficulty=difficulty,
        question_type=question_type,
        seconds_per_question=seconds_per_question,
        question=question,
        answer=answer,
        time_taken=time_taken,
    )

