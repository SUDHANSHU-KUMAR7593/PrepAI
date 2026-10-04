# 🚀 PrepAI — Interview Preparation Notes

A concise, interview-ready cheat sheet explaining the architecture, tech stack, and top questions for PrepAI in simple words.

---

## 1. Project Overview (The 30-Second Answer)
> **"What is PrepAI?"**  
> *"PrepAI is a full-stack, production-grade interview preparation platform built with Python (Flask 3.0), MySQL 8.x (SQLAlchemy 2.x), and Google Gemini AI. It enables candidates to generate custom interview questions (including MCQs and coding challenges), practice under real-time countdown pressure with text or voice, receive instant AI evaluations scored on Clarity, Relevance, and Conciseness, bookmark key questions, and track detailed preparation analytics on a dashboard."*

---

## 2. Tech Stack & Why Chosen

| Component | Technology | Why Chosen? |
| :--- | :--- | :--- |
| **Backend** | **Python / Flask 3.0** | Lightweight, modular, fast JSON endpoints, clean MVC structure. |
| **AI Engine** | **Google Gemini (`gemini-2.5-flash`)** | High inference speed, cost-effective, native support for strict JSON schema output. |
| **Database** | **MySQL 8.x + PyMySQL** | Production relational database, ACID compliance, connection pooling (`pool_pre_ping`), multi-user concurrency. |
| **ORM / Migrations** | **SQLAlchemy 2.x / Flask-Migrate** | Declarative models, relationship cascading, type safety, automated schema migrations. |
| **Auth & Security** | **Flask-Login + Flask-WTF** | Session management, password hashing (`scrypt/pbkdf2`), CSRF protection on forms and APIs. |
| **Frontend** | **HTML5, Vanilla CSS, Vanilla JS** | Fast load times, zero build-step overhead, direct DOM and timer manipulation. |
| **Voice APIs** | **Web Speech API** | Built-in browser speech recognition (Speech-to-Text) and synthesis (Text-to-Speech). |
| **Production** | **Gunicorn WSGI / Render** | Industry-standard production server for Python web applications. |
| **Testing** | **pytest + pytest-flask** | 26 automated unit and integration tests covering models, auth, questions, mock interview, and migration. |

---

## 3. Core Features & How They Work

1. **User Authentication:**  
   Users register and sign in. Passwords are encrypted with salted hashes (`generate_password_hash`). Protected routes use `@login_required` via Flask-Login.
2. **AI Question Generator (`/questions`):**  
   User selects topic, interview type (*Technical, Behavioral, HR, System Design, MCQ, Coding*), difficulty (*Easy, Medium, Hard*), and count. Gemini generates questions with concise model answers or options.
3. **Interactive Practice Mode (`/practice/<id>`):**  
   Flashcard-style interactive practice. Instant checking for MCQs, model answer reveals for open-ended questions, and accuracy tracking.
4. **Timed Mock Interview (`/mock-interview`):**  
   JavaScript presents questions sequentially with a countdown timer (e.g., 120s). When time runs out, the answer is auto-submitted.
5. **Voice Mode (`/voice-interview`):**  
   The browser reads questions aloud (`speechSynthesis`) and transcribes candidate speech in real time (`SpeechRecognition`).
6. **Rubric-Based AI Feedback:**  
   Every answer is evaluated on a 10-point scale across **Clarity**, **Relevance**, and **Conciseness**, alongside identified strengths, improvements, and an ideal answer.
7. **Question Library & Bookmarks (`/library`, `/bookmarks`):**  
   Search, filter, and review previously generated sessions. One-click question bookmarking for targeted revision.
8. **Progress Dashboard (`/dashboard`):**  
   Displays total questions practiced, unique topics covered, accuracy percentage, and weakest topic insights.

---

## 4. Database Design

Managed in MySQL via SQLAlchemy 2.x models with composite indexes:
* **`users`**: `id` (UUID PK), `email` (UNIQUE), `password_hash`, `full_name`, `target_role`, `created_at`, `updated_at`.
* **`question_sessions`**: `id` (UUID PK), `user_id` (FK with CASCADE), `topic`, `question_type`, `difficulty`, `questions` (JSON text), `created_at`.
* **`mock_interviews`**: `id` (UUID PK), `user_id` (FK with CASCADE), `topic`, `role`, `difficulty`, `seconds_per_question`, `items` (JSON text), `overall_score`, `status`, `completed_at`, `created_at`, `updated_at`.
* **`bookmarks`**: `id` (UUID PK), `user_id` (FK with CASCADE), `session_id` (FK with CASCADE), `question_index`, `note`, `created_at`.
* **`practice_attempts`**: `id` (UUID PK), `user_id` (FK with CASCADE), `session_id` (FK), `topic`, `question_type`, `difficulty`, `question_text`, `user_answer`, `correct_answer`, `is_correct`, `score`, `time_taken_seconds`, `created_at`.

