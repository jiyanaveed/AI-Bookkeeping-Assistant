import { apiUrl } from "./api.js";

const KEY = "internalAdminKey";

function toast(msg) {
  const el = document.getElementById("admin-toast");
  if (!el) return;
  if (!msg) {
    el.textContent = "";
    el.classList.add("hidden");
    return;
  }
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hdr() {
  const k = document.getElementById("admin-key").value.trim() || localStorage.getItem(KEY) || "";
  return { "X-Admin-Key": k, Accept: "application/json" };
}

function cardSection(title, inner) {
  const wrap = document.createElement("section");
  wrap.className = "surface surface-pad monitor-section";
  const h = document.createElement("h3");
  h.textContent = title;
  wrap.appendChild(h);
  if (typeof inner === "string") {
    const p = document.createElement("p");
    p.className = "empty-panel";
    p.style.padding = "0.5rem 0";
    p.textContent = inner;
    wrap.appendChild(p);
  } else {
    wrap.appendChild(inner);
  }
  return wrap;
}

function kvTable(obj) {
  if (!obj || typeof obj !== "object") {
    const p = document.createElement("p");
    p.className = "empty-panel";
    p.style.padding = "0.5rem 0";
    p.textContent = "—";
    return p;
  }
  const t = document.createElement("table");
  t.className = "kv-table";
  for (const [k, v] of Object.entries(obj)) {
    if (v === null || v === undefined) continue;
    const tr = document.createElement("tr");
    const th = document.createElement("th");
    th.textContent = k;
    const td = document.createElement("td");
    td.textContent = typeof v === "object" ? JSON.stringify(v) : String(v);
    tr.appendChild(th);
    tr.appendChild(td);
    t.appendChild(tr);
  }
  return t;
}

function renderPipelineBoard(rows) {
  const wrap = document.createElement("div");
  if (!rows || !rows.length) {
    wrap.className = "empty-panel";
    wrap.textContent = "No pipeline rows.";
    return wrap;
  }
  const grid = document.createElement("div");
  grid.className = "pipeline-board";
  for (const p of rows) {
    const pill = document.createElement("div");
    pill.className = "pipeline-pill";
    const strong = document.createElement("strong");
    strong.textContent = p.pipeline_name || "—";
    pill.appendChild(strong);
    pill.appendChild(
      document.createTextNode(`${p.enabled ? "On" : "Off"} · ${p.status || ""}`.trim()),
    );
    if (p.reason_text) {
      const small = document.createElement("div");
      small.style.marginTop = "0.35rem";
      small.style.color = "var(--color-muted)";
      small.style.fontSize = "0.75rem";
      small.textContent = p.reason_text;
      pill.appendChild(small);
    }
    grid.appendChild(pill);
  }
  wrap.appendChild(grid);
  return wrap;
}

function renderFlags(rows) {
  const wrap = document.createElement("div");
  if (!rows || !rows.length) {
    wrap.className = "empty-panel";
    wrap.textContent = "No review flags.";
    return wrap;
  }
  for (const f of rows) {
    const row = document.createElement("div");
    row.className = "flag-row";
    const left = document.createElement("div");
    const title = document.createElement("div");
    title.style.fontWeight = "700";
    title.textContent = f.flag_type || "flag";
    const msg = document.createElement("div");
    msg.style.color = "var(--color-muted)";
    msg.style.marginTop = "0.25rem";
    msg.textContent = f.message || "";
    left.appendChild(title);
    left.appendChild(msg);
    const right = document.createElement("div");
    right.style.flexShrink = "0";
    const sev = document.createElement("span");
    sev.className = "badge " + (f.resolved ? "badge-status-cancelled" : "badge-channel");
    sev.textContent = f.resolved ? "Resolved" : (f.severity || "open");
    right.appendChild(sev);
    row.appendChild(left);
    row.appendChild(right);
    wrap.appendChild(row);
  }
  return wrap;
}

function renderTimeline(rows) {
  const wrap = document.createElement("div");
  wrap.className = "timeline";
  if (!rows || !rows.length) {
    const p = document.createElement("p");
    p.className = "empty-panel";
    p.textContent = "No events.";
    wrap.appendChild(p);
    return wrap;
  }
  for (const e of rows) {
    const item = document.createElement("div");
    item.className = "timeline-item";
    const tm = document.createElement("time");
    tm.textContent = e.created_at || "";
    const line = document.createElement("div");
    line.style.marginTop = "0.25rem";
    const strong = document.createElement("strong");
    strong.textContent = e.event_type || "";
    line.appendChild(strong);
    line.appendChild(document.createTextNode(` · ${e.actor_name || ""} `));
    const span = document.createElement("span");
    span.style.color = "var(--color-muted)";
    span.textContent = `(${e.actor_type || ""})`;
    line.appendChild(span);
    item.appendChild(tm);
    item.appendChild(line);
    wrap.appendChild(item);
  }
  return wrap;
}

function renderFieldMatrix(rows) {
  const wrap = document.createElement("div");
  wrap.style.overflowX = "auto";
  if (!rows || !rows.length) {
    wrap.className = "empty-panel";
    wrap.textContent = "No captured fields.";
    return wrap;
  }
  const t = document.createElement("table");
  t.className = "kv-table";
  const head = document.createElement("tr");
  ["Field", "Value", "Source", "Verified"].forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h;
    head.appendChild(th);
  });
  t.appendChild(head);
  for (const f of rows) {
    const tr = document.createElement("tr");
    const val =
      f.value_text ??
      (f.value_json !== undefined && f.value_json !== null ? JSON.stringify(f.value_json) : "—");
    [f.field_name, val, f.source_type, f.verification_status].forEach((cell) => {
      const td = document.createElement("td");
      td.textContent = cell == null ? "—" : String(cell);
      tr.appendChild(td);
    });
    t.appendChild(tr);
  }
  wrap.appendChild(t);
  return wrap;
}

