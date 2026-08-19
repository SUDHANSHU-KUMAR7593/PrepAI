# PrepAI - AI Powered Interview Preparation Platform

PrepAI is a Flask-based web application designed to help candidates practice for technical, behavioral, HR, and system-design interviews. Using AI, the platform generates realistic interview questions, conducts timed mock interviews, provides rubric-based feedback, and tracks user progress locally.

---

## 🚀 Features

* **AI Question Generator:** Dynamically creates customized interview questions based on topic, role, question type, and difficulty level.
* **Timed Mock Interviews:** Simulates real interview pressure with a built-in timer for user submissions.
* **Instant Evaluation:** Reviews written answers using AI to deliver performance scores, highlighting strengths, specific areas for improvement, and a suggested model answer.
* **User Dashboard:** Tracks metrics including total questions practiced, distinct topics covered, and recent session history.
* **Secure Authentication:** Built-in user sign-up and login capabilities with securely hashed passwords.

---

## 🛠️ Tech Stack

* **Backend:** Python, Flask
* **Database:** SQLite (Local storage for users, sessions, and question history)
* **AI Integration:** Groq / OpenAI API (Chat completions for generation and evaluation)
* **Frontend:** HTML5, CSS3, JavaScript (Vanilla JS for browser-side timing and asynchronous API handling)

---

## 📋 System Architecture & Workflow

1. **Setup:** The user authenticates and configures a practice session (selecting topic, difficulty, question count, and time limits).
2. **Generation:** The Flask backend requests contextual questions and model answers from the AI engine.
3. **Execution:** The frontend renders questions one by one, managing the countdown timer.
4. **Evaluation:** Upon submission, the user's answer is evaluated against a structured grading rubric via the AI API.
5. **Persistence:** Results, scores, and feedback logs are written to the local SQLite database and updated on the dashboard.

---

## 📁 Project Structure
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
## 🔧 Getting Started

### Prerequisites
* Python 3.8+
* A Groq or OpenAI API key

### Installation

1. **Clone the repository:**
```bash
git clone [https://github.com/SUDHANSHU-KUMAR7593/PrepAI.git](https://github.com/SUDHANSHU-KUMAR7593/PrepAI.git)
cd PrepAI

2.**Create and activate a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3.**Install the required dependencies:**
```bash
pip install -r requirements.txt

4.**Set up your environment variables (Create a .env file):**
Code snippet
FLASK_SECRET_KEY=your_secret_key_here
AI_API_KEY=your_groq_or_openai_api_key_here

5.**Run the application:**
``bash
python app.py
Open http://127.0.0.1:5000 in your web browser.

---

## 🚀 Future Roadmap

* [ ] **LeetCode Code Execution:** Integrate an isolated sandbox environment to test actual programming solutions and run user code against test cases.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚙️ Deployment

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

## 27. Interview Reading Guide

Use this section as the final checklist before your interview. Read the files in this order because it follows how the application actually works.

### 27.1 Files You Must Read Deeply

#### `app.py`

This is the most important file in the project. If the interviewer asks technical questions, most answers will come from this file.

Read and understand these parts:

- Flask app creation with `app = Flask(__name__)`.
- Environment variable loading using `load_dotenv()`.
- Database path setup with `DATABASE = os.path.join(BASE_DIR, "prepai.sqlite3")`.
- Allowed values:
  - `QUESTION_TYPES`
  - `DIFFICULTIES`
- Session security configuration:
  - `SECRET_KEY`
  - `SESSION_COOKIE_HTTPONLY`
  - `SESSION_COOKIE_SAMESITE`
  - `SESSION_COOKIE_SECURE`
- `now_iso()` for UTC timestamps.
- `get_db()` for opening SQLite connections.
- `init_db()` for creating database tables.
- `current_user()` for reading the logged-in user from the session.
- `inject_user()` for making `current_user` and `year` available in templates.
- `login_required()` for protecting authenticated routes.
- `validate_choice()` for restricting form options.
- `clamp_int()` for safely handling numeric input.
- `ai_config()` for reading AI configuration.
- `call_ai()` for sending requests to the AI provider.
- `parse_tool_args()` for extracting structured AI tool-call responses.
- `generate_ai_question_answers()` for AI question generation with answers.
- `generate_ai_interview_questions()` for mock interview question generation.
- `evaluate_ai_answer()` for AI scoring and feedback.
- `clamp_score()` for keeping AI scores between 0 and 10.
- `/` route for the landing page.
- `/auth` route for signup and signin.
- `/logout` route for signing out.
- `/dashboard` route for user stats and recent sessions.
- `/questions` route for AI question generation.
- `/mock-interview` route for typed mock interview.
- `/voice-interview` route for voice interview.
- `/api/mock-interview/start` API for starting interviews.
- `/api/mock-interview/submit` API for submitting answers and getting feedback.
- `init_db()` at the bottom, which ensures tables exist when the app starts.
- `if __name__ == "__main__"` block for local development.

