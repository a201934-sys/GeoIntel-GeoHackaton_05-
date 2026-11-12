/*
 * Frontend-only prototype. Set window.COPILOT_CONFIG before this file loads:
 * window.COPILOT_CONFIG = {
 *   chatEndpoint: "/api/chat", // OpenAI-compatible chat completions endpoint
 *   model: "google/gemma-4-26B-A4B-it"
 * };
 * Keep any credentials inside the Python service, never in this browser file.
 */

(() => {
  const views = [...document.querySelectorAll('.view-panel')];
  const navItems = [...document.querySelectorAll('.nav-item[data-view]')];
  const toast = document.getElementById('toast');
  const chatInput = document.getElementById('chatInput');
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const promptButtons = [...document.querySelectorAll('.prompt-chip')];
  const selectedFiles = document.getElementById('selectedFiles');
  let toastTimeout;
  let pending = false;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('is-visible');
    window.clearTimeout(toastTimeout);
    toastTimeout = window.setTimeout(() => toast.classList.remove('is-visible'), 3600);
  }

  function setView(name) {
    const target = document.getElementById(`view-${name}`);
    if (!target) return;
    views.forEach(view => {
      const active = view === target;
      view.classList.toggle('is-active', active);
      view.hidden = !active;
    });
    navItems.forEach(item => {
      const active = item.dataset.view === name;
      item.classList.toggle('is-active', active);
      if (active) item.setAttribute('aria-current', 'page');
      else item.removeAttribute('aria-current');
    });
    document.getElementById('sidebar').classList.remove('is-open');
    document.querySelector('.main-area').scrollTo({ top: 0, behavior: 'smooth' });
  }

  navItems.forEach(item => item.addEventListener('click', () => setView(item.dataset.view)));
  document.querySelectorAll('[data-view-link]').forEach(item => item.addEventListener('click', () => setView(item.dataset.viewLink)));
  document.getElementById('mobileMenu').addEventListener('click', () => document.getElementById('sidebar').classList.toggle('is-open'));

  const copilotPanel = document.getElementById('copilotPanel');
  function focusCopilot() {
    copilotPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    window.setTimeout(() => chatInput.focus(), 250);
  }
  document.getElementById('openCopilot').addEventListener('click', focusCopilot);
  document.getElementById('askCopilotInterpretation').addEventListener('click', focusCopilot);
  document.getElementById('askCopilotRisks').addEventListener('click', focusCopilot);
  document.getElementById('askCopilotRisks2').addEventListener('click', focusCopilot);

  document.querySelector('.banner-dismiss').addEventListener('click', event => {
    event.currentTarget.closest('.demo-banner').remove();
  });
  document.getElementById('aboutLink').addEventListener('click', () => {
    showToast('Demo mode uses illustrative visuals and sample replies. Connect a Python endpoint before presenting geological conclusions.');
  });
  document.querySelector('.help-button').addEventListener('click', () => {
    showToast('This frontend is a working interaction prototype. Source data is still on HPC and is not read by this page.');
  });

  document.getElementById('toggleHorizons').addEventListener('click', event => {
    const button = event.currentTarget;
    const enabled = button.getAttribute('aria-pressed') === 'true';
    button.setAttribute('aria-pressed', String(!enabled));
    button.classList.toggle('is-selected', !enabled);
    document.querySelector('.seismic-panel').classList.toggle('hide-horizons', enabled);
  });
  document.getElementById('toggleWells').addEventListener('click', event => {
    const button = event.currentTarget;
    const enabled = button.getAttribute('aria-pressed') === 'true';
    button.setAttribute('aria-pressed', String(!enabled));
    button.classList.toggle('is-selected', !enabled);
    document.querySelector('.seismic-panel').classList.toggle('hide-wells', enabled);
  });
  document.getElementById('sectionSelect').addEventListener('click', () => {
    showToast('Section controls will use the selected seismic volume after notebook integration.');
  });

  function addFileChips(fileList) {
    [...fileList].forEach(file => {
      const chip = document.createElement('div');
      chip.className = 'selected-file';
      const icon = document.createElement('i');
      icon.textContent = file.name.toLowerCase().endsWith('.sgy') || file.name.toLowerCase().endsWith('.segy') ? 'SEIS' : 'FILE';
      const name = document.createElement('span');
      name.textContent = file.name;
      const local = document.createElement('i');
      local.textContent = 'LOCAL';
      chip.append(icon, name, local);
      selectedFiles.append(chip);
    });
    if (fileList.length) showToast(`${fileList.length} file${fileList.length === 1 ? '' : 's'} shown for this browser session only. Nothing was uploaded or analysed.`);
  }
  document.getElementById('fileInput').addEventListener('change', event => addFileChips(event.target.files));
  const dropZone = document.getElementById('dropZone');
  ['dragenter', 'dragover'].forEach(type => dropZone.addEventListener(type, event => {
    event.preventDefault();
    dropZone.classList.add('is-dragging');
  }));
  ['dragleave', 'drop'].forEach(type => dropZone.addEventListener(type, event => {
    event.preventDefault();
    dropZone.classList.remove('is-dragging');
  }));
  dropZone.addEventListener('drop', event => {
    if (event.dataTransfer?.files?.length) addFileChips(event.dataTransfer.files);
  });

  function makeMessage(role, text, timeLabel) {
    const wrapper = document.createElement('div');
    wrapper.className = role === 'user' ? 'user-message' : 'assistant-message';
    const body = document.createElement('div');
    body.className = 'message-body';
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    const name = document.createElement('strong');
    name.textContent = role === 'user' ? 'You' : 'Copilot';
    const time = document.createElement('time');
    time.textContent = timeLabel || 'Just now';
    meta.append(name, time);
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    const paragraph = document.createElement('p');
    paragraph.textContent = text;
    bubble.append(paragraph);
    if (role === 'assistant') {
      const hint = document.createElement('p');
      hint.className = 'message-hint';
      hint.textContent = window.COPILOT_CONFIG?.chatEndpoint
        ? 'Review the cited evidence and validate against source data.'
        : 'Illustrative response only. Connect the notebook for evidence-based analysis.';
      bubble.append(hint);
      const avatar = document.createElement('span');
      avatar.className = 'message-avatar';
      avatar.setAttribute('aria-hidden', 'true');
      avatar.textContent = '✦';
      wrapper.append(avatar);
    }
    body.append(meta, bubble);
    wrapper.append(body);
    chatMessages.append(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return wrapper;
  }

  function makeTyping() {
    const wrapper = document.createElement('div');
    wrapper.className = 'assistant-message typing-message';
    wrapper.innerHTML = '<span class="message-avatar" aria-hidden="true">✦</span><div class="message-body"><div class="message-meta"><strong>Copilot</strong><time>Thinking</time></div><div class="message-bubble"><span class="typing-dots" aria-label="Generating reply"><i></i><i></i><i></i></span></div></div>';
    chatMessages.append(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return wrapper;
  }

  function demoAnswer(question) {
    const q = question.toLowerCase();
    if (q.includes('structural') || q.includes('stratigraphic') || q.includes('trap')) {
      return 'I can’t classify the trap from this preview because no seismic interpretation, well ties or basin context are connected. To compare structural and stratigraphic hypotheses, check whether closure is supported by mapped structure, then test for lateral facies change, pinch-out and seal continuity. Keep both explanations open until those observations are available.';
    }
    if (q.includes('evidence') || q.includes('check') || q.includes('next')) {
      return 'A useful next pass is to tie the candidate reservoir interval to the well markers, inspect continuity across near/far and full-stack volumes, then compare the mapped closure with the inversion attributes. Record the observation, source and uncertainty for each step. These are workflow suggestions, not findings about the supplied data.';
    }
    if (q.includes('risk') || q.includes('invalidate') || q.includes('uncertainty')) {
      return 'Potential review questions include: does the seal remain continuous across the closure, is reservoir presence supported by well or inversion evidence, and is charge timing compatible with trap formation? The current prototype has no prospect evidence, so it cannot rank these risks or say they are present.';
    }
    if (q.includes('analogue') || q.includes('field')) {
      return 'No basin studies or field summaries are linked yet, so I can’t identify a defensible analogue. Add references that describe tectonic setting, reservoir, seal and trap style; then compare those play elements explicitly rather than matching on basin name alone.';
    }
    return 'I’m in demo mode and can’t inspect the challenge data yet. Connect a Python endpoint that reads the HPC seismic and well outputs, then I can answer with evidence, alternatives and a confidence explanation. For now, I can help outline what to check.';
  }

  async function requestAnswer(question) {
    const config = window.COPILOT_CONFIG || {};
    if (!config.chatEndpoint) {
      await new Promise(resolve => window.setTimeout(resolve, 650));
      return demoAnswer(question);
    }
    const response = await fetch(config.chatEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: config.model || 'google/gemma-4-26B-A4B-it',
        messages: [
          { role: 'system', content: 'You are an exploration geoscience copilot. Distinguish observations from interpretations, cite the connected evidence, explain uncertainty, and compare plausible alternatives. If source data is absent, say so. Do not invent geological findings.' },
          { role: 'user', content: question }
        ],
        temperature: 0.3
      })
    });
    if (!response.ok) throw new Error(`The analysis service returned ${response.status}.`);
    const payload = await response.json();
    const answer = payload.choices?.[0]?.message?.content || payload.reply || payload.answer;
    if (!answer) throw new Error('The analysis service returned no answer.');
    return typeof answer === 'string' ? answer : JSON.stringify(answer);
  }

  async function submitQuestion(question) {
    const text = question.trim();
    if (!text || pending) return;
    pending = true;
    promptButtons.forEach(button => { button.disabled = true; });
    document.querySelector('.send-button').disabled = true;
    makeMessage('user', text);
    chatInput.value = '';
    chatInput.style.height = '30px';
    const typing = makeTyping();
    try {
      const answer = await requestAnswer(text);
      typing.remove();
      makeMessage('assistant', answer);
    } catch (error) {
      typing.remove();
      makeMessage('assistant', `I couldn’t reach the analysis service. ${error.message} Check the Python API connection and try again.`);
    } finally {
      pending = false;
      promptButtons.forEach(button => { button.disabled = false; });
      document.querySelector('.send-button').disabled = false;
      chatInput.focus();
    }
  }

  chatForm.addEventListener('submit', event => {
    event.preventDefault();
    submitQuestion(chatInput.value);
  });
  promptButtons.forEach(button => button.addEventListener('click', () => submitQuestion(button.textContent)));
  chatInput.addEventListener('input', () => {
    chatInput.style.height = '30px';
    chatInput.style.height = `${Math.min(chatInput.scrollHeight, 86)}px`;
  });
  chatInput.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      chatForm.requestSubmit();
    }
  });
})();
