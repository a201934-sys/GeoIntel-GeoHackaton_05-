/*
 * Frontend-only GeoIntel prototype.
 * Configure an OpenAI-compatible service before this file loads if available:
 * window.COPILOT_CONFIG = { chatEndpoint: "/api/chat", model: "your-model" };
 * File contents are not sent by this prototype; keep credentials server-side.
 */

(() => {
  const views = [...document.querySelectorAll('.view-panel')];
  const navItems = [...document.querySelectorAll('.nav-item[data-view]')];
  const toast = document.getElementById('toast');
  const chatInput = document.getElementById('chatInput');
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const questionCards = [...document.querySelectorAll('.question-card')];
  const attachmentTray = document.getElementById('attachmentTray');
  const fileInput = document.getElementById('fileInput');
  const photoInput = document.getElementById('photoInput');
  const modeButtons = [...document.querySelectorAll('.scope-button')];
  const pendingAttachments = [];
  let currentMode = 'general';
  let toastTimeout;
  let pending = false;

  const generalQuestions = [
    ['How do structural and stratigraphic traps differ?', 'Structural vs. stratigraphic traps', 'Compare two common trapping styles'],
    ['What can seismic attributes tell us about reservoir facies?', 'Seismic attributes', 'Explore what they can reveal'],
    ['What makes a fault sealing or transmissive?', 'Fault seal behaviour', 'Review the factors that matter'],
    ['What should I investigate first when evaluating a prospect?', 'Prospect evaluation', 'Plan a focused first-pass review']
  ];
  const prospectQuestions = [
    ['What evidence in the attached material supports a structural trap?', 'Test a trap hypothesis', 'Use only evidence I provide'],
    ['What observations could point to a stratigraphic trap?', 'Explore an alternative', 'Compare a different explanation'],
    ['What important uncertainty should I investigate next?', 'Prioritise an uncertainty', 'Connect observations to next steps'],
    ['Which evidence would help rule out this interpretation?', 'Challenge the interpretation', 'Look for disconfirming evidence']
  ];

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('is-visible');
    window.clearTimeout(toastTimeout);
    toastTimeout = window.setTimeout(() => toast.classList.remove('is-visible'), 3800);
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
    const crumb = document.querySelector('.breadcrumbs strong');
    crumb.textContent = ({ overview: 'Ask', interpretation: 'Analysis' })[name] || 'Ask';
    document.getElementById('sidebar').classList.remove('is-open');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  navItems.forEach(item => item.addEventListener('click', () => setView(item.dataset.view)));
  document.getElementById('mobileMenu').addEventListener('click', () => document.getElementById('sidebar').classList.toggle('is-open'));

  document.querySelectorAll('[data-go-home]').forEach(button => button.addEventListener('click', () => {
    setView('overview');
    window.setTimeout(() => chatInput.focus(), 80);
  }));

  document.getElementById('aboutButton').addEventListener('click', () => {
    showToast('This frontend preview does not send file contents to an analysis service. Connect the Python upload and chat routes before analysing selected files.');
  });
  document.getElementById('aboutLink').addEventListener('click', () => {
    showToast('GeoIntel can answer general geology questions. Prospect-specific conclusions require connected evidence and should cite its source.');
  });

  function renderQuestions() {
    const questions = currentMode === 'general' ? generalQuestions : prospectQuestions;
    questionCards.forEach((card, index) => {
      const [question, title, description] = questions[index];
      card.dataset.question = question;
      card.querySelector('strong').textContent = title;
      card.querySelector('small').textContent = description;
      card.setAttribute('aria-label', question);
    });
    chatInput.placeholder = currentMode === 'general'
      ? 'Ask GeoIntel anything about geology…'
      : 'Ask GeoIntel to inspect evidence you provide…';
  }

  modeButtons.forEach(button => button.addEventListener('click', () => {
    currentMode = button.dataset.mode;
    modeButtons.forEach(option => {
      const selected = option === button;
      option.classList.toggle('is-selected', selected);
      option.setAttribute('aria-pressed', String(selected));
    });
    renderQuestions();
  }));

  document.getElementById('addFilesButton').addEventListener('click', () => fileInput.click());
  document.getElementById('addPhotosButton').addEventListener('click', () => photoInput.click());

  function attachmentKind(file) {
    if (file.type.startsWith('image/')) return 'PHOTO';
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (['sgy', 'segy'].includes(extension)) return 'SEISMIC';
    if (extension === 'las') return 'WELL LOG';
    if (['pdf', 'doc', 'docx', 'txt'].includes(extension)) return 'DOCUMENT';
    return 'FILE';
  }

  function renderAttachments() {
    attachmentTray.replaceChildren();
    attachmentTray.hidden = pendingAttachments.length === 0;
    pendingAttachments.forEach((file, index) => {
      const chip = document.createElement('span');
      chip.className = 'attachment-chip';
      const kind = document.createElement('i');
      kind.className = 'attachment-kind';
      kind.textContent = attachmentKind(file);
      const name = document.createElement('span');
      name.className = 'attachment-chip-name';
      name.textContent = file.name;
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'remove-attachment';
      remove.setAttribute('aria-label', `Remove ${file.name}`);
      remove.textContent = '×';
      remove.addEventListener('click', () => {
        pendingAttachments.splice(index, 1);
        renderAttachments();
      });
      chip.append(kind, name, remove);
      attachmentTray.append(chip);
    });
  }

  function acceptFiles(files) {
    [...files].forEach(file => pendingAttachments.push(file));
    renderAttachments();
    if (files.length) showToast(`${files.length} item${files.length === 1 ? '' : 's'} selected. They remain in this browser preview and are not uploaded or analysed.`);
  }

  fileInput.addEventListener('change', event => {
    acceptFiles(event.target.files);
    event.target.value = '';
  });
  photoInput.addEventListener('change', event => {
    acceptFiles(event.target.files);
    event.target.value = '';
  });

  function makeMessage(role, text, files = [], visualizations = []) {
    const wrapper = document.createElement('div');
    wrapper.className = role === 'user' ? 'user-message' : 'assistant-message';
    const body = document.createElement('div');
    body.className = 'message-body';
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    const name = document.createElement('strong');
    name.textContent = role === 'user' ? 'You' : 'GeoIntel';
    const time = document.createElement('time');
    time.textContent = 'Just now';
    meta.append(name, time);
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    const paragraph = document.createElement('p');
    paragraph.textContent = String(text || '');
    bubble.append(paragraph);
    if (role === 'user' && files.length) {
      const attached = document.createElement('p');
      attached.className = 'user-attachments';
      attached.textContent = `Attached locally: ${files.map(file => file.name).join(', ')}`;
      bubble.append(attached);
    }
    if (role === 'assistant') {
      const hint = document.createElement('p');
      hint.className = 'message-hint';
      hint.textContent = window.COPILOT_CONFIG?.chatEndpoint
        ? 'Check the evidence and validate the explanation before using it.'
        : 'Preview response only. Connect the Python service for live answers.';
      bubble.append(hint);
      const avatar = document.createElement('span');
      avatar.className = 'message-avatar';
      avatar.setAttribute('aria-hidden', 'true');
      avatar.textContent = '✦';
      wrapper.append(avatar);
    }
    body.append(meta, bubble);
    if (role === 'assistant' && visualizations.length) {
      visualizations.forEach(item => {
        const source = visualizationSource(item);
        if (!source) return;
        const figure = document.createElement('figure');
        figure.className = 'visualization-figure';
        const image = document.createElement('img');
        image.src = source;
        image.alt = item.alt || item.title || 'Geological visualization returned by GeoIntel';
        image.loading = 'lazy';
        image.addEventListener('error', () => {
          figure.classList.add('visualization-error');
          image.removeAttribute('src');
          image.alt = 'Visualization could not be loaded';
        }, { once: true });
        figure.append(image);
        const captionText = item.title || item.caption || item.description;
        if (captionText) {
          const caption = document.createElement('figcaption');
          caption.textContent = captionText;
          figure.append(caption);
        }
        body.append(figure);
      });
    }
    wrapper.append(body);
    chatMessages.append(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return wrapper;
  }

  function makeTyping() {
    const wrapper = document.createElement('div');
    wrapper.className = 'assistant-message typing-message';
    wrapper.innerHTML = '<span class="message-avatar" aria-hidden="true">✦</span><div class="message-body"><div class="message-meta"><strong>GeoIntel</strong><time>Thinking</time></div><div class="message-bubble"><span class="typing-dots" aria-label="Generating reply"><i></i><i></i><i></i></span></div></div>';
    chatMessages.append(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return wrapper;
  }

  function demoAnswer(question, mode) {
    if (mode === 'prospect') {
      return 'I don’t have prospect evidence to inspect in this preview. Add a file or photo to your message; a connected Python service will be needed to read it and return source-linked observations. I can still explain the geology concept in general mode.';
    }
    const q = question.toLowerCase();
    if (q.includes('structural') || q.includes('stratigraphic') || q.includes('trap')) {
      return 'A structural trap holds hydrocarbons because deformation creates a geometry that closes updip, such as a fold or fault-bounded closure. A stratigraphic trap forms where reservoir quality or continuity changes laterally, for example at a pinch-out or facies boundary. Some prospects combine both. This is a general explanation, not an interpretation of your prospect.';
    }
    if (q.includes('attribute') || q.includes('seismic') || q.includes('facies')) {
      return 'Seismic attributes can highlight changes in reflector amplitude, continuity, frequency or geometry that may relate to lithology, fluid or stratigraphic patterns. They are indirect measurements, so interpret them with seismic context, well calibration and alternative explanations in mind. This is general guidance, not an analysis of uploaded data.';
    }
    if (q.includes('fault') || q.includes('seal') || q.includes('transmissive')) {
      return 'Fault sealing depends on factors such as juxtaposition of reservoir against seal, fault-rock properties, displacement, and the fault’s history. A fault can seal in one interval and transmit in another. Check the geometry and available calibration before treating it as a prospect-specific conclusion.';
    }
    if (q.includes('risk') || q.includes('investigate') || q.includes('first') || q.includes('uncertainty')) {
      return 'A useful first pass is to list the play elements—trap, reservoir, seal, charge and timing—then identify the weakest-supported element and what observation could test it. Rank uncertainties by how much they could change the decision. This is a general workflow suggestion, not a finding about your prospect.';
    }
    return 'I can explain geology concepts and exploration methods in this preview. For an open-ended answer, connect the Python chat service. For a prospect-specific interpretation, provide evidence and have the service cite what it used.';
  }

  function visualizationSource(item) {
    if (typeof item === 'string') item = { url: item };
    if (!item || typeof item !== 'object') return '';
    let source = item.url || item.src || item.image_url || item.image || item.data;
    if (typeof source !== 'string' || !source.trim()) return '';
    source = source.trim();
    if (/^data:image\/(png|jpe?g|webp|gif);base64,/i.test(source)) return source;
    if (/^(https?:\/\/|\/|\.\.?\/)/i.test(source)) return source;
    if (item.data === source) {
      const mime = item.mimeType || item.mime_type || 'image/png';
      if (/^image\/(png|jpeg|webp|gif)$/i.test(mime)) return `data:${mime};base64,${source}`;
    }
    return '';
  }

  function readVisualizations(payload, message) {
    let visuals = payload.visualizations ?? payload.visualization ?? message?.visualizations ?? payload.metadata?.visualizations ?? [];
    if (!Array.isArray(visuals)) visuals = [visuals];
    const imageUrl = payload.visualization_url || payload.plot_url || payload.image_url;
    if (imageUrl) visuals.push({ type: 'image', url: imageUrl, title: payload.visualization_title || payload.plot_title || '' });
    if (Array.isArray(message?.content)) {
      message.content.forEach(part => {
        const url = part?.image_url?.url || part?.image_url;
        if (typeof url === 'string') visuals.push({ type: 'image', url, alt: 'Image returned by GeoIntel' });
      });
    }
    return visuals.filter(item => visualizationSource(item));
  }

  async function requestAnswer(question, mode, files) {
    if (files.length) {
      return {
        text: 'I can see the selected file names, but this frontend preview does not send or read file contents yet. Connect the Python upload and analysis service before asking for a file-based interpretation.',
        visualizations: []
      };
    }
    const config = window.COPILOT_CONFIG || {};
    if (!config.chatEndpoint) {
      await new Promise(resolve => window.setTimeout(resolve, 550));
      return { text: demoAnswer(question, mode), visualizations: [] };
    }
    const systemPrompt = mode === 'general'
      ? 'You are GeoIntel, a clear and careful geology assistant. Answer questions across geology and exploration methods in plain language. Distinguish general scientific knowledge from claims about a specific prospect. State uncertainty and do not claim access to files unless they are actually provided.'
      : 'You are GeoIntel, an exploration geoscience assistant. For prospect-specific questions, use only evidence supplied through the connected service, identify its source, distinguish observation from interpretation, compare plausible alternatives, and state uncertainty. If evidence is missing, say so. Do not invent data or conclusions.';
    const response = await fetch(config.chatEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: config.model || 'google/gemma-4-26B-A4B-it',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: question }
        ],
        temperature: 0.3
      })
    });
    if (!response.ok) throw new Error(`The analysis service returned ${response.status}.`);
    const payload = await response.json();
    const message = payload.choices?.[0]?.message;
    const content = message?.content ?? payload.reply ?? payload.answer ?? '';
    const answer = typeof content === 'string'
      ? content
      : Array.isArray(content)
        ? content.filter(part => typeof part?.text === 'string').map(part => part.text).join('\n')
        : JSON.stringify(content);
    const visualizations = readVisualizations(payload, message);
    if (!answer && !visualizations.length) throw new Error('The analysis service returned no answer.');
    return { text: answer, visualizations };
  }

  async function submitQuestion(question) {
    const text = question.trim();
    if (!text || pending) return;
    pending = true;
    const sendButton = chatForm.querySelector('.send-button');
    sendButton.disabled = true;
    const usedFiles = [...pendingAttachments];
    makeMessage('user', text, usedFiles);
    chatInput.value = '';
    chatInput.style.height = '';
    pendingAttachments.splice(0, pendingAttachments.length);
    renderAttachments();
    document.getElementById('suggestedPrompts').classList.add('is-hidden');
    const typing = makeTyping();
    try {
      const answer = await requestAnswer(text, currentMode, usedFiles);
      typing.remove();
      makeMessage('assistant', answer.text, [], answer.visualizations);
    } catch (error) {
      typing.remove();
      makeMessage('assistant', `I couldn’t reach the analysis service. ${error.message} Check the Python API connection and try again.`);
    } finally {
      pending = false;
      sendButton.disabled = false;
      chatInput.focus();
    }
  }

  chatForm.addEventListener('submit', event => {
    event.preventDefault();
    submitQuestion(chatInput.value);
  });
  questionCards.forEach(card => card.addEventListener('click', () => submitQuestion(card.dataset.question)));
  chatInput.addEventListener('input', () => {
    chatInput.style.height = '';
    chatInput.style.height = `${Math.min(chatInput.scrollHeight, 180)}px`;
  });
  chatInput.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      chatForm.requestSubmit();
    }
  });

  renderQuestions();
})();