Interview explanation:

"`app.py` is the core backend. It contains the Flask routes, authentication, SQLite schema creation, AI API integration, question generation, mock interview APIs, answer evaluation, and deployment entry point."

### 27.2 Templates You Must Read

#### `templates/base.html`

This is the shared layout for the app.

Understand:

- Common HTML structure.
- CSS loading from `static/styles.css`.
- Navigation links.
- Conditional UI depending on whether `current_user` exists.
- Flash message rendering through `templates/partials/flash.html`.
- `{% block content %}` where each page inserts its own content.

Interview explanation:

"`base.html` avoids repeating layout code. Other templates extend it and only provide page-specific content."

#### `templates/index.html`

This is the landing page.

Understand:

- What value proposition is shown first.
- Signup/signin links.
- Feature highlights.
- How it uses routes like `url_for('auth', mode='signup')`.

Interview explanation:

"The landing page introduces the product and sends users to authentication."

#### `templates/auth.html`

This file handles the login and signup UI.

Understand:

- How `mode` switches between signin and signup.
- Which fields are submitted to `/auth`.
- Why signup asks for full name but signin does not.
- How errors and success messages appear through flash messages.

Interview explanation:

"The same template supports both signup and signin by checking the `mode` variable passed from Flask."

#### `templates/dashboard.html`

This is shown after login.

Understand:

- Dashboard cards.
- Total generated questions.
- Number of topics practiced.
- Recent question sessions.
- Links to question generation and mock interview.

Interview explanation:

"The dashboard gives users a quick progress view and helps them continue practicing."

#### `templates/questions.html`

This is the AI question generator UI.

Understand:

- Topic input.
- Question type selection.
- Difficulty selection.
- Count selection.
- Result rendering after AI returns questions and model answers.

Interview explanation:

"This page lets users generate personalized interview questions by topic, type, difficulty, and count."

#### `templates/mock_interview.html`

This is the UI for both typed and voice mock interviews.

Understand:

- The same template is used for typed and voice modes.
- `voice` variable controls whether voice features are enabled.
- It loads `static/interview.js`.
- It contains the form for interview setup.
- It contains the question display area.
- It contains the answer input area.
- It contains feedback and summary sections.

Interview explanation:

"The mock interview page is controlled mostly by JavaScript. Flask renders the initial page, and JavaScript handles the interactive interview flow."

#### `templates/partials/flash.html`

This small file renders success and error messages.

Understand:

- It uses Flask flash messages.
- It is included inside `base.html`.

Interview explanation:

"Flash messages provide user feedback after actions like login, signup, logout, or AI errors."

### 27.3 Static Files You Must Read

#### `static/interview.js`

This is the most important frontend logic file.

Understand:

- How the mock interview starts.
- How frontend state is stored.
- How questions are displayed one by one.
- How the timer works with `setInterval`.
- How answer submission calls `/api/mock-interview/submit`.
- How feedback is rendered.
- How the summary is shown after all questions are completed.
- How voice mode uses browser speech recognition.
- How text-to-speech reads questions aloud.
- How errors are displayed to users.

Interview explanation:

"`interview.js` makes the mock interview interactive. It calls backend APIs, manages the timer, captures answers, renders AI feedback, and supports voice features using browser APIs."

#### `static/styles.css`

Read this lightly.

Understand:

- General layout styling.
- Buttons, cards, forms, dashboard, and mock interview styles.
- Responsive design choices.

Interview explanation:

"The CSS keeps the app polished and responsive, but it does not contain business logic."

### 27.4 Deployment Files You Must Know

#### `requirements.txt`

This lists Python dependencies:

