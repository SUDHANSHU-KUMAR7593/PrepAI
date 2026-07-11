# PrepAI - AI Interview Preparation Platform

PrepAI is a Flask-based interview preparation web application that helps students and job seekers practice for technical, behavioral, HR, and system-design interviews. It uses AI to generate realistic interview questions, runs timed mock interviews, evaluates user answers with rubric-based feedback, and stores practice history in a local SQLite database.

This README is written as both a developer guide and a presentation preparation document. It explains what the project does, how it works, why key decisions were made, and how to answer common interview or CEO-level questions about the product.

## 1. Executive Summary

PrepAI solves a practical problem: many candidates know what to study, but they do not get enough realistic interview practice or immediate feedback. The application gives users a focused interview-prep workspace where they can:

- Generate AI-created interview questions by topic, question type, difficulty, and count.
- Practice timed mock interviews.
- Submit written or spoken answers.
- Receive structured AI feedback with a score, strengths, improvements, and a suitable model answer.
- Track previous question sessions and progress from a dashboard.

The current version is designed as a lightweight, deployable MVP using Flask, SQLite, server-side rendering, browser JavaScript, and Groq-compatible OpenAI-style chat completions.

## 2. Problem Statement

Interview preparation is often unstructured. Candidates usually rely on static question banks, YouTube videos, or manual notes. These methods have limitations:

- They are not personalized to a target topic or role.
- They do not simulate timed interview pressure.
- They rarely provide instant feedback.
- They do not help users understand what was strong or weak in their answer.
- They do not maintain a simple practice history.

PrepAI addresses this by combining AI question generation, timed practice, answer evaluation, and progress tracking into one web application.

## 3. Target Users

Primary users:

- College students preparing for placements.
- Freshers applying for internships or entry-level jobs.
- Candidates preparing for technical interviews.
- Candidates practicing HR, behavioral, or communication rounds.

Secondary users:

- Training and placement departments.
- Coaching centers.
- Bootcamps.
- Career mentors.

## 4. Core Value Proposition

PrepAI gives candidates a repeatable interview practice loop:

1. Choose a topic, role, difficulty, and question type.
2. Get realistic AI-generated questions.
3. Answer under time pressure.
4. Receive immediate structured feedback.
5. Review improvements and model answers.
6. Repeat and track progress.

This makes interview practice more active, personalized, and measurable.

## 5. Key Features

### 5.1 User Authentication

Users can sign up, sign in, and sign out. Passwords are not stored directly. They are hashed using Werkzeug security utilities.

Relevant code:

- `app.py`: `/auth`, `/logout`, `current_user`, `login_required`
- `users` table in SQLite

### 5.2 Dashboard

After login, users see a dashboard showing:

- Recent question-generation sessions.
- Total number of questions practiced.
- Number of unique topics covered.

Relevant code:

- `app.py`: `/dashboard`
- `templates/dashboard.html`

### 5.3 AI Question Generator

Users can generate questions by selecting:

- Topic or role.
- Question type: technical, behavioral, HR, or system design.
- Difficulty: easy, medium, or hard.
- Count: 3 to 10 questions.

The AI returns each question with a concise model answer.

Relevant code:

- `app.py`: `/questions`
- `generate_ai_question_answers`
- `templates/questions.html`

### 5.4 Timed Mock Interview

The mock interview mode creates a timed Q&A session. The user answers one question at a time and receives feedback after each submission.

Configurable options:

- Topic.
- Target role.
- Question type.
- Difficulty.
- Number of questions.
- Seconds per question.

Relevant code:

- `app.py`: `/mock-interview`
- `app.py`: `/api/mock-interview/start`
- `app.py`: `/api/mock-interview/submit`
- `static/interview.js`
- `templates/mock_interview.html`

### 5.5 Voice Mock Interview

The voice interview mode uses browser speech APIs:

- `SpeechRecognition` or `webkitSpeechRecognition` for speech-to-text.
- `speechSynthesis` for reading questions aloud.

This helps users practice speaking, not just typing.

Important note: voice support depends on the browser. Chrome, Edge, and Safari desktop usually provide better support.

Relevant code:

- `app.py`: `/voice-interview`
- `static/interview.js`: voice recognition and speech synthesis functions

### 5.6 AI-Based Feedback

For every submitted mock interview answer, the AI evaluates:

