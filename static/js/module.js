/* module.js – טעינת מודול, טאבים, עורך קוד וניווט */
(function () {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  let moduleData = null;
  let currentTab = 'theory';
  let editor = null;
  let totalModules = null;

  function getModuleIdFromURL() {
    const m = location.pathname.match(/\/module\/(\d+)/);
    if (m) return parseInt(m[1], 10);
    const sp = new URLSearchParams(location.search);
    return parseInt(sp.get('id') || '1', 10);
  }

  async function getTotalModules() {
    try {
      const res = await fetch('/static/content/index.json?ts=' + Date.now());
      if (!res.ok) throw new Error("לא הצלחתי לטעון את index.json");
      const data = await res.json();
      const arr = Array.isArray(data) ? data : data.modules;
      if (!Array.isArray(arr)) return null;
      return arr.length;
    } catch (e) {
      console.warn("[module] לא הצלחתי להביא מספר מודולים:", e.message);
      return null;
    }
  }

  async function loadModule() {
    const id = getModuleIdFromURL();
    totalModules = await getTotalModules();

    const url = `/static/content/module-${id}/module.json?ts=${Date.now()}`;
    console.debug('[module] fetching', url);

    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status} (${res.statusText})`);
      const text = await res.text();
      if (!text) throw new Error('קובץ module.json ריק');
      moduleData = JSON.parse(text);

      $('#module-title').textContent = moduleData.title || `מודול ${id}`;
      $('#module-id').textContent = `#${moduleData.id || id}`;
      $('#tab-content').innerHTML = `<p class="tp-muted">בחרו כרטיסייה כדי להציג תוכן.</p>`;

      renderNavButtons(id);


      console.info(`[module] ✅ מודול ${id} נטען בהצלחה`);
    } catch (e) {
      console.error('[module] load error', e);
      $('#tab-content').innerHTML = `<div class="tp-error">❌ ${e.message}</div>`;
    }
  }

  function bindTabs() {
    const tabsNav = $('.tp-tabs');
    if (!tabsNav) return;

    tabsNav.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.tp-tab');
      if (!btn) return;

      $$('.tp-tab').forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');

      const tab = btn.dataset.tab || 'theory';
      currentTab = tab;
      renderTab(tab);
    });
  }
function renderTab(tab) {
  if (!moduleData) return;
  const container = $('#tab-content');
  if (!container) return;

  switch (tab) {
    case 'theory':
      container.innerHTML = moduleData.theoryHTML || "<p>אין תוכן תיאורטי</p>";
      break;

    case 'examples':
      container.innerHTML = (moduleData.examples || [])
        .map(ex => `<div class="tp-example">${ex}</div>`)
        .join('') || "<p>אין דוגמאות</p>";
      break;

case 'exercises':
  container.innerHTML = (moduleData.exercises || [])
    .map((ex, idx) => `
      <div class="tp-exercise">
        <p>${typeof ex === 'string' ? ex : ex.question}</p>
        <button class="tp-btn tp-btn--small show-solution" data-ex="${idx}">הצג פתרון</button>
        <pre class="tp-solution" id="solution-${idx}" style="display:none;"></pre>
      </div>
    `).join('') || "<p>אין תרגילים</p>";

  // רינדור playground כרגיל
  renderPlayground();

  // חיבור הכפתורים
  $$('.show-solution').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.ex, 10);
      const ex = moduleData.exercises[idx];
      const solDiv = $(`#solution-${idx}`);
      if (!solDiv) return;
      solDiv.style.display = "block";
      solDiv.textContent = typeof ex === 'string' ? "אין פתרון זמין" : ex.solution || "אין פתרון זמין";
    });
  });
  break;