- `Flask`: backend web framework.
- `requests`: HTTP calls to AI provider.
- `python-dotenv`: local environment variable loading.
- `gunicorn`: production WSGI server.

Interview explanation:

"`requirements.txt` tells Render which Python packages to install."

#### `render.yaml`

This is the Render deployment configuration.

Understand:

- Runtime is Python.
- Build command is `pip install -r requirements.txt`.
- Start command is `gunicorn app:app`.
- Environment variables are defined but secret values are not committed.

Interview explanation:

"Render reads this file to know how to build and run the app in production."

#### `Procfile`

This contains:

```text
web: gunicorn app:app
```

Interview explanation:

"The Procfile is another deployment convention that tells a platform how to start the web process."

#### `.env.example`

This file shows which environment variables are required without exposing real secrets.

Important variables:

- `SECRET_KEY`
- `AI_API_KEY`
- `AI_GATEWAY_URL`
- `AI_MODEL`

Interview explanation:

"`.env.example` documents required secrets safely. The real `.env` is ignored and must never be pushed to GitHub."

#### `.gitignore`

This prevents unnecessary or sensitive files from being committed.

Important ignored files:

- `.env`
- `.venv/`
- `node_modules/`
- `dist/`
- `*.sqlite3`
- `__pycache__/`
- `*.py[cod]`

Interview explanation:

"`.gitignore` protects secrets, local environments, generated files, dependencies, and local databases from being pushed."

### 27.5 Files You Do Not Need To Explain Deeply

These files are not part of the final Flask deployment:

- `package.json`
- `bun.lock`
- `bunfig.toml`
- `vite.config.ts`
- `tsconfig.json`
- `eslint.config.js`
- `components.json`
- `.prettierrc`
- `.prettierignore`
- `node_modules/`
- `dist/`

How to explain if asked:

"These are leftover frontend tooling files from an earlier or generated setup. The final deployed project is a Flask and Jinja app, so the real runtime files are `app.py`, `templates/`, `static/`, `requirements.txt`, and Render configuration."

Do not say they are wrong. Say they are not required for the current deployment.

### 27.6 Database Design To Understand

The app uses SQLite with three main tables.

#### `users`

Stores:

- User ID.
- Email.
- Hashed password.
- Full name.
- Target role.
- Created and updated timestamps.

Important point:

Raw passwords are never stored. Passwords are hashed using Werkzeug.

#### `question_sessions`

Stores:

- Generated question session ID.
- User ID.
- Topic.
- Question type.
- Difficulty.
- Generated questions as JSON text.
- Created timestamp.

Important point:

Questions are stored as JSON text for MVP simplicity.

#### `mock_interviews`

Stores:

- Interview ID.
- User ID.
- Topic.
- Role.
- Difficulty.
- Question type.
- Seconds per question.
- Interview items as JSON text.
- Overall score.
- Status.
- Completed timestamp.
- Created and updated timestamps.

Important point:

Each item stores question, answer, feedback, score, and time taken.

Interview explanation:

"SQLite was chosen because it is simple for an MVP. For production scale, I would move to PostgreSQL."

### 27.7 Authentication Flow

Signup flow:

1. User opens `/auth?mode=signup`.
2. User submits email, password, and full name.
3. Flask validates password length.
4. Password is hashed with `generate_password_hash`.
5. User is inserted into the `users` table.
6. User ID is stored in Flask session.
7. User is redirected to dashboard.

Signin flow:

1. User opens `/auth?mode=signin`.
2. User submits email and password.
3. Flask finds the user by email.
4. `check_password_hash` verifies the password.
5. User ID is stored in session.
6. User is redirected to dashboard.

Logout flow:

1. User submits the logout form.
2. Flask clears the session.
3. User is redirected to landing page.

Interview explanation:

"Authentication uses Flask sessions and Werkzeug password hashing. Protected pages use the `login_required` decorator."

### 27.8 AI Question Generation Flow

1. User opens `/questions`.
2. User enters topic, type, difficulty, and count.
3. Flask validates the input.
4. Backend calls `generate_ai_question_answers`.
5. That function creates a structured tool-calling prompt.
6. `call_ai` sends the request to the AI provider.
7. `parse_tool_args` extracts structured JSON.
8. Questions and model answers are saved in SQLite.
9. User sees the generated results.

Interview explanation:

