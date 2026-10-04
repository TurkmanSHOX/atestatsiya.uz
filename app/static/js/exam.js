/**
 * Attestatsiya.uz 2.0 - Real-time Test Engine Client
 * O'qituvchilar uchun qulay, tezkor va server nazoratidagi test dvigateli
 */
class ExamEngine {
  constructor(sessionId, finishUrl) {
    this.sessionId = sessionId;
    this.finishUrl = finishUrl;
    this.questions = [];
    this.currentIndex = 0;
    this.remainingSeconds = 0;
    this.timerInterval = null;
    this.heartbeatInterval = null;
    this.questionStartTime = Date.now();

    this.init();
  }

  async init() {
    await this.fetchSessionData();
    this.renderQuestionNav();
    this.renderCurrentQuestion();
    this.startTimer();
    this.startHeartbeat();
  }

  async fetchSessionData() {
    try {
      const res = await fetch(`/api/exam/session/${this.sessionId}`);
      const json = await res.json();
      if (json.success) {
        this.questions = json.data.questions;
        this.remainingSeconds = json.data.remaining_seconds;
        document.getElementById('totalQuestionsCount').innerText = this.questions.length;
        this.updateStats();
      } else {
        alert("Sessiya ma'lumotlarini yuklab bo'lmadi: " + json.message);
      }
    } catch (e) {
      console.error("Sessiya yuklashda xatolik:", e);
    }
  }

  renderQuestionNav() {
    const grid = document.getElementById('questionNavigatorGrid');
    if (!grid) return;
    grid.innerHTML = '';

    this.questions.forEach((q, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.id = `navBtn_${idx}`;
      btn.className = 'btn btn-outline-secondary btn-sm nav-number-btn fw-bold';
      btn.innerText = idx + 1;
      btn.onclick = () => this.goToQuestion(idx);

      if (q.selected_option_ids && q.selected_option_ids.length > 0) {
        btn.classList.add('btn-answered');
      } else if (q.is_flagged) {
        btn.classList.add('btn-flagged');
      }

      if (idx === this.currentIndex) {
        btn.classList.add('active');
      }

      grid.appendChild(btn);
    });
  }