- Overall score.
- Clarity.
- Relevance.
- Conciseness.
- Strengths.
- Improvements.
- Ideal or suitable answer.

This turns the app from a simple question generator into a feedback-driven learning system.

Relevant code:

- `evaluate_ai_answer`
- `/api/mock-interview/submit`

## 6. Tech Stack

### Backend

- Python
- Flask
- SQLite
- Werkzeug password hashing
- Requests library for AI API calls
- python-dotenv for local environment variables
- Gunicorn for production serving

### Frontend

- HTML templates with Jinja2
- CSS in `static/styles.css`
- JavaScript in `static/interview.js`
- Browser speech APIs for voice interview mode

### AI Provider

- Groq API using an OpenAI-compatible chat completions endpoint.
- Default model: `llama-3.3-70b-versatile`

### Deployment

- Render-compatible configuration with:
  - `render.yaml`
  - `Procfile`
  - `gunicorn app:app`

## 7. Project Structure

```text
interview-ace-main/
├── app.py
├── prepai.sqlite3
├── requirements.txt
├── Procfile
├── render.yaml
├── .env.example
├── static/
│   ├── interview.js
│   └── styles.css
└── templates/
    ├── auth.html
    ├── base.html
    ├── dashboard.html
    ├── index.html
    ├── mock_interview.html
    ├── questions.html
    └── partials/
        └── flash.html
```

## 8. Application Flow

### Public Flow

1. User opens the landing page.
2. User signs up or signs in.
3. Authenticated user is redirected to the dashboard.

### Question Generator Flow

1. User enters a topic.
2. User selects type, difficulty, and count.
3. Flask validates the request.
4. Backend calls the AI provider.
5. AI returns structured questions and answers.
6. Results are saved in SQLite.
7. User sees generated questions in the UI.

### Mock Interview Flow

1. User starts a mock interview.
2. Backend generates interview questions with AI.
3. Questions are stored in `mock_interviews`.
4. Frontend displays one question at a time.
5. Timer starts for each question.
6. User submits an answer or time expires.
7. Backend sends question, answer, topic, difficulty, and time taken to AI.
8. AI returns score and feedback.
9. Backend stores feedback.
10. User continues until all questions are completed.
11. Summary page displays overall performance.

## 9. Database Design

The app uses SQLite with three main tables.

### `users`

Stores account information:

- `id`
- `email`
- `password_hash`
- `full_name`
- `target_role`
- `created_at`
- `updated_at`

### `question_sessions`

Stores generated question sets:

- `id`
- `user_id`
- `topic`
- `question_type`
- `difficulty`
- `questions` as JSON text
- `created_at`

### `mock_interviews`

Stores mock interview sessions:

- `id`
- `user_id`
- `topic`
- `role`
- `difficulty`
- `question_type`
- `seconds_per_question`
- `items` as JSON text
- `overall_score`
- `status`
- `completed_at`
- `created_at`
- `updated_at`

## 10. Security Considerations

Implemented security practices:

- Passwords are hashed using Werkzeug.
- Sessions use Flask's signed session mechanism.
- Cookies are configured with `HttpOnly`.
- `SameSite=Lax` is enabled.
- Secure cookies are enabled automatically on Render.
- Environment variables are used for secrets.
- `.env` should not be committed.
- User-specific queries filter by `user_id`.

Current limitations:

- No email verification.
- No password reset flow.
- No CSRF protection package is currently used.
- No rate limiting for login or AI requests.
- SQLite is not ideal for high-scale production usage.

Production improvements:

- Add Flask-WTF or another CSRF protection mechanism.
- Add rate limiting with Flask-Limiter.
- Move from SQLite to PostgreSQL.
- Add stronger validation and monitoring.
- Add audit logs for sensitive actions.

## 11. AI Integration Details

The AI integration is centralized in `app.py`.

Main functions:

- `ai_config()`: reads AI settings from environment variables.
- `call_ai(payload)`: sends request to the AI gateway.
- `parse_tool_args(payload)`: extracts structured tool-call responses.
- `generate_ai_question_answers(...)`: generates question-answer pairs.
- `generate_ai_interview_questions(...)`: generates mock interview questions.
- `evaluate_ai_answer(...)`: scores and evaluates user answers.

The app uses function/tool calling style responses to make the AI return structured JSON instead of unpredictable plain text. This makes parsing more reliable.

