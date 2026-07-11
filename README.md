# PrepAI - AI Interview Preparation Platform

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