  renderCurrentQuestion() {
    if (!this.questions.length) return;
    const q = this.questions[this.currentIndex];
    this.questionStartTime = Date.now();

    document.getElementById('currentQuestionNumber').innerText = this.currentIndex + 1;
    document.getElementById('questionTopicName').innerText = q.topic_name || q.subject_name || "Mavzu";
    document.getElementById('questionText').innerText = q.text;

    // Savol rasmi (Question Media)
    const mediaContainer = document.getElementById('questionMedia');
    if (mediaContainer) {
      mediaContainer.innerHTML = '';
      const qImages = (q.images && q.images.length > 0) ? q.images : (q.image_url ? [{ file_url: q.image_url }] : []);
      if (qImages.length > 0) {
        qImages.forEach(img => {
          const imgUrl = img.file_url || (img.file_path ? (img.file_path.startsWith('/') ? img.file_path : '/' + img.file_path.replace(/\\/g, '/')) : '');
          if (!imgUrl) return;
          const wrap = document.createElement('div');
          wrap.className = 'd-inline-block position-relative m-1';
          wrap.innerHTML = `
            <img src="${imgUrl}" alt="Savol rasmi" class="img-fluid rounded-3 border shadow-sm" style="max-height: 280px; object-fit: contain; cursor: zoom-in;" onclick="window.openImageZoom('${imgUrl}', 'Savol rasmi')" />
            <button type="button" class="btn btn-sm btn-dark bg-opacity-75 border-0 position-absolute bottom-0 end-0 m-2 rounded-circle text-white" title="Kattalashtirish" onclick="window.openImageZoom('${imgUrl}', 'Savol rasmi')">
              <i class="bi bi-arrows-fullscreen"></i>
            </button>
          `;
          mediaContainer.appendChild(wrap);
        });
      }
    }

    // Flag holati
    const flagBtn = document.getElementById('flagQuestionBtn');
    if (flagBtn) {
      if (q.is_flagged) {
        flagBtn.className = 'btn btn-warning text-dark fw-semibold';
        flagBtn.innerHTML = '<i class="bi bi-bookmark-fill me-1"></i> Belgilangan';
      } else {
        flagBtn.className = 'btn btn-outline-warning text-dark fw-semibold';
        flagBtn.innerHTML = '<i class="bi bi-bookmark me-1"></i> Keyinroq ko\'rish';
      }
    }

    // Variantlar
    const container = document.getElementById('optionsContainer');
    container.innerHTML = '';

    const isMulti = q.question_type === 'MULTIPLE_CHOICE';
    const anyOptionHasImage = q.options.some(opt => opt.has_image || (opt.images && opt.images.length > 0) || opt.image_url);

    if (anyOptionHasImage) {
      container.className = 'row g-3 mb-5 flex-grow-1';
    } else {
      container.className = 'mb-5 flex-grow-1';
    }

    q.options.forEach((opt) => {
      const isChecked = q.selected_option_ids && q.selected_option_ids.includes(opt.id);
      const optImages = (opt.images && opt.images.length > 0) ? opt.images : (opt.image_url ? [{ file_url: opt.image_url }] : []);
      const hasImage = optImages.length > 0;

      const card = document.createElement('label');
      card.className = `exam-option-card d-flex align-items-start p-3 rounded-3 border transition-all h-100 ${isChecked ? 'selected bg-success-subtle border-success shadow-sm' : 'bg-white border-secondary-subtle'}`;
      card.style.cursor = 'pointer';

      const input = document.createElement('input');
      input.type = isMulti ? 'checkbox' : 'radio';
      input.name = `question_option_${q.question_id}`;
      input.value = opt.id;
      input.checked = isChecked;
      input.className = 'form-check-input me-3 mt-1 flex-shrink-0';
      if (!isMulti) input.style.accentColor = '#16a34a';

      input.onchange = () => this.handleOptionSelect(opt.id, isMulti);

      const contentBox = document.createElement('div');
      contentBox.className = 'flex-grow-1';

      // Key + text
      const headerBox = document.createElement('div');
      headerBox.className = 'd-flex align-items-baseline flex-wrap';

      const spanKey = document.createElement('span');
      spanKey.className = 'fw-bold me-2 text-success fs-6';
      spanKey.innerText = `${opt.key})`;
      headerBox.appendChild(spanKey);

      if (opt.text && opt.text.trim()) {
        const spanText = document.createElement('span');
        spanText.className = 'text-dark fw-medium lh-base';
        spanText.innerText = opt.text;
        headerBox.appendChild(spanText);
      }
      contentBox.appendChild(headerBox);

      // Rasm bo'lsa
      if (hasImage) {
        optImages.forEach(img => {
          const imgUrl = img.file_url || (img.file_path ? (img.file_path.startsWith('/') ? img.file_path : '/' + img.file_path.replace(/\\/g, '/')) : '');
          if (!imgUrl) return;

          const imgBox = document.createElement('div');
          imgBox.className = 'position-relative mt-2 p-1 bg-light border rounded text-center';
          imgBox.style.maxWidth = '260px';
          imgBox.innerHTML = `
            <img src="${imgUrl}" alt="Variant ${opt.key} rasmi" class="img-fluid rounded" style="max-height: 160px; object-fit: contain;" />
            <button type="button" class="btn btn-sm btn-light border position-absolute top-0 end-0 m-1 shadow-sm opacity-75 hover-opacity-100" title="Kattalashtirish" onclick="event.preventDefault(); event.stopPropagation(); window.openImageZoom('${imgUrl}', 'Variant ${opt.key} rasmi');">
              <i class="bi bi-arrows-fullscreen"></i>
            </button>
          `;
          contentBox.appendChild(imgBox);
        });
      }

      card.appendChild(input);
      card.appendChild(contentBox);

      if (anyOptionHasImage) {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-12';
        col.appendChild(card);
        container.appendChild(col);
      } else {
        card.classList.add('mb-2');
        container.appendChild(card);
      }
    });

    // Navigatsiya tugmalari holati
    document.getElementById('prevQuestionBtn').disabled = (this.currentIndex === 0);
    const nextBtn = document.getElementById('nextQuestionBtn');
    if (this.currentIndex === this.questions.length - 1) {
      nextBtn.innerHTML = '<i class="bi bi-check2-all me-1"></i> Yakunlash';
      nextBtn.className = 'btn btn-success px-4 fw-semibold';
      nextBtn.onclick = () => this.showFinishModal();
    } else {
      nextBtn.innerHTML = 'Keyingi <i class="bi bi-chevron-right ms-1"></i>';
      nextBtn.className = 'btn btn-success px-4 fw-semibold';
      nextBtn.onclick = () => this.nextQuestion();
    }

    // Nav tugmalarida aktivlikni belgilash
    document.querySelectorAll('.nav-number-btn').forEach((btn, idx) => {
      btn.classList.toggle('active', idx === this.currentIndex);
    });
  }