case 'quiz':
  container.innerHTML = `<div id="quiz-container"></div>`;

  if (moduleData.quizzes && moduleData.quizzes.length) {
    // הוספת תפריט לבחירת שאלון
    const selectorHtml = moduleData.quizzes.map((q, i) =>
      `<button class="tp-btn tp-btn--small quiz-selector" data-quiz-index="${i}">
         ${q.title || "שאלון " + (i+1)}
       </button>`
    ).join(" ");

    container.innerHTML = `<div class="tp-quiz-select">${selectorHtml}</div><div id="quiz-container"></div>`;

    // ברירת מחדל: טוען את הראשון
    renderQuiz(moduleData.quizzes[0]);

    // חיבור האירועים לכפתורים
    $$('.quiz-selector').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.dataset.quizIndex, 10);
        renderQuiz(moduleData.quizzes[idx]);
      });
    });

  } else {
    container.innerHTML = "<p>אין שאלון</p>";
  }
  break;
case 'ai':
  renderAITab(container);
  break;


    default:
      container.innerHTML = "<p>לא נמצא תוכן</p>";
  }
}

  function renderPlayground() {
    const container = $('#playground-container');
    if (!container) return;

    container.innerHTML = `
      <section id="playground" class="tp-playground tp-card" aria-label="עורך קוד והרצה">
        <div class="tp-playground__toolbar">
          <div class="tp-toolbar__left"><strong>עורך קוד</strong></div>
          <div class="tp-toolbar__right">
            <button id="run-code" class="tp-btn tp-btn--primary" type="button">▶ הרץ קוד</button>
            <button id="clear-output" class="tp-btn tp-btn--ghost" type="button">נקה פלט</button>
          </div>
        </div>
        <div class="tp-playground__grid">
          <div id="editor" class="tp-editor" aria-label="Ace Editor"></div>
          <div class="tp-output">
            <div class="tp-output__header"><strong>פלט</strong></div>
            <pre id="output" class="tp-terminal" dir="ltr"></pre>
          </div>
        </div>
      </section>
    `;

    editor = ace.edit("editor");
    editor.setTheme("ace/theme/monokai");
    editor.session.setMode("ace/mode/python");
    editor.setOptions({ enableBasicAutocompletion: true, enableLiveAutocompletion: true });

    $('#run-code').addEventListener("click", async () => {
      const code = editor.getValue();
      try {
        const res = await fetch("/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code })
        });
        const data = await res.json();
        $('#output').textContent = data.output || data.error || "לא התקבל פלט";
      } catch (err) {
        $('#output').textContent = "❌ שגיאה בהרצה: " + err.message;
      }
    });

    $('#clear-output').addEventListener("click", () => {
      $('#output').textContent = "";
    });
  }
