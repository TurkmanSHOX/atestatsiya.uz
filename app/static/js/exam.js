/**
 * Attestatsiya.uz - Real-time Test Engine Client & Anti-Cheat System
 */
class ExamEngine {
  constructor(sessionId, finishUrl, resultUrlBase) {
    this.sessionId = sessionId;
    this.finishUrl = finishUrl;
    this.resultUrlBase = resultUrlBase;
    this.questions = [];
    this.currentIndex = 0;
    this.remainingSeconds = 0;
    this.timerInterval = null;
    this.heartbeatInterval = null;
    this.warningCount = 0;
    this.maxWarnings = 5;

    this.init();
  }

  async init() {
    this.setupAntiCheat();
    await this.fetchSessionData();
    this.renderQuestionNav();
    this.renderCurrentQuestion();
    this.startTimer();
    this.startHeartbeat();
  }

  setupAntiCheat() {
    // 1. O'ng tugmani bloklash
    document.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      this.logViolation('CONTEXT_MENU', 'LOW', 'O\'ng tugma bosildi');
      return false;
    });

    // 2. Nusxa olish / joylashni bloklash
    document.addEventListener('copy', (e) => {
      e.preventDefault();
      this.logViolation('SUSPICIOUS_PASTE', 'MEDIUM', 'Matndan nusxa olishga urinish');
    });
    document.addEventListener('paste', (e) => {
      e.preventDefault();
      this.logViolation('SUSPICIOUS_PASTE', 'MEDIUM', 'Matn joylashtirishga urinish');
    });

    // 3. Klaviatura kombinatsiyalarini bloklash (F12, Ctrl+Shift+I, etc.)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'F12' || (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J' || e.key === 'C'))) {
        e.preventDefault();
        this.logViolation('DEVTOOLS_OPEN', 'HIGH', 'Tuzuvchi vositalarini ochishga urinish');
      }
    });

    // 4. Tab yoki oynani almashtirish (Blur & Visibility change)
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.handleTabSwitch();
      }
    });

    window.addEventListener('blur', () => {
      this.handleTabSwitch();
    });
  }

  handleTabSwitch() {
    this.warningCount++;
    this.logViolation('TAB_SWITCH', 'HIGH', `Foydalanuvchi imtihon oynasidan chiqdi (${this.warningCount}-ogohlantirish)`);
    
    const warnBox = document.getElementById('cheatWarningAlert');
    if (warnBox) {
      warnBox.classList.remove('d-none');
      document.getElementById('cheatWarningCount').innerText = this.warningCount;
    }

    if (this.warningCount >= this.maxWarnings) {
      alert("Diqqat! Qoidalarni bir necha bor buzganingiz sababli imtihoningiz muddatidan oldin yakunlanmoqda.");
      this.finishExam(true);
    }
  }

  async logViolation(type, severity, details) {
    try {
      await fetch(`/api/exam/session/${this.sessionId}/security-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: type, severity: severity, details: { note: details } })
      });
    } catch (e) {
      console.error("Anti-cheat xatoligi:", e);
    }
  }

  async fetchSessionData() {
    try {
      const res = await fetch(`/api/exam/session/${this.sessionId}`);
      const json = await res.json();
      if (json.success) {
        this.questions = json.data.questions;
        this.remainingSeconds = json.data.remaining_seconds;
        if (json.data.status === 'EXPIRED') {
          window.location.reload();
        }
      } else {
        alert("Sessiya ma'lumotlarini yuklab bo'lmadi: " + json.message);
      }
    } catch (e) {
      console.error("Ma'lumot yuklashda xatolik:", e);
    }
  }

  startTimer() {
    const timerElem = document.getElementById('examTimer');
    const updateTimerDisplay = () => {
      if (this.remainingSeconds <= 0) {
        clearInterval(this.timerInterval);
        alert("Imtihon vaqti tugadi! Javoblaringiz avtomatik yakunlanadi.");
        this.finishExam(true);
        return;
      }

      const hours = Math.floor(this.remainingSeconds / 3600);
      const minutes = Math.floor((this.remainingSeconds % 3600) / 60);
      const seconds = this.remainingSeconds % 60;

      const formatted = 
        (hours > 0 ? String(hours).padStart(2, '0') + ':' : '') +
        String(minutes).padStart(2, '0') + ':' +
        String(seconds).padStart(2, '0');

      if (timerElem) {
        timerElem.innerText = formatted;
        if (this.remainingSeconds < 300) {
          timerElem.classList.add('urgent');
        }
      }

      this.remainingSeconds--;
    };

    updateTimerDisplay();
    this.timerInterval = setInterval(updateTimerDisplay, 1000);
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/exam/session/${this.sessionId}/heartbeat`, { method: 'POST' });
        const json = await res.json();
        if (json.success) {
          if (json.status === 'EXPIRED') {
            window.location.href = `${this.resultUrlBase}/${json.result_id}`;
          } else {
            // Sinxronizatsiya
            this.remainingSeconds = json.remaining_seconds;
          }
        }
      } catch (e) {
        console.warn("Heartbeat xatosi:", e);
      }
    }, 15000);
  }

  renderQuestionNav() {
    const navContainer = document.getElementById('questionNavigator');
    if (!navContainer) return;
    navContainer.innerHTML = '';

    this.questions.forEach((q, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'nav-question-btn';
      btn.id = `navBtn_${idx}`;
      btn.innerText = idx + 1;

      if (idx === this.currentIndex) btn.classList.add('current');
      if (q.is_flagged) btn.classList.add('flagged');
      else if (q.is_answered) btn.classList.add('answered');
      else btn.classList.add('unanswered');

      btn.addEventListener('click', () => {
        this.goToQuestion(idx);
      });

      navContainer.appendChild(btn);
    });
  }

  renderCurrentQuestion() {
    if (!this.questions.length) return;
    const q = this.questions[this.currentIndex];

    document.getElementById('currentQuestionNumber').innerText = this.currentIndex + 1;
    document.getElementById('totalQuestionsCount').innerText = this.questions.length;
    document.getElementById('questionPoints').innerText = q.points;
    document.getElementById('questionText').innerHTML = q.text;

    // Media
    const mediaContainer = document.getElementById('questionMedia');
    if (mediaContainer) {
      mediaContainer.innerHTML = '';
      if (q.media && q.media.length > 0) {
        q.media.forEach(m => {
          if (m.media_type === 'IMAGE') {
            const img = document.createElement('img');
            img.src = `/${m.file_path}`;
            img.className = 'img-fluid rounded border mb-3';
            img.style.maxHeight = '300px';
            mediaContainer.appendChild(img);
          }
        });
      }
    }

    // Options Container
    const optsContainer = document.getElementById('optionsContainer');
    optsContainer.innerHTML = '';

    const isMultiple = (q.type === 'MULTIPLE_CHOICE');
    const inputType = isMultiple ? 'checkbox' : 'radio';

    q.options.forEach(opt => {
      const optDiv = document.createElement('div');
      optDiv.className = 'form-check p-3 mb-2 border rounded bg-white shadow-sm';

      const input = document.createElement('input');
      input.className = 'form-check-input ms-0 me-3';
      input.type = inputType;
      input.name = `question_option_${q.question_id}`;
      input.value = opt.id;
      input.id = `opt_${opt.id}`;

      if (q.selected_option_ids && q.selected_option_ids.includes(opt.id)) {
        input.checked = true;
      }

      input.addEventListener('change', () => {
        this.saveCurrentAnswer();
      });

      const label = document.createElement('label');
      label.className = 'form-check-label w-100 cursor-pointer fw-medium';
      label.htmlFor = `opt_${opt.id}`;
      label.innerHTML = `<strong>${opt.key ? opt.key + ') ' : ''}</strong> ${opt.text}`;

      optDiv.appendChild(input);
      optDiv.appendChild(label);
      optsContainer.appendChild(optDiv);
    });

    // Update Flag button state
    const flagBtn = document.getElementById('flagQuestionBtn');
    if (flagBtn) {
      if (q.is_flagged) {
        flagBtn.className = 'btn btn-warning';
        flagBtn.innerHTML = '<i class="bi bi-bookmark-fill me-1"></i> Belgilangan';
      } else {
        flagBtn.className = 'btn btn-outline-warning';
        flagBtn.innerHTML = '<i class="bi bi-bookmark me-1"></i> Keyinroq ko\'rish';
      }
    }

    // Prev / Next button states
    document.getElementById('prevQuestionBtn').disabled = (this.currentIndex === 0);
    document.getElementById('nextQuestionBtn').disabled = (this.currentIndex === this.questions.length - 1);

    // Update Nav highlights
    this.updateNavButtonState(this.currentIndex);
  }

  async saveCurrentAnswer() {
    const q = this.questions[this.currentIndex];
    const inputs = document.querySelectorAll(`input[name="question_option_${q.question_id}"]:checked`);
    const selectedIds = Array.from(inputs).map(i => parseInt(i.value));

    q.selected_option_ids = selectedIds;
    q.is_answered = (selectedIds.length > 0);

    this.updateNavButtonState(this.currentIndex);

    try {
      await fetch(`/api/exam/session/${this.sessionId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: q.question_id,
          selected_option_ids: selectedIds,
          is_flagged: q.is_flagged,
          time_spent: 2
        })
      });
    } catch (e) {
      console.warn("Javob saqlashda xatolik:", e);
    }
  }

  toggleFlag() {
    const q = this.questions[this.currentIndex];
    q.is_flagged = !q.is_flagged;
    this.saveCurrentAnswer();
    this.renderCurrentQuestion();
  }

  goToQuestion(index) {
    if (index >= 0 && index < this.questions.length) {
      this.currentIndex = index;
      this.renderCurrentQuestion();
      this.highlightCurrentNav(index);
    }
  }

  nextQuestion() {
    if (this.currentIndex < this.questions.length - 1) {
      this.goToQuestion(this.currentIndex + 1);
    }
  }

  prevQuestion() {
    if (this.currentIndex > 0) {
      this.goToQuestion(this.currentIndex - 1);
    }
  }

  updateNavButtonState(idx) {
    const btn = document.getElementById(`navBtn_${idx}`);
    if (!btn) return;
    const q = this.questions[idx];

    btn.className = 'nav-question-btn';
    if (idx === this.currentIndex) btn.classList.add('current');

    if (q.is_flagged) {
      btn.classList.add('flagged');
    } else if (q.is_answered) {
      btn.classList.add('answered');
    } else {
      btn.classList.add('unanswered');
    }
  }

  highlightCurrentNav(idx) {
    document.querySelectorAll('.nav-question-btn').forEach((b, i) => {
      if (i === idx) b.classList.add('current');
      else b.classList.remove('current');
    });
  }

  showFinishModal() {
    const answered = this.questions.filter(q => q.is_answered).length;
    const unanswered = this.questions.length - answered;
    const flagged = this.questions.filter(q => q.is_flagged).length;

    document.getElementById('summaryTotal').innerText = this.questions.length;
    document.getElementById('summaryAnswered').innerText = answered;
    document.getElementById('summaryUnanswered').innerText = unanswered;
    document.getElementById('summaryFlagged').innerText = flagged;

    const modal = new bootstrap.Modal(document.getElementById('finishExamModal'));
    modal.show();
  }

  async finishExam(force = false) {
    if (this.timerInterval) clearInterval(this.timerInterval);
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);

    try {
      const res = await fetch(`/api/exam/session/${this.sessionId}/finish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const json = await res.json();
      if (json.success) {
        window.location.href = `${this.resultUrlBase}/${json.result_id}`;
      } else {
        alert("Xatolik: " + json.message);
      }
    } catch (e) {
      alert("Imtihonni yakunlashda xatolik yuz berdi.");
    }
  }
}
