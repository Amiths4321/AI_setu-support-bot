const launcher = document.getElementById('launcher');
const chatPanel = document.getElementById('chatPanel');
const closeBtn = document.getElementById('closeBtn');
const resetBtn = document.getElementById('resetBtn');
const chatBody = document.getElementById('chatBody');
const quickRepliesEl = document.getElementById('quickReplies');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const apiBaseInput = document.getElementById('apiBase');
const connStatus = document.getElementById('connStatus');

let sessionId = crypto.randomUUID();
let hasOpenedOnce = false;

function apiBase() {
  return apiBaseInput.value.replace(/\/+$/, '');
}

async function fetchJSON(path, body) {
  const res = await fetch(apiBase() + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('Request failed: ' + path);
  return res.json();
}

function setConn(ok) {
  connStatus.classList.remove('ok', 'err');
  connStatus.classList.add(ok ? 'ok' : 'err');
  connStatus.innerHTML = `<i class="dot"></i> ${ok ? 'connected' : 'unreachable'}`;
}

async function pingHealth() {
  try {
    const res = await fetch(apiBase() + '/api/health');
    setConn(res.ok);
  } catch (e) {
    setConn(false);
  }
}

function addBubble(text, who) {
  const row = document.createElement('div');
  row.className = `bubble-row ${who}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  row.appendChild(bubble);
  chatBody.appendChild(row);
  chatBody.scrollTop = chatBody.scrollHeight;
  return row;
}

function addTypingIndicator() {
  const row = document.createElement('div');
  row.className = 'bubble-row bot';
  row.innerHTML = `<div class="bubble typing-bubble"><span></span><span></span><span></span></div>`;
  chatBody.appendChild(row);
  chatBody.scrollTop = chatBody.scrollHeight;
  return row;
}

function renderQuickReplies(options) {
  quickRepliesEl.innerHTML = '';
  (options || []).forEach(opt => {
    const btn = document.createElement('button');
    btn.textContent = opt;
    btn.addEventListener('click', () => sendMessage(opt));
    quickRepliesEl.appendChild(btn);
  });
}

async function sendMessage(text) {
  text = text.trim();
  if (!text) return;

  addBubble(text, 'user');
  renderQuickReplies([]); // clear old quick replies once the user has acted
  chatInput.value = '';

  const typingRow = addTypingIndicator();

  try {
    const data = await fetchJSON('/api/chat', { session_id: sessionId, message: text });
    setConn(true);
    // small artificial delay so the typing indicator is perceptible — purely cosmetic
    await new Promise(r => setTimeout(r, 350));
    typingRow.remove();
    addBubble(data.reply, 'bot');
    renderQuickReplies(data.quick_replies);
  } catch (e) {
    setConn(false);
    typingRow.remove();
    addBubble("I'm having trouble reaching the bank's servers right now. Please try again in a moment.", 'bot');
  }
}

function openPanel() {
  chatPanel.hidden = false;
  launcher.style.display = 'none';
  if (!hasOpenedOnce) {
    hasOpenedOnce = true;
    sendMessage('hi');
  }
}

function closePanel() {
  chatPanel.hidden = true;
  launcher.style.display = 'flex';
}

launcher.addEventListener('click', openPanel);
closeBtn.addEventListener('click', closePanel);

resetBtn.addEventListener('click', async () => {
  try {
    await fetchJSON('/api/reset', { session_id: sessionId });
  } catch (e) {
    // even if the reset call fails, still clear the visible chat locally
  }
  chatBody.innerHTML = '';
  renderQuickReplies([]);
  sendMessage('hi');
});

chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  sendMessage(chatInput.value);
});

pingHealth();
setInterval(pingHealth, 5000);
