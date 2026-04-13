import * as api from "./api.js";

const CHANNELS = ["in_app", "email", "whatsapp", "slack"];

function el(id) {
  return document.getElementById(id);
}

function showReminderError(msg) {
  const box = el("reminder-alert");
  if (!box) {
    alert(msg);
    return;
  }
  box.textContent = msg;
  box.classList.remove("hidden");
}

function clearReminderError() {
  const box = el("reminder-alert");
  if (!box) return;
  box.textContent = "";
  box.classList.add("hidden");
}

function renderComplianceNote(board) {
  const noteEl = el("compliance-board-note");
  if (!noteEl) return;
  const text = board?.note || "";
  if (!text) {
    noteEl.classList.add("hidden");
    noteEl.textContent = "";
    return;
  }
  noteEl.textContent = text;
  noteEl.classList.remove("hidden");
}

function renderDeadlineList(board) {
  const root = el("deadline-list");
  if (!root) return;
  root.innerHTML = "";
  const deadlines = board?.deadlines || [];
  if (!deadlines.length) {
    root.innerHTML =
      '<p class="empty-panel" style="margin:0">No compliance deadlines stored yet. Complete onboarding with a verified company and an active reminders pipeline.</p>';
    return;
  }
  for (const d of deadlines) {
    root.appendChild(deadlineCard(d));
  }
}

function deadlineCard(d) {
  const article = document.createElement("article");
  article.className = "deadline-card";
  const strong = document.createElement("strong");
  const kindLabel =
    d.deadline_kind === "accounts"
      ? "Annual accounts"
      : d.deadline_kind === "confirmation_statement"
        ? "Confirmation statement"
        : (d.deadline_kind || "").replace(/_/g, " ");
  strong.textContent = d.title || kindLabel;
  const meta = document.createElement("div");
  meta.className = "deadline-meta";
  const co = [d.company_name, d.company_number ? `#${d.company_number}` : null].filter(Boolean).join(" · ");
  meta.textContent = [co || null, `Due ${d.due_date}`, `Source: ${d.source || "Companies House"}`]
    .filter(Boolean)
    .join(" · ");
  article.appendChild(strong);
  article.appendChild(meta);
  return article;
}

function badgeStatus(status) {
  const s = document.createElement("span");
  const st = (status || "").toLowerCase();
  s.className =
    "badge " +
    (st === "cancelled" ? "badge-status-cancelled" : st === "scheduled" ? "badge-status-scheduled" : "badge-channel");
  s.textContent = status || "—";
  return s;
}

function badgeChannel(ch) {
  const s = document.createElement("span");
  s.className = "badge badge-channel";
  s.textContent = (ch || "—").replace(/_/g, " ");
  return s;
}

function badgeOrigin(origin) {
  const s = document.createElement("span");
  s.className = "badge " + (origin === "compliance_auto" ? "badge-status-scheduled" : "badge-channel");
  s.textContent = origin === "compliance_auto" ? "Auto" : "Manual";
  return s;
}

function card(r, userId) {
  const d = document.createElement("article");
  const isAuto = r.origin === "compliance_auto";
  d.className = "rem-card" + (r.status === "cancelled" ? " cancelled" : "") + (isAuto ? " rem-card--auto" : " rem-card--manual");

  const top = document.createElement("div");
  top.className = "rem-card-top";
  const titles = document.createElement("div");
  const h = document.createElement("h3");
  h.className = "rem-card-title";
  h.textContent = r.title || r.reminder_type;
  titles.appendChild(h);
  const sub = document.createElement("div");
  sub.style.fontSize = "0.78rem";
  sub.style.color = "var(--color-muted)";
  sub.style.marginTop = "0.2rem";
  sub.textContent = `Ref · ${r.id.slice(0, 8)}…`;
  titles.appendChild(sub);
  top.appendChild(titles);
  const badges = document.createElement("div");
  badges.style.display = "flex";
  badges.style.flexWrap = "wrap";
  badges.style.gap = "0.35rem";
  badges.appendChild(badgeOrigin(r.origin || "manual"));
  badges.appendChild(badgeStatus(r.status));
  badges.appendChild(badgeChannel(r.channel));
  top.appendChild(badges);
  d.appendChild(top);

  const dl = document.createElement("dl");
  dl.className = "rem-meta-grid";
  const add = (label, value) => {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value ?? "—";
    dl.appendChild(dt);
    dl.appendChild(dd);
  };
  add("Notify on", String(r.reminder_date));
  add("Type", r.reminder_type);
  if (isAuto && r.schedule_offset_label) {
    add("Offset", String(r.schedule_offset_label).replace(/_/g, " "));
  }
  if (isAuto && r.compliance_due_date) {
    add("Statutory due", String(r.compliance_due_date));
  }
  add("Company", r.company_name || r.entity_id || "—");

  d.appendChild(dl);

  const actions = document.createElement("div");
  actions.className = "card-actions";
  if (r.status !== "cancelled") {
    const bCancel = document.createElement("button");
    bCancel.type = "button";
    bCancel.textContent = "Cancel";
    bCancel.className = "btn btn-danger";
    bCancel.onclick = async () => {
      if (!confirm("Cancel this reminder?")) return;
      try {
        await api.postEmpty(`/v1/reminders/${r.id}/cancel`, { user_id: userId });
        clearReminderError();
        await loadReminders(userId);
      } catch (e) {
        showReminderError(e.message || String(e));
      }
    };
    actions.appendChild(bCancel);
    const bEd = document.createElement("button");
    bEd.type = "button";
    bEd.textContent = "Edit date";
    bEd.className = "btn btn-secondary";
    bEd.onclick = () => {
      const nd = prompt("New reminder date (YYYY-MM-DD)", String(r.reminder_date));
      if (!nd) return;
      api
        .patchJson(`/v1/reminders/${r.id}`, { user_id: userId }, { reminder_date: nd })
        .then(() => {
          clearReminderError();
          return loadReminders(userId);
        })
        .catch((e) => showReminderError(e.message || String(e)));
    };
    actions.appendChild(bEd);
  }
  d.appendChild(actions);
  return d;
}