  async handleOptionSelect(optionId, isMulti) {
    const q = this.questions[this.currentIndex];
    if (!q.selected_option_ids) q.selected_option_ids = [];

    if (isMulti) {
      if (q.selected_option_ids.includes(optionId)) {
        q.selected_option_ids = q.selected_option_ids.filter(id => id !== optionId);
      } else {
        q.selected_option_ids.push(optionId);
      }
    } else {
      q.selected_option_ids = [optionId];
    }

    this.renderCurrentQuestion();
    this.updateStats();

    // Serverga avtomatik saqlash
    const timeSpent = Math.round((Date.now() - this.questionStartTime) / 1000);
    this.questionStartTime = Date.now();

    try {
      await fetch(`/api/exam/session/${this.sessionId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: q.question_id,
          selected_option_ids: q.selected_option_ids,
          is_flagged: q.is_flagged,
          time_spent: timeSpent
        })
      });
    } catch (e) {
      console.error("Javobni saqlashda xatolik:", e);
    }
  }

  async toggleFlag() {
    const q = this.questions[this.currentIndex];
    q.is_flagged = !q.is_flagged;
    this.renderCurrentQuestion();
    this.updateStats();

    try {
      await fetch(`/api/exam/session/${this.sessionId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: q.question_id,
          selected_option_ids: q.selected_option_ids || [],
          is_flagged: q.is_flagged,
          time_spent: 0
        })
      });
    } catch (e) {
      console.error("Flag holatini saqlashda xatolik:", e);
    }
  }

  goToQuestion(idx) {
    if (idx >= 0 && idx < this.questions.length) {
      this.currentIndex = idx;
      this.renderCurrentQuestion();
    }
  }

  nextQuestion() {
    if (this.currentIndex < this.questions.length - 1) {
      this.currentIndex++;
      this.renderCurrentQuestion();
    }
  }

  prevQuestion() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.renderCurrentQuestion();
    }
  }

  updateStats() {
    let answered = 0;
    this.questions.forEach((q, idx) => {
      const btn = document.getElementById(`navBtn_${idx}`);
      if (!btn) return;

      const hasAns = q.selected_option_ids && q.selected_option_ids.length > 0;
      if (hasAns) {
        answered++;
        btn.className = 'btn btn-success btn-sm nav-number-btn fw-bold';
      } else if (q.is_flagged) {
        btn.className = 'btn btn-warning text-dark btn-sm nav-number-btn fw-bold';
      } else {
        btn.className = 'btn btn-outline-secondary btn-sm nav-number-btn fw-bold';
      }
      if (idx === this.currentIndex) {
        btn.classList.add('border-dark', 'border-2');
      }
    });

    const ansElem = document.getElementById('answeredCount');
    const unansElem = document.getElementById('unansweredCount');
    if (ansElem) ansElem.innerText = answered;
    if (unansElem) unansElem.innerText = this.questions.length - answered;
  }

  startTimer() {
    const timerElem = document.getElementById('examTimer');

    const updateDisplay = () => {
      if (this.remainingSeconds <= 0) {
        clearInterval(this.timerInterval);
        timerElem.innerText = "00:00";
        alert("Vaqt tugadi! Testingiz avtomatik yakunlanadi.");
        this.finishExam(true);
        return;
      }

      const m = Math.floor(this.remainingSeconds / 60);
      const s = this.remainingSeconds % 60;
      timerElem.innerText = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;

      if (this.remainingSeconds <= 300) {
        timerElem.className = 'exam-timer fs-4 fw-extrabold text-danger font-monospace animate-pulse';
      }

      this.remainingSeconds--;
    };

    updateDisplay();
    this.timerInterval = setInterval(updateDisplay, 1000);
  }

  startHeartbeat() {
    // Har 30 soniyada server bilan sinxronizatsiya
    this.heartbeatInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/exam/session/${this.sessionId}/heartbeat`, { method: 'POST' });
        const json = await res.json();
        if (json.success) {
          if (json.status === 'EXPIRED') {
            clearInterval(this.heartbeatInterval);
            clearInterval(this.timerInterval);
            window.location.href = `/results/${json.result_id}`;
          } else if (json.remaining_seconds !== undefined) {
            this.remainingSeconds = json.remaining_seconds;
          }
        }
      } catch (e) {
        console.error("Heartbeat error:", e);
      }
    }, 30000);
  }

  showFinishModal() {
    let answered = this.questions.filter(q => q.selected_option_ids && q.selected_option_ids.length > 0).length;
    document.getElementById('modalAnsweredCount').innerText = answered;
    document.getElementById('modalTotalCount').innerText = this.questions.length;

    const modal = new bootstrap.Modal(document.getElementById('finishModal'));
    modal.show();
  }

  async finishExam(force = false) {
    clearInterval(this.timerInterval);
    clearInterval(this.heartbeatInterval);

    try {
      const res = await fetch(`/api/exam/session/${this.sessionId}/finish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const json = await res.json();
      if (json.success && json.result_id) {
        window.location.href = `/results/${json.result_id}`;
      } else {
        alert("Testni yakunlashda xatolik yuz berdi.");
      }
    } catch (e) {
      console.error("Test yakunlash xatosi:", e);
      alert("Aloqa uzildi. Iltimos qayta urinib ko'ring.");
    }
  }
}

window.openImageZoom = function(src, title = "Tasvirni ko'rish") {
  const modalEl = document.getElementById('imageZoomModal');
  if (!modalEl) return;
  const imgEl = document.getElementById('imageZoomSrc');
  const titleEl = document.getElementById('imageZoomTitle');
  if (imgEl) imgEl.src = src;
  if (titleEl) titleEl.innerText = title;
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.EXAM_CONFIG && window.EXAM_CONFIG.sessionId) {
    window.engine = new ExamEngine(
      window.EXAM_CONFIG.sessionId,
      window.EXAM_CONFIG.finishUrl
    );
  }
});