function renderSearchResults(data) {
  const root = document.getElementById("search-results");
  root.innerHTML = "";
  const h = document.createElement("h3");
  h.textContent = "Results";
  h.style.margin = "0 0 0.5rem";
  h.style.fontSize = "0.8125rem";
  h.style.textTransform = "uppercase";
  h.style.letterSpacing = "0.06em";
  h.style.color = "var(--color-muted)";
  root.appendChild(h);
  if (!Array.isArray(data) || !data.length) {
    const p = document.createElement("p");
    p.className = "empty-panel";
    p.style.margin = "0";
    p.textContent = "No matches.";
    root.appendChild(p);
    return;
  }
  const t = document.createElement("table");
  t.className = "kv-table";
  const hr = document.createElement("tr");
  ["User", "Email", "Match"].forEach((x) => {
    const th = document.createElement("th");
    th.textContent = x;
    hr.appendChild(th);
  });
  t.appendChild(hr);
  for (const r of data) {
    const tr = document.createElement("tr");
    [r.user_id, r.email ?? "—", r.match ?? "—"].forEach((c) => {
      const td = document.createElement("td");
      td.textContent = c == null ? "—" : String(c);
      tr.appendChild(td);
    });
    tr.style.cursor = "pointer";
    tr.title = "Click to load monitor";
    tr.addEventListener("click", () => {
      document.getElementById("mon-uid").value = r.user_id;
      document.getElementById("btn-load").click();
    });
    t.appendChild(tr);
  }
  root.appendChild(t);
}

function renderMonitor(data) {
  const root = document.getElementById("monitor-root");
  root.innerHTML = "";
  if (!data.exists) {
    root.appendChild(
      cardSection(
        "Overview",
        `No onboarding profile for user ${data.user_id || ""}. Open onboarding UI or trigger profile creation via API.`,
      ),
    );
    return;
  }

  root.appendChild(cardSection("User overview", kvTable({ ...data.user, user_id: data.user_id })));
  root.appendChild(cardSection("Profile", kvTable(data.profile_overview)));
  if (data.company_verification) {
    root.appendChild(cardSection("Company verification", kvTable(data.company_verification)));
  }
  root.appendChild(cardSection("Field matrix", renderFieldMatrix(data.field_matrix)));
  root.appendChild(cardSection("Pipeline board", renderPipelineBoard(data.pipeline_board)));
  root.appendChild(cardSection("Review flags", renderFlags(data.review_flags)));
  root.appendChild(cardSection("Event timeline", renderTimeline(data.event_timeline)));
}

async function parseJsonResponse(r) {
  const t = await r.text();
  if (!r.ok) {
    throw new Error(t || `${r.status} ${r.statusText}`);
  }
  if (!t) return {};
  try {
    return JSON.parse(t);
  } catch {
    return { raw: t };
  }
}

document.getElementById("admin-key").value = localStorage.getItem(KEY) || "";
document.getElementById("admin-key").addEventListener("change", () => {
  localStorage.setItem(KEY, document.getElementById("admin-key").value.trim());
});

document.getElementById("btn-search").onclick = async () => {
  toast("");
  const q = document.getElementById("search-q").value.trim();
  if (!q) return;
  try {
    const r = await fetch(apiUrl(`/v1/admin/users/search?q=${encodeURIComponent(q)}`), {
      headers: hdr(),
    });
    const data = await parseJsonResponse(r);
    renderSearchResults(Array.isArray(data) ? data : []);
  } catch (e) {
    toast(e.message || String(e));
    document.getElementById("search-results").innerHTML = "";
  }
};

document.getElementById("btn-load").onclick = async () => {
  toast("");
  const uid = document.getElementById("mon-uid").value.trim();
  if (!uid) return;
  try {
    const r = await fetch(apiUrl(`/v1/admin/users/${encodeURIComponent(uid)}/monitor`), { headers: hdr() });
    const data = await parseJsonResponse(r);
    renderMonitor(data);
  } catch (e) {
    toast(e.message || String(e));
  }
};

document.getElementById("btn-route").onclick = async () => {
  toast("");
  const uid = document.getElementById("mon-uid").value.trim();
  if (!uid) return;
  try {
    const r = await fetch(apiUrl(`/v1/admin/users/${encodeURIComponent(uid)}/rerun-routing`), {
      method: "POST",
      headers: hdr(),
    });
    await parseJsonResponse(r);
    document.getElementById("btn-load").click();
  } catch (e) {
    toast(e.message || String(e));
  }
};