## 12. Environment Variables

Create a `.env` file locally based on `.env.example`.

Required:

```text
SECRET_KEY=<long-random-secret>
AI_API_KEY=<your-groq-api-key>
AI_GATEWAY_URL=https://api.groq.com/openai/v1/chat/completions
AI_MODEL=llama-3.3-70b-versatile
```

Optional:

```text
PORT=5000
FLASK_DEBUG=true
SESSION_COOKIE_SECURE=true
```

Important: never commit the real `.env` file.

## 13. Local Setup

### 13.1 Create Virtual Environment

```bash
python -m venv .venv
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 13.2 Install Dependencies

```bash
pip install -r requirements.txt
```

### 13.3 Configure Environment

```bash
copy .env.example .env
```

Then add the real values in `.env`.

### 13.4 Run the App

```bash
python app.py
```

Open:

```text
http://localhost:5000
```

## 14. Deployment on Render

This repository already includes Render deployment files.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app
```

Environment variables to add in Render:

```text
SECRET_KEY=<long-random-secret>
AI_API_KEY=<your-groq-api-key>
AI_GATEWAY_URL=https://api.groq.com/openai/v1/chat/completions
AI_MODEL=llama-3.3-70b-versatile
```

Important Render note:

The current app uses SQLite. On many cloud platforms, local SQLite files may reset when the service redeploys or restarts unless persistent storage is attached. For production, PostgreSQL is recommended.

## 15. Demo Script for Presentation

Use this flow when presenting to CEOs, judges, or interviewers.

### 15.1 Opening Pitch

"PrepAI is an AI-powered interview preparation platform for students and job seekers. It helps users generate personalized interview questions, practice timed mock interviews, receive structured feedback, and track their preparation progress from one dashboard."

### 15.2 Problem

"Most candidates prepare using static resources. They read questions but do not practice answering under pressure. They also do not get instant feedback. PrepAI closes that gap by creating a realistic practice loop."

### 15.3 Solution

"The user selects a topic, interview type, difficulty, and question count. The app generates relevant questions using AI. In mock interview mode, the user answers under a timer and receives feedback scored on clarity, relevance, and conciseness."

### 15.4 Live Demo Path

1. Open landing page.
2. Sign up or sign in.
3. Show dashboard metrics.
4. Go to AI Question Generator.
5. Generate questions for a topic like `React hooks`, `Operating Systems`, or `Data Structures`.
6. Show generated model answers.
7. Go to Mock Interview.
8. Start a timed session.
9. Submit an answer.
10. Show AI feedback, rubric, strengths, improvements, and suitable answer.
11. Optionally show Voice Mock Interview.

### 15.5 Closing Statement

"The MVP proves that personalized interview practice can be made faster, more accessible, and more measurable. With production upgrades like PostgreSQL, analytics, organization accounts, and role-specific roadmaps, this can become a scalable placement-preparation product."

## 16. CEO-Level Questions and Strong Answers

### Q1. What problem are you solving?

PrepAI solves the lack of personalized, feedback-driven interview practice. Candidates often read questions passively, but interviews require active answering, time management, communication, and improvement through feedback.

### Q2. Who is your customer?

The primary customer is a student or job seeker preparing for placements or interviews. A broader business customer could be a college placement cell, bootcamp, or training institute that wants to help many candidates practice consistently.

### Q3. What makes this different from ChatGPT?

ChatGPT is a general-purpose assistant. PrepAI is a focused workflow product. It provides structured interview modes, timers, session history, scoring rubrics, dashboards, and a repeatable preparation journey. The value is not only the AI response, but the product experience around interview practice.

### Q4. Why did you choose Flask?

Flask is lightweight, fast to develop with, and suitable for an MVP. It gives enough flexibility to build routes, authentication, database access, and API endpoints without unnecessary complexity.

### Q5. Why SQLite?

SQLite is simple, file-based, and excellent for prototyping. It removes the setup burden during MVP development. For production scale, I would migrate to PostgreSQL.

### Q6. Is this production ready?

It is MVP-ready, not fully enterprise production-ready. The core product flow works, but before production scaling I would add PostgreSQL, CSRF protection, rate limiting, password reset, monitoring, logging, automated tests, and stronger admin controls.

### Q7. How does the AI feedback work?

