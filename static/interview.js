const root = document.getElementById("interview-app");
const isVoice = root?.dataset.voice === "true";

const state = {
  phase: "setup",
  interviewId: null,
  questions: [],
  index: 0,
  seconds: 120,
  timeLeft: 120,
  timerId: null,
  startedAt: 0,
  feedback: null,
  history: [],
  transcript: "",
  interim: "",
  recognition: null,
  listening: false,
};

const $ = (id) => document.getElementById(id);
function show(id) {
  ["setup-view", "interview-view", "summary-view"].forEach((view) => $(view).classList.toggle("hidden", view !== id));
}
function toast(message) {
  const node = document.createElement("div");
  node.className = "flash success runtime";
  node.textContent = message;
  document.body.appendChild(node);
  setTimeout(() => node.remove(), 2600);
}
function api(path, body) {
  return fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async (response) => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || "Request failed");
    return payload;
  });
}

function formatTime(value) {
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;
}

function startTimer() {
  clearInterval(state.timerId);
  state.startedAt = Date.now();
  state.timeLeft = state.seconds;
  renderTimer();
  state.timerId = setInterval(() => {
    if (state.feedback) return;
    state.timeLeft -= 1;
    renderTimer();
    if (state.timeLeft <= 0) {
      clearInterval(state.timerId);
      submitAnswer(true);
    }
  }, 1000);
}

function renderTimer() {
  $("timer").textContent = formatTime(Math.max(0, state.timeLeft));
  $("progress-bar").style.width = `${Math.max(0, (state.timeLeft / state.seconds) * 100)}%`;
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function recognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function renderVoice() {
  if (!isVoice) return;
  const full = `${state.transcript}${state.interim ? " " + state.interim : ""}`.trim();
  $("transcript").textContent = full || "Your spoken answer will appear here...";
  $("mic-dot").classList.toggle("live", state.listening);
  $("mic-label").textContent = state.listening ? "Listening..." : "Mic off";
  $("mic-toggle").textContent = state.listening ? "Stop" : "Speak";
}

function startListening() {
  const Ctor = recognitionCtor();
  if (!Ctor) {
    toast("Voice input is not supported in this browser.");
    return;
  }
  const recognition = new Ctor();
  recognition.lang = "en-US";
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.onresult = (event) => {
    let finalText = "";
    let interimText = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (result.isFinal) finalText += result[0].transcript;
      else interimText += result[0].transcript;
    }
    if (finalText) state.transcript = `${state.transcript} ${finalText.trim()}`.trim();
    state.interim = interimText;
    renderVoice();
  };
  recognition.onend = () => {
    state.listening = false;
    renderVoice();
  };
  state.recognition = recognition;
  recognition.start();
  state.listening = true;
  renderVoice();
}

function stopListening() {
  try {
    state.recognition?.stop();
  } catch {}
  state.listening = false;
  renderVoice();
}

function currentAnswer() {
  if (!isVoice) return $("answer").value.trim();
  return `${state.transcript}${state.interim ? " " + state.interim : ""}`.trim();
}

function renderQuestion() {
  state.feedback = null;
  $("question-count").textContent = `Question ${state.index + 1} of ${state.questions.length}`;
  $("question-text").textContent = state.questions[state.index];
  $("feedback-card").classList.add("hidden");
  $("answer-actions").classList.remove("hidden");
  $("next-question").textContent = state.index + 1 >= state.questions.length ? "View summary" : "Next question";
  if (isVoice) {
    state.transcript = "";
    state.interim = "";
    renderVoice();
    if ($("auto-speak")?.checked) speak(state.questions[state.index]);
  } else {
    $("answer").value = "";
    $("answer").disabled = false;
  }
  startTimer();
}