"The app does not rely on random free-form AI text. It asks the model to return structured tool-call arguments, which makes parsing more reliable."

### 27.9 Mock Interview Flow

1. User opens `/mock-interview` or `/voice-interview`.
2. User chooses topic, role, question type, difficulty, count, and time.
3. JavaScript calls `/api/mock-interview/start`.
4. Flask generates interview questions with AI.
5. Questions are stored in `mock_interviews`.
6. JavaScript displays the first question.
7. Timer starts.
8. User submits an answer or time expires.
9. JavaScript calls `/api/mock-interview/submit`.
10. Flask sends the answer to AI for evaluation.
11. AI returns score, rubric, strengths, improvements, and ideal answer.
12. Flask stores feedback in SQLite.
13. JavaScript shows the feedback.
14. User continues until all questions are completed.
15. App shows overall score and summary.

Interview explanation:

"The mock interview flow combines Flask APIs, browser JavaScript, a timer, AI evaluation, and database persistence."

### 27.10 Voice Interview Flow

Voice mode uses browser APIs:

- `SpeechRecognition` or `webkitSpeechRecognition` for speech-to-text.
- `speechSynthesis` for text-to-speech.

Important limitations:

- Voice support depends on browser.
- Microphone permission is required.
- HTTPS is usually required in production.
- Typed mock interview is the fallback.

Interview explanation:

"Voice mode makes the interview feel closer to a real spoken interview, but it depends on browser support."

### 27.11 Security Points To Mention

Implemented:

- Password hashing with Werkzeug.
- Real API key stored in environment variables, not GitHub.
- `.env` ignored by Git.
- Session cookies are `HttpOnly`.
- `SameSite=Lax` is enabled.
- Secure cookies are enabled on Render.
- Routes are protected with `login_required`.
- Queries filter by `user_id`.
- Numeric inputs are clamped.
- AI score values are clamped between 0 and 10.

Limitations:

- No CSRF protection package yet.
- No rate limiting yet.
- No email verification.
- No password reset flow.
- SQLite is not ideal for high-scale production.
- AI feedback can be imperfect.

Interview explanation:

"The app has basic MVP security, but for production I would add CSRF protection, rate limiting, password reset, monitoring, and PostgreSQL."

### 27.12 Deployment Explanation

Deployment uses Render.

Render steps:

1. Connect GitHub repository.
2. Install packages from `requirements.txt`.
3. Start the app with `gunicorn app:app`.
4. Add environment variables in Render.

Required Render environment variables:

- `SECRET_KEY`
- `AI_API_KEY`
- `AI_GATEWAY_URL`
- `AI_MODEL`

Important:

Do not push `.env` to GitHub. Add the real API key only in Render's environment variable settings.

Interview explanation:

"The app is deployed as a Python web service. Render installs dependencies and runs the Flask app through Gunicorn."

### 27.13 Things To Say If Asked About Unused Files

Question:

"Why are there Bun, Vite, or package files?"

Answer:

"Those files came from an earlier or generated frontend setup. During final implementation, I simplified the project to a Flask server-rendered app using Jinja templates and plain JavaScript. The deployed app does not depend on those files."

Question:

"Did you push unnecessary files?"

Answer:

"No. The GitHub repo contains only the Flask app, templates, static assets, Python requirements, deployment files, README, `.env.example`, and `.gitignore`. Local-only generated or unused files are ignored."

### 27.14 Most Important Functions To Revise

Revise these functions from `app.py`:

- `init_db()`
- `current_user()`
- `login_required()`
- `validate_choice()`
- `clamp_int()`
- `ai_config()`
- `call_ai()`
- `parse_tool_args()`
- `generate_ai_question_answers()`
- `generate_ai_interview_questions()`
- `evaluate_ai_answer()`
- `clamp_score()`
- `auth()`
- `dashboard()`
- `questions()`
- `api_start_mock_interview()`
- `api_submit_answer()`

For each function, know:

- What input it receives.
- What it returns.
- Whether it talks to database, AI, session, template, or JSON API.
- What can go wrong.
- How errors are handled.

### 27.15 Questions Interviewers May Ask

#### What is PrepAI?

PrepAI is an AI-powered interview preparation platform that helps users generate personalized interview questions, practice timed mock interviews, receive structured AI feedback, and track preparation progress.

#### Why did you build it?

