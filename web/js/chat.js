import * as api from "./api.js";

const UI = {
  msgs: null,
  input: null,
  pending: null,
  convHint: null,
};

let pendingAttachments = [];

export function bindChat(elements) {
  Object.assign(UI, elements);
}

function emptyChatPlaceholder() {
  const wrap = document.createElement("div");
  wrap.className = "chat-empty";
  const icon = document.createElement("div");
  icon.className = "chat-empty-icon";
  icon.textContent = "💬";
  const h = document.createElement("h3");
  h.textContent = "Start the conversation";
  const p = document.createElement("p");
  p.textContent = "Ask a question or attach a document. Your thread is isolated per test user ID above.";
  wrap.appendChild(icon);
  wrap.appendChild(h);
  wrap.appendChild(p);
  return wrap;
}

export async function refreshHistory(userId, conversationId) {
  if (!UI.msgs) return;
  if (!conversationId) {
    UI.msgs.innerHTML = "";
    UI.msgs.appendChild(emptyChatPlaceholder());
    return;
  }
  let rows;
  try {
    rows = await api.getJson(`/v1/conversations/${conversationId}/messages`, { user_id: userId });
  } catch {
    UI.msgs.innerHTML = "";
    UI.msgs.appendChild(emptyChatPlaceholder());
    return;
  }
  UI.msgs.innerHTML = "";
  if (!rows.length) {
    UI.msgs.appendChild(emptyChatPlaceholder());
    return;
  }
  for (const m of rows) {
    renderMessage(m, userId);
  }
  UI.msgs.scrollTop = UI.msgs.scrollHeight;
}

function renderMessage(m, userId) {
  const div = document.createElement("div");
  div.className = `bubble ${m.sender_type === "user" ? "user" : "assistant"}`;
  const meta = document.createElement("div");
  meta.className = "meta";
  const spending = m.intent === "spending" ? " · spending" : "";
  meta.textContent =
    m.sender_type === "user"
      ? `You${spending}`
      : `${m.agent_name || "Assistant"} · verified answers use Companies House where noted`;
  div.appendChild(meta);
  const text = document.createElement("div");
  text.textContent = m.message_text;
  div.appendChild(text);
  if (m.attachments && m.attachments.length) {
    const prev = document.createElement("div");
    prev.className = "attach-preview";
    for (const a of m.attachments) {
      const chip = document.createElement("span");
      chip.className = "attach-chip";
      const isImg = (a.content_type || "").startsWith("image/");
      if (isImg) {
        const img = document.createElement("img");
        img.src = api.fileUrl(a.file_id, userId);
        img.alt = a.filename;
        img.style.maxWidth = "180px";
        img.style.maxHeight = "120px";
        img.style.borderRadius = "6px";
        img.style.display = "block";
        chip.appendChild(img);
        const link = document.createElement("a");
        link.href = api.fileUrl(a.file_id, userId);
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = a.filename;
        link.style.display = "block";
        chip.appendChild(link);
      } else {
        const link = document.createElement("a");
        link.href = api.fileUrl(a.file_id, userId);
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = a.filename;
        chip.appendChild(link);
      }
      prev.appendChild(chip);
    }
    div.appendChild(prev);
  }
  UI.msgs.appendChild(div);
}

export async function handleFileInput(userId, inputEl) {
  const files = inputEl.files;
  if (!files || !files.length) return;
  const res = await api.uploadFiles(userId, Array.from(files));
  for (const u of res.uploads) {
    pendingAttachments.push({ id: u.id, name: u.original_filename, contentType: u.content_type });
  }
  renderPending();
  inputEl.value = "";
}

function renderPending() {
  if (!UI.pending) return;
  UI.pending.innerHTML = "";
  if (!pendingAttachments.length) return;
  const lab = document.createElement("span");
  lab.className = "pending-label";
  lab.textContent = "Queued:";
  UI.pending.appendChild(lab);
  for (const p of pendingAttachments) {
    const s = document.createElement("span");
    s.className = "attach-chip";
    s.textContent = p.name;
    UI.pending.appendChild(s);
  }
}

export function clearPending() {
  pendingAttachments = [];
  renderPending();
}

export async function sendMessage(userId, conversationId, text, options = {}) {
  const body = {
    message: text,
    user_id: userId,
    conversation_id: conversationId || null,
    attachment_ids: pendingAttachments.map((p) => p.id),
  };
  if (options.messageIntent) {
    body.message_intent = options.messageIntent;
  }
  const out = await api.postJson("/v1/chat", body);
  clearPending();
  return out;
}