function renderRubric(rubric) {
  $("rubric").innerHTML = ["clarity", "relevance", "conciseness"]
    .map((key) => {
      const label = key.charAt(0).toUpperCase() + key.slice(1);
      const value = Number(rubric[key] || 0).toFixed(1);
      const note = rubric[`${key}_note`] || "";
      return `<div><strong>${label}<span>${value} / 10</span></strong><i style="width:${value * 10}%"></i><p>${note}</p></div>`;
    })
    .join("");
}

function renderFeedback(feedback) {
  state.feedback = feedback;
  clearInterval(state.timerId);
  if (isVoice) stopListening();
  else $("answer").disabled = true;
  $("answer-actions").classList.add("hidden");
  $("feedback-card").classList.remove("hidden");
  $("feedback-score").textContent = `${Number(feedback.score).toFixed(1)} / 10`;
  renderRubric(feedback.rubric);
  $("feedback-strengths").textContent = feedback.strengths;
  $("feedback-improvements").textContent = feedback.improvements;
  $("feedback-ideal").textContent = feedback.idealAnswer;
}

async function submitAnswer(timedOut = false) {
  const answer = currentAnswer();
  const elapsed = Math.min(state.seconds, Math.round((Date.now() - state.startedAt) / 1000));
  $("submit-answer").disabled = true;
  try {
    const feedback = await api("/api/mock-interview/submit", {
      interviewId: state.interviewId,
      index: state.index,
      answer,
      timeTakenSeconds: elapsed,
    });
    state.history.push({ ...feedback, question: state.questions[state.index], transcript: answer });
    renderFeedback(feedback);
    if (timedOut) toast("Time is up. Answer submitted.");
    if (feedback.mode === "local") toast("Feedback generated in local practice mode.");
  } catch (error) {
    toast(error.message);
  } finally {
    $("submit-answer").disabled = false;
  }
}

function renderSummary() {
  clearInterval(state.timerId);
  show("summary-view");
  const overall = state.history.length
    ? state.history.reduce((sum, item) => sum + Number(item.score || 0), 0) / state.history.length
    : 0;
  $("overall-score").textContent = `${overall.toFixed(1)} / 10`;
  $("history").innerHTML = state.history
    .map((item, index) => {
      const transcript = isVoice ? `<details><summary>Your transcript</summary><p>${item.transcript || "(no speech captured)"}</p></details>` : "";
      return `<article class="panel"><div class="feedback-head"><strong>${index + 1}. ${item.question}</strong><span class="score">${Number(item.score).toFixed(1)} / 10</span></div>${transcript}<p><b>Strengths:</b> ${item.strengths}</p><p><b>Improvements:</b> ${item.improvements}</p><p><b>Suitable answer:</b> ${item.idealAnswer}</p></article>`;
    })
    .join("");
}

$("start-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.count = Number(payload.count);
  payload.secondsPerQuestion = Number(payload.secondsPerQuestion);
  event.submitter.disabled = true;
  try {
    const response = await api("/api/mock-interview/start", payload);
    state.interviewId = response.id;
    state.questions = response.questions;
    state.index = 0;
    state.seconds = payload.secondsPerQuestion;
    state.history = [];
    show("interview-view");
    renderQuestion();
    if (response.mode === "local") toast("Interview started in local practice mode.");
  } catch (error) {
    toast(error.message);
  } finally {
    event.submitter.disabled = false;
  }
});
$("submit-answer")?.addEventListener("click", () => submitAnswer(false));
$("skip-answer")?.addEventListener("click", () => submitAnswer(false));
$("next-question")?.addEventListener("click", () => {
  if (state.index + 1 >= state.questions.length) renderSummary();
  else {
    state.index += 1;
    renderQuestion();
  }
});
$("restart")?.addEventListener("click", () => {
  stopListening();
  clearInterval(state.timerId);
  show("setup-view");
});
$("mic-toggle")?.addEventListener("click", () => (state.listening ? stopListening() : startListening()));
$("speak-question")?.addEventListener("click", () => speak(state.questions[state.index]));

if (isVoice && !recognitionCtor()) {
  $("voice-warning")?.classList.remove("hidden");
}