Many students prepare passively by reading questions. PrepAI helps them actively practice answering under time pressure and receive instant feedback.

#### What tech stack did you use?

Flask, SQLite, Jinja templates, HTML, CSS, JavaScript, browser speech APIs, Requests, python-dotenv, Gunicorn, and Render.

#### Why Flask?

Flask is lightweight, simple, and fast for building an MVP. It provides enough control for routes, authentication, database access, templates, and APIs.

#### Why SQLite?

SQLite is simple and good for local development and MVPs. For production scale, PostgreSQL would be better.

#### How does AI integration work?

The backend reads the AI key from environment variables, sends a structured request to the AI provider, and parses tool-call JSON responses to get questions or feedback.

#### How do you protect the API key?

The real API key stays in `.env` locally and in Render environment variables in production. `.env` is ignored by Git and is not pushed to GitHub.

#### How do you store passwords?

Passwords are hashed using Werkzeug. The raw password is never stored.

#### How do you prevent one user from seeing another user's data?

Protected routes require login, and database queries filter records using the current user's `user_id`.

#### What happens if AI fails?

The backend catches runtime errors and shows a clear error message to the user. API routes return JSON errors.

#### What are the limitations?

SQLite persistence on cloud platforms, no CSRF package yet, no rate limiting, no password reset, browser-dependent voice support, and AI feedback may not always be perfect.

#### How would you improve it?

Add PostgreSQL, tests, CSRF protection, rate limiting, analytics, resume-based questions, company-specific preparation, PDF reports, and an admin dashboard.

### 27.16 One-Minute Technical Explanation

"PrepAI is a Flask-based interview preparation app. `app.py` handles routing, authentication, SQLite database setup, AI integration, question generation, and mock interview APIs. The UI is rendered with Jinja templates inside `templates/`, while `static/interview.js` manages the interactive mock interview timer, answer submission, feedback rendering, and voice features. The app stores users, generated question sessions, and mock interview records in SQLite. For AI, the backend calls a Groq-compatible OpenAI-style endpoint and uses structured tool-calling responses so generated questions and feedback can be parsed reliably. It is deployed on Render using `gunicorn app:app`, with secrets stored in environment variables."

### 27.17 Two-Minute Product Explanation

"PrepAI solves the problem of unstructured interview preparation. Students often read questions but do not practice answering under realistic conditions or get feedback. In PrepAI, a user signs in, generates interview questions by topic and difficulty, practices a timed mock interview, submits typed or spoken answers, and receives AI feedback with scores, strengths, improvements, and an ideal answer. The dashboard tracks recent practice sessions. The MVP is built with Flask, SQLite, Jinja templates, JavaScript, and an AI API. It is simple enough to deploy, but the idea can scale with PostgreSQL, analytics, institution dashboards, resume-based questions, and role-specific learning paths."

### 27.18 Final Day Revision Checklist

Before the interview, make sure you can explain:

- What problem PrepAI solves.
- Who the target users are.
- Why Flask was chosen.
- Why SQLite was chosen for MVP.
- How signup and signin work.
- How password hashing works.
- How `login_required` protects routes.
- How AI question generation works.
- How AI answer evaluation works.
- Why tool-calling style responses are useful.
- How mock interview timer works.
- How voice mode works.
- What files are required for deployment.
- Why `.env` is not pushed.
- What limitations exist.
- What production improvements you would make.
- What files are unused leftovers and why they are not part of deployment.

### 27.19 Files To Open During Revision

Open these files in VS Code while preparing:

```text
README.md
app.py
templates/base.html
templates/auth.html
templates/dashboard.html
templates/questions.html
templates/mock_interview.html
templates/partials/flash.html
static/interview.js
static/styles.css
requirements.txt
render.yaml
Procfile
.env.example
.gitignore
```

You do not need to revise these deeply:

```text
package.json
bun.lock
bunfig.toml
vite.config.ts
tsconfig.json
eslint.config.js
components.json
.prettierrc
.prettierignore
node_modules/
dist/
.venv/
__pycache__/
prepai.sqlite3
```

### 27.20 Best Closing Answer

"This project shows that I can build a complete AI-powered web application: authentication, database design, server-rendered frontend, JavaScript interactivity, AI API integration, deployment configuration, and product thinking. I also understand its limitations and how I would improve it for production."
>>>>>>> Stashed changes