When the user submits an answer, the backend sends the topic, difficulty, question type, question, answer, and time taken to the AI model. The AI is instructed to return structured feedback including score, clarity, relevance, conciseness, strengths, improvements, and an ideal answer.

### Q8. How do you make AI output reliable?

The app uses tool/function calling style prompts. Instead of asking for free-form text, it defines a structured response schema. The backend then parses the returned JSON arguments and validates important fields.

### Q9. What happens if the AI API fails?

The backend catches AI runtime errors and returns an error message to the user. Specific cases like rate limits or exhausted credits are handled with clearer messages.

### Q10. How are passwords stored?

Passwords are hashed using Werkzeug's password hashing utilities. The raw password is never stored in the database.

### Q11. How do you prevent users from seeing other users' data?

Protected routes require login. Database queries for sessions and mock interviews include the current user's `user_id`, so each user can access only their own records.

### Q12. Why did you add voice interview mode?

Real interviews are spoken conversations. Voice mode helps users practice verbal communication, not just written answers. It uses browser speech recognition and text-to-speech to simulate a more natural interview experience.

### Q13. What are the main limitations?

The main limitations are SQLite persistence on cloud platforms, dependency on an external AI provider, browser-dependent voice support, no CSRF package, and no advanced analytics yet.

### Q14. How would you monetize this?

Possible monetization models:

- Freemium plan with limited practice sessions.
- Premium subscription for unlimited mock interviews.
- College or bootcamp licensing.
- Role-specific preparation packs.
- Analytics dashboard for training institutions.

### Q15. What metrics would you track?

Important metrics:

- Daily active users.
- Number of generated question sessions.
- Number of completed mock interviews.
- Average score improvement over time.
- Most practiced topics.
- User retention.
- Conversion from free to paid plans.

### Q16. How would you scale this?

I would move the database to PostgreSQL, add background jobs for heavier AI workflows, cache repeated prompts, add rate limiting, use proper observability, and deploy behind a production-grade WSGI server with autoscaling.

### Q17. How do you control AI cost?

I would limit question count, add user quotas, cache common question sets, monitor token usage, and choose cost-effective models depending on the task. For example, generation can use a cheaper model while detailed evaluation can use a stronger model.

### Q18. How would you improve accuracy?

I would improve prompts, add role-specific rubrics, use curated evaluation criteria, compare AI scores with human evaluator samples, and allow users to report poor feedback.

### Q19. What is your product roadmap?

Short-term:

- Better UI polish.
- More detailed progress analytics.
- Export interview reports.
- Add tests.

Medium-term:

- PostgreSQL migration.
- Role-specific interview tracks.
- Resume-based question generation.
- Company-specific preparation.

Long-term:

- Institution dashboards.
- Mentor review workflows.
- Adaptive learning plans.
- Mobile app or PWA.

### Q20. What did you personally learn from building this?

This project demonstrates full-stack development, authentication, database design, API integration, AI prompt design, frontend state management, deployment configuration, and product thinking. It also shows how AI can be wrapped inside a focused workflow to solve a specific user problem.

## 17. Technical Interview Questions and Answers

### Q1. Explain the architecture.

The app uses a Flask backend with server-rendered Jinja templates. SQLite stores users, generated question sessions, and mock interview records. The frontend uses JavaScript for the interactive mock interview timer, answer submission, feedback rendering, and voice features. The backend communicates with the AI provider through HTTP requests.

### Q2. What is the purpose of `login_required`?

`login_required` is a decorator that protects routes. If a user is not signed in, it redirects them to the signin page. This prevents unauthenticated access to dashboard, question generation, and interview features.

### Q3. How is input validated?

The backend validates question type and difficulty using allowed sets. It clamps numeric values such as question count and seconds per question to safe minimum and maximum ranges.

### Q4. Why use JSON text columns for questions and interview items?

For an MVP, storing generated questions and interview items as JSON text keeps the schema simple. In a larger production system, these could be normalized into separate `questions`, `answers`, and `feedback` tables for better querying.

### Q5. What is `clamp_int` used for?

`clamp_int` safely converts input to an integer and restricts it to an allowed range. This prevents invalid values like negative question counts or extremely long timers.

### Q6. What is `clamp_score` used for?

`clamp_score` ensures AI-generated scores stay between 0 and 10. This protects the UI and database from invalid AI output.

### Q7. How does the timer work?

