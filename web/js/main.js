import * as chat from "./chat.js";
import * as rem from "./reminders.js";

const KEY_UID = "internalTestUserId";
const KEY_CID = "internalConversationId";
const KEY_CONV_UID = "internalConversationOwnerId";

function userId() {
  const el = document.getElementById("user-id");
  if (el && el.value.trim()) return el.value.trim();
  return localStorage.getItem("auth_user_id") || localStorage.getItem(KEY_UID) || "";
}

function saveUserId() {
  const el = document.getElementById("user-id");
  const v = el ? el.value.trim() : "";
  if (v) localStorage.setItem(KEY_UID, v);
}

/** Conversation id only if it was created under the current test user (avoids 404 after switching users). */
function conversationIdForUser(uid) {
  const cid = localStorage.getItem(KEY_CID);
  const owner = localStorage.getItem(KEY_CONV_UID);
  if (!cid || !uid) return null;
  if (!owner || owner !== uid) return null;
  return cid;
}

function showView(name) {
  document.getElementById("view-chat").classList.toggle("hidden", name !== "chat");
  document.getElementById("view-reminders").classList.toggle("hidden", name !== "reminders");
  document.querySelectorAll(".nav-cluster .nav-item[data-view]").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === name);
  });
}

function setConvHint() {
  const hint = document.getElementById("conv-hint");
  const uid = userId();
  const cid = conversationIdForUser(uid);
  if (cid) {
    hint.innerHTML = `Thread <strong>${cid.slice(0, 8)}…</strong>`;
  } else {
    hint.innerHTML = "No active thread — send a message to start";
  }
}

function clearConversationKeys() {
  localStorage.removeItem(KEY_CID);
  localStorage.removeItem(KEY_CONV_UID);
}

async function doSend() {
  const box = document.getElementById("chat-input");
  const text = box.value.trim();
  if (!text) return;

  saveUserId();
  const uid = userId();
  if (!uid) {
    alert("Missing user id. Log in again or set test user ID.");
    return;
  }

  const sendBtn = document.getElementById("btn-send");
  sendBtn.disabled = true;
  try {
    const cid = conversationIdForUser(uid);
    const spendBox = document.getElementById("record-spending");
    const messageIntent = spendBox?.checked ? "spending" : undefined;
    const out = await chat.sendMessage(uid, cid, text, { messageIntent });
    localStorage.setItem(KEY_CID, out.conversation_id);
    localStorage.setItem(KEY_CONV_UID, uid);
    setConvHint();
    box.value = "";
    await chat.refreshHistory(uid, out.conversation_id);
  } catch (err) {
    alert(err.message || String(err));
  } finally {
    sendBtn.disabled = false;
  }
}

async function init() {
  const uidInput = document.getElementById("user-id");
  if (uidInput) {
    uidInput.value =
      localStorage.getItem("auth_user_id") ||
      localStorage.getItem(KEY_UID) ||
      "00000000-0000-0000-0000-000000000001";
    uidInput.addEventListener("change", () => {
      saveUserId();
      clearConversationKeys();
      setConvHint();
      void chat.refreshHistory(userId(), conversationIdForUser(userId()));
    });
  }

  chat.bindChat({
    msgs: document.getElementById("chat-msgs"),
    input: document.getElementById("chat-input"),
    pending: document.getElementById("pending-files"),
    convHint: document.getElementById("conv-hint"),
  });

  rem.bindReminderForm(userId);

  document.querySelectorAll(".nav-cluster .nav-item[data-view]").forEach((b) => {
    b.onclick = () => {
      showView(b.dataset.view);
      if (b.dataset.view === "reminders") rem.loadReminders(userId());
    };
  });

  document.getElementById("btn-new-chat").onclick = () => {
    clearConversationKeys();
    setConvHint();
    chat.refreshHistory(userId(), null);
  };

  document.getElementById("btn-refresh-chat").onclick = async () => {
    saveUserId();
    await chat.refreshHistory(userId(), conversationIdForUser(userId()));
  };

  document.getElementById("file-input").onchange = (e) => {
    chat.handleFileInput(userId(), e.target);
  };

  const chatForm = document.getElementById("chat-form");
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    void doSend();
  });

  document.getElementById("btn-send").addEventListener("click", () => {
    void doSend();
  });

  const chatInput = document.getElementById("chat-input");
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void doSend();
    }
  });

  document.getElementById("btn-rem-refresh").onclick = () => {
    saveUserId();
    rem.loadReminders(userId());
  };

  setConvHint();

  const start = new URLSearchParams(window.location.search).get("view");
  if (start === "reminders") {
    showView("reminders");
    try {
      await rem.loadReminders(userId());
    } catch (e) {
      console.warn("loadReminders", e);
    }
  } else {
    showView("chat");
  }

  try {
    await chat.refreshHistory(userId(), conversationIdForUser(userId()));
  } catch (e) {
    console.warn("refreshHistory", e);
  }
}

init();