> **Key Design Decision:** SQLAlchemy relationships use `cascade="all, delete-orphan"`. Deleting a user safely cascades to delete all their sessions, interviews, bookmarks, and attempts. Connection pooling keeps connection latency minimal.

---

## 5. AI Integration & Prompt Engineering

* **Guaranteed JSON Output:** Instead of parsing unstructured text with regex, PrepAI uses Gemini's structured output mode (`response_schema` / JSON output). The AI cannot return broken markdown or invalid keys.
* **Evaluation Prompt:** Instructs the AI to act as a strict technical interviewer, scoring:
  * **Clarity (0–10):** Was the idea articulated cleanly?
  * **Relevance (0–10):** Did the candidate answer the specific question asked?
  * **Conciseness (0–10):** Was the response focused and free of fluff?
* **Error Handling:** If Gemini returns a 429 rate limit or network timeout, the backend catches the runtime exception and sends a clean error message to the user instead of crashing.

---

## 6. Security & Defensive Coding

* **Password Protection:** Werkzeug's modern cryptographic salted hashing (`scrypt/pbkdf2`). Raw passwords are never stored.
* **CSRF Protection:** Flask-WTF protects all web forms and asynchronous JSON endpoints (`X-CSRFToken` header).
* **Session Security:** `HttpOnly=True` (blocks XSS cookie theft), `SameSite="Lax"` (prevents CSRF), `Secure` (auto-enabled on HTTPS).
* **Data Isolation:** All database queries explicitly filter by `user_id == current_user.id`. Users cannot access or modify each other's sessions.
* **Input Clamping:** Helper functions `clamp_int()` and `clamp_score()` keep numeric inputs (question counts, timers, scores) safely within allowed boundaries. Answers are capped at 5,000 characters.
* **Fail-Fast Database Check:** On application startup, a live MySQL connectivity test executes immediately. If MySQL is unreachable, it raises a clear diagnostic error without falling back to any insecure local storage.
* **Secret Management:** API keys reside in `.env` / cloud environment variables and are excluded from Git via `.gitignore`.

---

## 7. Top 10 Common Interview Questions & Simple Answers

### Q1: "Why did you build PrepAI?"
**Answer:** *"Most candidates prepare passively by reading answers, but freeze in real interviews. PrepAI creates active practice with a countdown timer, voice answering, instant structured feedback, and targeted question library revision."*

### Q2: "What is the high-level architecture?"
**Answer:** *"It's a modern MVC application. Flask handles routing, sessions, and JSON APIs. MySQL with SQLAlchemy handles persistence with connection pooling. Jinja2 and Vanilla JavaScript handle the responsive UI, timers, and browser speech APIs. Google Gemini handles question generation and rubric grading."*

### Q3: "Why choose Flask over Django?"
**Answer:** *"Flask is lightweight and unopinionated. It gave us direct control over routes, custom authentication, and fast JSON endpoints without Django's configuration overhead."*

### Q4: "Why MySQL? How was the migration handled?"
**Answer:** *"We upgraded from SQLite to MySQL to support production concurrency, connection pooling, and multi-user scaling. We engineered a verified, idempotent migration script (`migrate_sqlite_to_mysql.py`) that safely reads SQLite data, validates row counts, and transfers records into MySQL with zero data loss."*

### Q5: "How do you make sure the AI response doesn't break your app?"
**Answer:** *"We enforce strict JSON schema using Gemini's native structured outputs. The API is guaranteed to return valid JSON with our exact expected fields."*

### Q6: "How does the voice feature work?"
**Answer:** *"It uses the browser's native Web Speech API. `SpeechRecognition` transcribes the candidate's speech to text in real time, while `speechSynthesis` reads the questions aloud. No expensive third-party audio service is needed."*

### Q7: "What happens if a user's browser doesn't support speech?"
**Answer:** *"The app checks for `window.SpeechRecognition`. If unavailable (e.g., Firefox without flags), it shows a friendly warning and lets the user practice seamlessly in typed mock interview mode."*

### Q8: "How do you secure user data and sessions?"
**Answer:** *"Passwords use Werkzeug salted hashes. Cookie sessions are hardened with `HttpOnly` and `SameSite`. CSRF tokens protect all state-changing endpoints. All database operations are scoped to `current_user.id` so users can only view their own data."*

### Q9: "Why use PrepAI instead of ChatGPT?"
**Answer:** *"ChatGPT is a generic chat box with no structure. PrepAI provides a complete interview workflow: countdown timers that simulate pressure, voice input/output, a standardized 3-criteria grading rubric, and progress tracking."*

### Q10: "What are the current limitations and what would you build next?"
**Answer:** *"Current areas for expansion: integrating sandboxed code execution (e.g. Pyodide or isolated Docker runners) for live coding challenges, and collaborative peer mock interviews."*