The timer is implemented in `static/interview.js` using `setInterval`. It decreases `timeLeft` every second, updates the progress bar, and automatically submits the answer when time reaches zero.

### Q8. How does the voice feature work?

The app checks for browser support for `SpeechRecognition` or `webkitSpeechRecognition`. It captures final and interim speech transcripts, displays them to the user, and submits the combined transcript as the answer. It also uses `speechSynthesis` to read questions aloud.

### Q9. What is the role of `init_db()`?

`init_db()` creates required database tables and indexes if they do not already exist. It runs when the app starts, making local setup easier.

### Q10. How does deployment work?

Render installs dependencies from `requirements.txt` and starts the app with `gunicorn app:app`. Environment variables are configured in Render, not committed to source code.

## 18. Business Pitch

PrepAI can become a scalable career-preparation product because interview preparation is a repeated, high-anxiety, high-value activity. Students and job seekers are willing to invest time and money if the product clearly improves confidence and performance.

The strongest business angle is B2B2C:

- Colleges want better placement outcomes.
- Bootcamps want measurable student readiness.
- Students want personalized practice.
- PrepAI can provide practice, analytics, and progress reports.

## 19. Competitive Positioning

Compared with static question banks:

- PrepAI is personalized and interactive.

Compared with general AI chatbots:

- PrepAI is structured around interview workflows.

Compared with human mock interviews:

- PrepAI is available anytime and cheaper to scale.

Compared with video courses:

- PrepAI requires active answering and gives feedback.

## 20. Future Enhancements

High-impact enhancements:

- Resume upload and resume-based questions.
- Company-specific interview sets.
- Role-specific learning paths.
- PostgreSQL production database.
- Admin dashboard for colleges.
- PDF export of interview reports.
- Email reports after each interview.
- Streaks and goals.
- Better analytics charts.
- Human mentor review option.
- Payment integration.
- Multi-language support.
- Automated tests and CI/CD pipeline.

## 21. Known Limitations

- SQLite database may reset on some cloud deployments without persistent storage.
- Voice recognition quality depends on browser and microphone permissions.
- AI feedback can be imperfect and should be treated as guidance, not a final judgment.
- No automated test suite is currently included.
- No CSRF library is currently configured.
- No payment, admin, or analytics module yet.

## 22. How to Explain the Code in 60 Seconds

"The application is built with Flask. `app.py` contains the routes, authentication, database setup, AI integration, and mock interview APIs. Templates inside `templates/` render the pages. `static/interview.js` manages the interactive interview experience, including the timer, answer submission, feedback rendering, and voice mode. SQLite stores users, question sessions, and mock interviews. The AI provider generates questions and evaluates answers using structured tool-calling responses."

## 23. How to Explain the Product in 30 Seconds

"PrepAI is an AI interview preparation platform. A user can generate role-specific questions, take a timed mock interview, answer by typing or speaking, and receive instant feedback scored on clarity, relevance, and conciseness. It helps candidates move from passive preparation to active, measurable practice."

## 24. Quick Troubleshooting

### AI API key missing

Error:

```text
AI_API_KEY is missing
```

Fix:

- Add `AI_API_KEY` to `.env`.
- Restart Flask.

### AI rate limit

Error:

```text
Rate limit hit. Try again shortly.
```

Fix:

- Wait and retry.
- Check Groq account limits.
- Reduce repeated calls during demo.

### Voice input not working

Fix:

- Use Chrome, Edge, or Safari desktop.
- Allow microphone permission.
- Use HTTPS in production.
- Try typed mock interview mode as a fallback.

### Database issues

Fix:

- Ensure the app has write permission in the project directory.
- Delete local `prepai.sqlite3` only if you intentionally want a fresh database.
- Restart the app so `init_db()` can recreate tables.

## 25. Final Presentation Checklist

Before presenting:

- Confirm `.env` has a valid `AI_API_KEY`.
- Run the app locally.
- Create a test account.
- Generate one question set successfully.
- Complete one mock interview answer.
- Test the voice mode only if the browser supports it.
- Prepare fallback screenshots or typed demo in case the AI API is slow.
- Keep one strong topic ready, such as `Data Structures`, `React`, `Operating Systems`, or `Behavioral interview for software engineer`.

## 26. Best One-Line Answer

"PrepAI is a focused AI interview preparation platform that turns static studying into timed, personalized, feedback-driven practice."
