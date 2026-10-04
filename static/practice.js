/**
 * PrepAI Practice Mode — interactive question-by-question practice
 */
(function () {
  const root = document.getElementById("practice-app");
  if (!root) return;

  const sessionId = root.dataset.sessionId;
  const csrfToken = root.dataset.csrf;
  const qtype = root.dataset.qtype;
  let questions = [];
  try {
    questions = JSON.parse(root.dataset.questions || "[]");
  } catch {
    questions = [];
  }

  const state = {
    index: 0,
    answers: [],
    startTime: 0,
  };

  const $ = (id) => document.getElementById(id);

  function show(id) {
    ["practice-setup", "practice-question", "practice-summary"].forEach(
      (v) => ($(v).classList.toggle("hidden", v !== id))
    );
  }

  function renderQuestion() {
    const q = questions[state.index];
    const questionText = typeof q === "string" ? q : q.question || "";

    $("pq-counter").textContent = `Question ${state.index + 1} of ${questions.length}`;
    $("pq-text").textContent = questionText;
    $("pq-progress").style.width = `${((state.index) / questions.length) * 100}%`;
    $("pq-feedback").classList.add("hidden");
    $("pq-actions").classList.remove("hidden");
    $("pq-submit").disabled = false;

    // Reset answer
    $("pq-answer").value = "";
    $("pq-answer").disabled = false;
    $("pq-next").textContent = state.index + 1 >= questions.length ? "View summary" : "Next question";

    // MCQ mode
    const mcqWrap = $("pq-mcq-options");
    const answerWrap = $("pq-answer-wrap");
    const codingWrap = $("pq-coding-details");

    mcqWrap.classList.add("hidden");
    codingWrap.classList.add("hidden");
    answerWrap.classList.remove("hidden");

    if (qtype === "mcq" && q.options) {
      mcqWrap.classList.remove("hidden");
      answerWrap.classList.add("hidden");
      mcqWrap.innerHTML = ["A", "B", "C", "D"]
        .filter((k) => q.options[k])
        .map(
          (k) =>
            `<label class="mcq-practice-option">
              <input type="radio" name="mcq-answer" value="${k}">
              <span><strong>${k}.</strong> ${q.options[k]}</span>
            </label>`
        )
        .join("");
    }

    if (qtype === "coding" && q.constraints) {
      codingWrap.classList.remove("hidden");
      $("pq-constraints").innerHTML = q.constraints
        ? `<h4>Constraints</h4><p>${q.constraints}</p>`
        : "";
      $("pq-example").innerHTML = q.example
        ? `<h4>Example</h4><pre>${q.example}</pre>`
        : "";
    }

    state.startTime = Date.now();
  }

  function getAnswer() {
    if (qtype === "mcq") {
      const checked = document.querySelector('input[name="mcq-answer"]:checked');
      return checked ? checked.value : "";
    }
    return $("pq-answer").value.trim();
  }

  async function submitAnswer(skip = false) {
    const answer = skip ? "" : getAnswer();
    const timeTaken = Math.round((Date.now() - state.startTime) / 1000);

    $("pq-submit").disabled = true;
    $("pq-answer").disabled = true;

    try {
      const resp = await fetch("/api/practice/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          sessionId,
          questionIndex: state.index,
          answer,
          timeTaken,
        }),
      });
      const data = await resp.json();

      state.answers.push({
        index: state.index,
        answer,
        ...data,
      });

      renderFeedback(data);
    } catch (err) {
      $("pq-submit").disabled = false;
      $("pq-answer").disabled = false;
      alert("Error submitting answer: " + err.message);
    }
  }

  function renderFeedback(data) {
    $("pq-actions").classList.add("hidden");
    $("pq-feedback").classList.remove("hidden");

    const q = questions[state.index];
    let html = "";

    if (data.is_correct !== null && data.is_correct !== undefined) {
      html += `<div class="practice-result ${data.is_correct ? "correct" : "incorrect"}">
        <strong>${data.is_correct ? "✓ Correct!" : "✗ Incorrect"}</strong>
      </div>`;
    }

    if (data.feedback) {
      if (data.feedback.correct_answer) {
        html += `<p><strong>Correct answer:</strong> ${data.feedback.correct_answer}</p>`;
      }
      if (data.feedback.explanation) {
        html += `<div class="explanation-block"><strong>Explanation:</strong><p>${data.feedback.explanation}</p></div>`;
      }
      if (data.feedback.model_answer) {
        html += `<div class="explanation-block"><strong>Model answer:</strong><p>${data.feedback.model_answer}</p></div>`;
      }
    }

    $("pq-fb-result").innerHTML = html;

    // Highlight correct MCQ option
    if (qtype === "mcq" && data.feedback?.correct_answer) {
      document.querySelectorAll(".mcq-practice-option").forEach((opt) => {
        const radio = opt.querySelector("input");
        if (radio.value === data.feedback.correct_answer) {
          opt.classList.add("correct");
        } else if (radio.checked) {
          opt.classList.add("incorrect");
        }
        radio.disabled = true;
      });
    }
  }

  function renderSummary() {
    show("practice-summary");
    const correct = state.answers.filter((a) => a.is_correct === true).length;
    const total = state.answers.length;
    const hasMCQ = state.answers.some((a) => a.is_correct !== null && a.is_correct !== undefined);

    if (hasMCQ) {
      $("ps-score").textContent = `${correct} / ${total} correct`;
    } else {
      $("ps-score").textContent = `${total} questions completed`;
    }

    $("ps-review").innerHTML = state.answers
      .map((a, i) => {
        const q = questions[a.index];
        const qText = typeof q === "string" ? q : q.question || "";
        let badge = "";
        if (a.is_correct === true) badge = '<span class="badge badge-success">Correct</span>';
        else if (a.is_correct === false) badge = '<span class="badge badge-danger">Incorrect</span>';
        else badge = '<span class="badge badge-type">Completed</span>';
        return `<article class="panel">
          <div class="feedback-head"><strong>${i + 1}. ${qText}</strong>${badge}</div>
          <p><strong>Your answer:</strong> ${a.answer || "(skipped)"}</p>
        </article>`;
      })
      .join("");
  }

  // Event listeners
  $("start-practice")?.addEventListener("click", () => {
    state.index = 0;
    state.answers = [];
    show("practice-question");
    renderQuestion();
  });

  $("pq-submit")?.addEventListener("click", () => submitAnswer(false));
  $("pq-skip")?.addEventListener("click", () => submitAnswer(true));

  $("pq-next")?.addEventListener("click", () => {
    if (state.index + 1 >= questions.length) {
      renderSummary();
    } else {
      state.index += 1;
      renderQuestion();
    }
  });

  $("practice-restart")?.addEventListener("click", () => {
    state.index = 0;
    state.answers = [];
    show("practice-setup");
  });
})();