export async function loadReminders(userId) {
  clearReminderError();
  const autoGrid = el("reminder-grid-auto");
  const manualGrid = el("reminder-grid-manual");
  const deadlineRoot = el("deadline-list");

  if (autoGrid) autoGrid.innerHTML = '<p class="empty-panel" style="margin:0">Loading…</p>';
  if (manualGrid) manualGrid.innerHTML = '<p class="empty-panel" style="margin:0">Loading…</p>';
  if (deadlineRoot) deadlineRoot.innerHTML = '<p class="empty-panel" style="margin:0">Loading…</p>';

  if (!userId) {
    const msg = '<p class="empty-panel" style="margin:0">Sign in to load reminders.</p>';
    if (autoGrid) autoGrid.innerHTML = msg;
    if (manualGrid) manualGrid.innerHTML = msg;
    if (deadlineRoot) deadlineRoot.innerHTML = msg;
    return;
  }

  try {
    const board = await api.getJson("/v1/reminders/compliance-board", { user_id: userId });
    renderComplianceNote(board);
    renderDeadlineList(board);

    const rows = await api.getJson("/v1/reminders", { user_id: userId });
    const auto = rows.filter((r) => r.origin === "compliance_auto");
    const manual = rows.filter((r) => r.origin !== "compliance_auto");

    if (autoGrid) {
      autoGrid.innerHTML = "";
      if (!auto.length) {
        autoGrid.innerHTML =
          '<p class="empty-panel" style="margin:0">No automatic schedule yet. Appears after compliance sync.</p>';
      } else {
        for (const r of auto) autoGrid.appendChild(card(r, userId));
      }
    }
    if (manualGrid) {
      manualGrid.innerHTML = "";
      if (!manual.length) {
        manualGrid.innerHTML = '<p class="empty-panel" style="margin:0">No manual reminders.</p>';
      } else {
        for (const r of manual) manualGrid.appendChild(card(r, userId));
      }
    }
  } catch (e) {
    if (autoGrid) autoGrid.innerHTML = "";
    if (manualGrid) manualGrid.innerHTML = "";
    if (deadlineRoot) deadlineRoot.innerHTML = "";
    showReminderError(e.message || String(e));
  }
}

export function bindReminderForm(userIdGetter) {
  const form = el("reminder-form");
  if (!form) return;
  const sel = el("rem-channel");
  if (sel) {
    sel.innerHTML = "";
    for (const c of CHANNELS) {
      const o = document.createElement("option");
      o.value = c;
      o.textContent = c.replace("_", " ");
      sel.appendChild(o);
    }
  }
  const rd = el("rem-date");
  if (rd && !rd.value) {
    const t = new Date();
    t.setDate(t.getDate() + 7);
    rd.value = t.toISOString().slice(0, 10);
  }

  const createBtn = el("btn-create-reminder");
  if (!createBtn) return;

  async function createReminder() {
    clearReminderError();
    const uid = userIdGetter();
    if (!uid) {
      showReminderError("Sign in before creating a reminder.");
      return;
    }
    const cid = el("rem-company-id")?.value.trim();
    const payload = {
      user_id: uid,
      title: el("rem-title")?.value || null,
      reminder_type: el("rem-type")?.value || "custom",
      reminder_date: el("rem-date")?.value,
      channel: el("rem-channel")?.value,
      entity_type: el("rem-entity-type")?.value.trim() || null,
      entity_id: el("rem-entity-id")?.value.trim() || null,
      company_id: cid || null,
    };
    try {
      await api.postJson("/v1/reminders", payload);
      form.reset();
      if (el("rem-type")) el("rem-type").value = "custom";
      const rd2 = el("rem-date");
      if (rd2) {
        const t = new Date();
        t.setDate(t.getDate() + 7);
        rd2.value = t.toISOString().slice(0, 10);
      }
      await loadReminders(uid);
    } catch (err) {
      showReminderError(err.message || String(err));
    }
  }

  createBtn.addEventListener("click", () => void createReminder());
}