// החלף את כל הפונקציה renderNavButtons בזה:
function renderNavButtons(currentId) {
  // לא יוצרים #module-nav חדש ולא מוסיפים HTML בתחתית

  // חיבור הכפתורים העליונים שכבר קיימים ב-HTML
  const btnHome = $('#go-home');
  if (btnHome) {
    btnHome.onclick = () => { window.location.href = "/"; };
  }

  const btnPrev = $('#go-prev');
  if (btnPrev) {
    if (currentId > 1) {
      btnPrev.style.display = "";
      btnPrev.onclick = () => { window.location.href = `/module/${currentId - 1}`; };
    } else {
      btnPrev.style.display = "none";
    }
  }

  const btnNext = $('#go-next');
  if (btnNext) {
    if (totalModules && currentId < totalModules) {
      btnNext.style.display = "";
      btnNext.onclick = () => { window.location.href = `/module/${currentId + 1}`; };
    } else {
      btnNext.style.display = "none";
    }
  }
}

  function renderQuiz(quizData) {
    const container = document.getElementById("quiz-container");
    if (!container) return;

    let html = `<h3>${quizData.title}</h3>`;
    quizData.questions.forEach((q, i) => {
      html += `
        <div class="tp-question">
          <p><strong>${q.question}</strong></p>
          ${q.options.map((opt, j) => `
            <label>
              <input type="radio" name="q${i}" value="${j}"> ${opt}
            </label><br/>
          `).join('')}
          <p class="tp-feedback" id="feedback-${i}"></p>
        </div>
      `;
    });
    html += `<button id="finish-quiz" class="tp-btn tp-btn--primary">סיים שאלון</button>`;
    html += `<p id="quiz-result"></p>`;
    container.innerHTML = html;

    // חישוב ציון + פידבק
    const finishBtn = document.getElementById("finish-quiz");
    if (finishBtn) {
      finishBtn.addEventListener("click", () => {
        let correctCount = 0;
        quizData.questions.forEach((q, i) => {
          const correct = q.answer;
          const selected = document.querySelector(`input[name="q${i}"]:checked`);
          const feedback = document.getElementById(`feedback-${i}`);
          if (!selected) {
            feedback.textContent = "❓ לא נבחרה תשובה";
            feedback.style.color = "orange";
          } else if (parseInt(selected.value) === correct) {
            feedback.textContent = "נכון ✅";
            feedback.style.color = "green";
            correctCount++;
          } else {
            feedback.textContent = `לא נכון ❌. התשובה הנכונה: ${q.options[correct]}`;
            feedback.style.color = "red";
          }
        });
        const result = document.getElementById("quiz-result");
        result.textContent = `ענית נכון על ${correctCount} מתוך ${quizData.questions.length} שאלות.`;
        result.style.fontWeight = "bold";
      });
    }
  }

  function renderAITab(container) {
  const moduleId = getModuleIdFromURL();
  container.innerHTML = `
    <section class="tp-card">
      <h3>שאל את ה-AI על המודול הזה</h3>
      <div id="ai-chat" class="tp-ai-chat">
        <div id="ai-messages" class="tp-ai-messages" aria-live="polite"></div>
        <div class="tp-ai-input">
          <textarea id="ai-question" class="tp-textarea" rows="3" placeholder="כתוב שאלה..."></textarea>
          <div class="tp-ai-actions">
            <button id="ai-send" class="tp-btn tp-btn--primary">שלח</button>
            <span id="ai-hint" class="tp-muted">מוגבל ל-10 שאלות / 5 דקות</span>
          </div>
        </div>
      </div>
    </section>
  `;

  const messagesEl = $('#ai-messages');
  const inputEl = $('#ai-question');
  const sendBtn = $('#ai-send');

  function appendMessage(role, text) {
  const el = document.createElement('div');
  el.className = role === 'user' ? 'tp-msg tp-msg--user' : 'tp-msg tp-msg--ai';

  // שמירה על כיוון LTR כברירת מחדל לקוד
  if (role === 'ai') {
    // החלפת ```...``` לבלוק קוד
    text = text
      .replace(/```(\w+)?\n([\s\S]*?)```/g, (m, lang, code) => {
        return `<pre dir="ltr"><code>${code.replace(/</g,"&lt;")}</code></pre>`;
      })
      // החלפת שורות רגילות
      .replace(/\n/g, "<br>");
    el.innerHTML = `<div dir="ltr">${text}</div>`;
  } else {
    el.textContent = text;
  }

  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}


  async function askAI() {
    const q = (inputEl.value || "").trim();
    if (!q) return;
    inputEl.value = "";
    appendMessage('user', q);
    sendBtn.disabled = true;
    sendBtn.textContent = "חושב…";

    try {
      const res = await fetch('/ask_ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, module_id: moduleId })
      });

      if (res.status === 429) {
        const data = await res.json();
        appendMessage('ai', `❗ ${data.detail}`);
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        appendMessage('ai', `❌ שגיאה: ${data.detail || res.statusText}`);
        return;
      }

      const data = await res.json();
      appendMessage('ai', data.answer || "לא התקבלה תשובה");
    } catch (err) {
      appendMessage('ai', "❌ שגיאה בחיבור לשרת: " + err.message);
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = "שלח";
      inputEl.focus();
    }
  }

  sendBtn.addEventListener('click', askAI);
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      askAI();
    }
  });
}




  document.addEventListener('DOMContentLoaded', () => {
    bindTabs();
    loadModule();
  });
})();
