import { apiUrl } from "./api.js";
import { bootOnboardingShell, getToken, logoutApi } from "./gate.js";

const ME = await bootOnboardingShell();
if (!ME) {
  throw new Error("redirect");
}

function uid() {
  return ME.user_id;
}

document.getElementById("auth-email-display").textContent = ME.email || ME.user_id.slice(0, 8) + "…";
document.getElementById("btn-onb-logout")?.addEventListener("click", async () => {
  await logoutApi();
  window.location.href = "/internal/login.html";
});

async function api(method, path, body, headers = {}) {
  const t = getToken();
  const h = {
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
    ...headers,
  };
  if (body != null && method !== "GET") h["Content-Type"] = "application/json";
  const r = await fetch(apiUrl(path), {
    method,
    headers: h,
    body: body != null && method !== "GET" ? JSON.stringify(body) : undefined,
  });
  const txt = await r.text();
  if (!r.ok) throw new Error(txt || String(r.status));
  try {
    return JSON.parse(txt);
  } catch {
    return txt;
  }
}

function setStatusLine(text) {
  const el = document.getElementById("verify-inline-status");
  if (el) el.textContent = text || "";
}

function feedbackRoot() {
  return document.getElementById("onboarding-feedback");
}

function clearFeedback() {
  const root = feedbackRoot();
  if (root) root.innerHTML = "";
}

function humanLabel(snake) {
  if (snake == null || snake === "") return "—";
  return String(snake)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function humanPipelineName(name) {
  const map = {
    companies_house: "Companies House compliance",
    bookkeeping: "Bookkeeping",
  };
  return map[name] || humanLabel(name);
}

function appendBanner(root, variant, title, detail) {
  const b = document.createElement("div");
  b.className = `ob-banner ob-banner--${variant}`;
  const h = document.createElement("p");
  h.className = "ob-banner__title";
  h.textContent = title;
  b.appendChild(h);
  if (detail) {
    const p = document.createElement("p");
    p.className = "ob-banner__detail";
    p.textContent = detail;
    b.appendChild(p);
  }
  root.appendChild(b);
}

function appendStatusCard(root, st) {
  if (!st || !st.profile) return;
  const prof = st.profile;
  const card = document.createElement("div");
  card.className = "ob-card";
  const h = document.createElement("h3");
  h.className = "ob-card__title";
  h.textContent = "Profile status";
  card.appendChild(h);
  const grid = document.createElement("div");
  grid.className = "ob-card__grid";

  const row = (label, value) => {
    const lk = document.createElement("p");
    lk.className = "ob-card__label";
    lk.textContent = label;
    const vv = document.createElement("p");
    vv.className = "ob-card__value";
    vv.textContent = value == null || value === "" ? "—" : String(value);
    grid.appendChild(lk);
    grid.appendChild(vv);
  };

  row("Completion", `${prof.completion_percent ?? 0}%`);
  row("Onboarding status", humanLabel(prof.status));
  row("Stage", humanLabel(prof.onboarding_stage));
  row("Acting as", humanLabel(prof.acting_as));
  row("Business type", humanLabel(prof.business_type));

  const cl = st.company_link;
  if (cl && (cl.matched_company_name || cl.matched_company_number)) {
    const ch = cl.companies_house_verified ? "Verified at Companies House" : "Companies House";
    row(
      ch,
      [cl.matched_company_name, cl.matched_company_number ? `#${cl.matched_company_number}` : ""]
        .filter(Boolean)
        .join(" · ") || "—",
    );
  }

  const nFields = (st.fields || []).length;
  row("Saved fields", String(nFields));

  card.appendChild(grid);
  root.appendChild(card);
}

function appendWorkflowCards(root, pipelines) {
  if (!pipelines || !pipelines.length) return;
  const card = document.createElement("div");
  card.className = "ob-card";
  const h = document.createElement("h3");
  h.className = "ob-card__title";
  h.textContent = "Workflow summary";
  card.appendChild(h);
  const grid = document.createElement("div");
  grid.className = "ob-workflow-grid";
  for (const p of pipelines) {
    const w = document.createElement("div");
    w.className = "ob-workflow-card";
    const head = document.createElement("div");
    head.className = "ob-workflow-card__head";
    const name = document.createElement("p");
    name.className = "ob-workflow-card__name";
    name.textContent = humanPipelineName(p.pipeline_name);
    const pill = document.createElement("span");
    pill.className = `ob-pill ${p.enabled ? "ob-pill--on" : "ob-pill--off"}`;
    pill.textContent = p.enabled ? "Enabled" : "Off";
    head.appendChild(name);
    head.appendChild(pill);
    w.appendChild(head);
    const st = document.createElement("p");
    st.className = "ob-workflow-card__status";
    st.textContent = `Status: ${humanLabel(p.status)} · ${humanLabel(p.activation_source || "")}`;
    w.appendChild(st);
    if (p.reason_text) {
      const r = document.createElement("p");
      r.className = "ob-workflow-card__reason";
      r.textContent = p.reason_text;
      w.appendChild(r);
    }
    grid.appendChild(w);
  }
  card.appendChild(grid);
  root.appendChild(card);
}

function appendReviewCallouts(root, flags) {
  const open = (flags || []).filter((f) => !f.resolved);
  if (!open.length) return;
  const card = document.createElement("div");
  card.className = "ob-card";
  const h = document.createElement("h3");
  h.className = "ob-card__title";
  h.textContent = "Review needed";
  card.appendChild(h);
  for (const f of open) {
    const sev = (f.severity || "medium").toLowerCase();
    const box = document.createElement("div");
    box.className = `ob-callout ob-callout--${sev === "high" || sev === "critical" ? "high" : sev === "low" ? "low" : "medium"}`;
    const meta = document.createElement("div");
    meta.className = "ob-callout__meta";
    const typ = document.createElement("p");
    typ.className = "ob-callout__type";
    typ.textContent = [humanLabel(f.flag_type), f.field_name ? humanLabel(f.field_name) : ""].filter(Boolean).join(" · ");
    meta.appendChild(typ);
    box.appendChild(meta);
    const msg = document.createElement("p");
    msg.className = "ob-callout__message";
    msg.textContent = f.message || "";
    box.appendChild(msg);
    card.appendChild(box);
  }
  root.appendChild(card);
}

function scrollFeedbackIntoView() {
  feedbackRoot()?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderFeedbackSave(fieldsOut, state) {
  clearFeedback();
  const root = feedbackRoot();
  if (!root) return;
  const pct = fieldsOut?.completion_percent;
  appendBanner(root, "success", "Progress saved", pct != null ? `Completion is now ${pct}%.` : "Your answers were stored.");
  appendStatusCard(root, state);
  appendWorkflowCards(root, state?.pipelines);
  appendReviewCallouts(root, state?.review_flags);
  scrollFeedbackIntoView();
}

function renderFeedbackRoutingFull(state) {
  clearFeedback();
  const root = feedbackRoot();
  if (!root) return;
  appendBanner(root, "success", "Routing updated", "Workflow rules and review checks were refreshed.");
  appendStatusCard(root, state);
  appendWorkflowCards(root, state?.pipelines);
  appendReviewCallouts(root, state?.review_flags);
  scrollFeedbackIntoView();
}

function renderFeedbackSubmit(result) {
  clearFeedback();
  const root = feedbackRoot();
  if (!root) return;
  const status = result?.status;
  const summary = result?.summary;
  appendBanner(
    root,
    "success",
    "Onboarding submitted",
    "Opening your setup summary — you can still fix details from the workspace if needed.",
  );
  if (summary) {
    const card = document.createElement("div");
    card.className = "ob-card";
    const h = document.createElement("h3");
    h.className = "ob-card__title";
    h.textContent = "Submission summary";
    card.appendChild(h);
    const grid = document.createElement("div");
    grid.className = "ob-card__grid";
    const row = (label, value) => {
      const lk = document.createElement("p");
      lk.className = "ob-card__label";
      lk.textContent = label;
      const vv = document.createElement("p");
      vv.className = "ob-card__value";
      vv.textContent = value == null || value === "" ? "—" : String(value);
      grid.appendChild(lk);
      grid.appendChild(vv);
    };
    row("Workspace status", humanLabel(status));
    row("Completion", `${summary.completion_percent ?? 0}%`);
    row("Business type", humanLabel(summary.business_type));
    row("Fields captured", String(summary.field_count ?? "—"));
    if (summary.pipelines && typeof summary.pipelines === "object") {
      const keys = Object.keys(summary.pipelines);
      row(
        "Active workflows",
        keys.length ? keys.map((k) => `${humanPipelineName(k)} (${summary.pipelines[k].enabled ? "on" : "off"})`).join(", ") : "—",
      );
    }
    card.appendChild(grid);
    root.appendChild(card);
  }
  scrollFeedbackIntoView();
}

function renderFeedbackError(message) {
  clearFeedback();
  const root = feedbackRoot();
  if (!root) return;
  appendBanner(root, "error", "Something went wrong", message || "Request failed. Try again.");
  scrollFeedbackIntoView();
}

function formatCoLine(row) {
  const parts = [];
  if (row.company_number) parts.push(`#${row.company_number}`);
  if (row.company_status) parts.push(row.company_status);
  if (row.match_score != null) parts.push(`score ${row.match_score}`);
  return parts.length ? ` · ${parts.join(" · ")}` : "";
}

function addDefRow(dl, label, value) {
  if (value == null || value === "") return;
  const dt = document.createElement("dt");
  dt.textContent = label;
  const dd = document.createElement("dd");
  dd.textContent = String(value);
  dl.appendChild(dt);
  dl.appendChild(dd);
}

function buildStrongMatchBlock(profile, titleText) {
  const wrap = document.createElement("div");
  const h = document.createElement("h3");
  h.className = "verify-panel__title";
  h.textContent = titleText;
  wrap.appendChild(h);
  const badgeRow = document.createElement("p");
  badgeRow.style.margin = "0 0 0.75rem";
  const badge = document.createElement("span");
  badge.className = "verify-panel__badge verify-panel__badge--ok";
  badge.textContent = "Strong match";
  badgeRow.appendChild(badge);
  wrap.appendChild(badgeRow);
  const dl = document.createElement("dl");
  dl.className = "verify-panel__dl";
  addDefRow(dl, "Company name", profile.company_name);
  addDefRow(dl, "Company number", profile.company_number);
  addDefRow(dl, "Company status", profile.company_status);
  wrap.appendChild(dl);
  return wrap;
}

function buildAmbiguousList(strong, framing) {
  const wrap = document.createElement("div");
  const h = document.createElement("h3");
  h.className = "verify-panel__title";
  h.textContent = "Companies House — choose a company";
  wrap.appendChild(h);
  if (framing) {
    const p = document.createElement("p");
    p.className = "verify-panel__muted";
    p.textContent = framing;
    wrap.appendChild(p);
  }
  const ul = document.createElement("ul");
  ul.className = "verify-panel__list";
  for (const row of strong) {
    const li = document.createElement("li");
    li.className = "verify-panel__item";
    const meta = document.createElement("div");
    meta.className = "verify-panel__item-meta";
    const nameEl = document.createElement("strong");
    nameEl.textContent = row.company_name || "—";
    const line = document.createElement("span");
    line.textContent = formatCoLine(row);
    meta.appendChild(nameEl);
    meta.appendChild(line);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-secondary";
    btn.style.fontSize = "0.78rem";
    btn.style.padding = "0.35rem 0.6rem";
    btn.textContent = "Use this company";
    btn.setAttribute("data-verify-number", row.company_number || "");
    li.appendChild(meta);
    li.appendChild(btn);
    ul.appendChild(li);
  }
  wrap.appendChild(ul);
  return wrap;
}

function buildWeakList(weak) {
  const ul = document.createElement("ul");
  ul.className = "verify-panel__list";
  for (const row of weak.slice(0, 8)) {
    const li = document.createElement("li");
    li.className = "verify-panel__item";
    const meta = document.createElement("div");
    meta.className = "verify-panel__item-meta";
    const nameEl = document.createElement("strong");
    nameEl.textContent = row.company_name || "—";
    const line = document.createElement("span");
    line.textContent = formatCoLine(row);
    meta.appendChild(nameEl);
    meta.appendChild(line);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-secondary";
    btn.style.fontSize = "0.78rem";
    btn.style.padding = "0.35rem 0.6rem";
    btn.textContent = "Look up by number";
    btn.setAttribute("data-verify-number", row.company_number || "");
    li.appendChild(meta);
    li.appendChild(btn);
    ul.appendChild(li);
  }
  return ul;
}

function wireVerifyNumberButtons(panel) {
  panel.querySelectorAll("[data-verify-number]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const num = btn.getAttribute("data-verify-number");
      if (!num) return;
      btn.disabled = true;
      try {
        const data = await api("POST", `/v1/onboarding/${uid()}/verify-company`, { query: num });
        renderVerificationPanel(data);
        setStatusLine(data.ok === false ? (data.error || "Verification failed.") : "Companies House verification updated.");
      } catch (e) {
        renderVerificationPanel({ ok: false, error: String(e.message) });
        setStatusLine("Verification request failed.");
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function renderVerificationPanel(data) {
  const panel = document.getElementById("verify-panel");
  if (!panel) return;

  panel.innerHTML = "";
  if (data == null) {
    panel.classList.add("hidden");
    return;
  }

  panel.classList.remove("hidden");

  if (typeof data === "string") {
    const p = document.createElement("p");
    p.className = "verify-panel__error";
    p.textContent = data;
    panel.appendChild(p);
    return;
  }

  if (data.ok === false) {
    const p = document.createElement("p");
    p.className = "verify-panel__error";
    p.textContent = data.error || "Verification failed.";
    panel.appendChild(p);
    return;
  }

  if (data.match_status === "strong_match" && data.profile && data.profile.company_number) {
    panel.appendChild(buildStrongMatchBlock(data.profile, "Companies House verification"));
    return;
  }

  const classified = data.classified;
  const profile = data.profile;

  if (profile && profile.company_name) {
    panel.appendChild(buildStrongMatchBlock(profile, "Companies House verification"));
    const ignored = classified && classified.alternate_strong_candidates_ignored;
    if (ignored > 0) {
      const note = document.createElement("p");
      note.className = "verify-panel__muted";
      note.textContent =
        "Other similar listings were not selected because one result clearly matches your search. Your profile is linked to the company above.";
      panel.appendChild(note);
    }
    return;
  }

  if (classified) {
    const strong = classified.strong_matches || [];
    if (strong.length > 1) {
      panel.appendChild(buildAmbiguousList(strong, classified.response_framing));
      wireVerifyNumberButtons(panel);
      return;
    }

    const h = document.createElement("h3");
    h.className = "verify-panel__title";
    h.textContent = "Companies House — no strong name match";
    panel.appendChild(h);
    const expl = document.createElement("p");
    expl.className = "verify-panel__muted";
    const assess = classified.match_assessment || "";
    expl.textContent =
      classified.response_framing ||
      (assess === "no_results"
        ? "No results for that search. Try the 8-digit company registration number."
        : "Try a different spelling or search by company number.");
    panel.appendChild(expl);

    const weak = classified.loosely_related_candidates || [];
    if (weak.length) {
      panel.appendChild(buildWeakList(weak));
      wireVerifyNumberButtons(panel);
    }
  }
}

function collectFields() {
  const fields = [];
  const add = (name, el) => {
    const v = el.value?.trim();
    if (!v) return;
    fields.push({ field_name: name, value_text: v, source_type: "user_provided" });
  };
  add("acting_as", document.getElementById("acting_as"));
  add("business_type", document.getElementById("business_type"));
  add("company_registration_status", document.getElementById("company_registration_status"));
  add("company_name_or_number", document.getElementById("company_name_or_number"));
  add("company_trade_status", document.getElementById("company_trade_status"));
  const inc = document.getElementById("income_types").value.trim();
  if (inc) fields.push({ field_name: "income_types", value_json: inc.split(",").map((s) => s.trim()), source_type: "user_provided" });
  add("self_assessment_registered", document.getElementById("self_assessment_registered"));
  add("vat_status", document.getElementById("vat_status"));
  add("payroll_status", document.getElementById("payroll_status"));
  add("estimated_12_month_taxable_turnover", document.getElementById("estimated_12_month_taxable_turnover"));
  add("preferred_reminder_channel", document.getElementById("preferred_reminder_channel"));
  add("email", document.getElementById("email"));
  add("phone_number", document.getElementById("phone_number"));
  add("business_start_date", document.getElementById("business_start_date"));
  return fields;
}

function toggleLtd() {
  const bt = document.getElementById("business_type").value;
  const ltd = bt === "limited_company";
  document.getElementById("wrap-reg").classList.toggle("hidden", !ltd);
  document.getElementById("wrap-co").classList.toggle("hidden", !ltd);
  document.getElementById("wrap-trade").classList.toggle("hidden", !ltd);
}

document.getElementById("business_type").onchange = toggleLtd;
toggleLtd();

if (ME.email) {
  const em = document.getElementById("email");
  if (em && !em.value) em.value = ME.email;
}

document.getElementById("btn-save").onclick = async () => {
  try {
    const out = await api("PUT", `/v1/onboarding/${uid()}/fields`, { fields: collectFields() });
    const st = await api("GET", `/v1/onboarding/${uid()}/state`);
    renderFeedbackSave(out, st);
  } catch (e) {
    renderFeedbackError(String(e.message));
  }
};

document.getElementById("btn-verify").onclick = async () => {
  const q = document.getElementById("company_name_or_number").value.trim();
  if (!q) return alert("Enter company name or number");
  try {
    const data = await api("POST", `/v1/onboarding/${uid()}/verify-company`, { query: q });
    renderVerificationPanel(data);
    setStatusLine(
      data.ok === false ? (data.error || "Verification failed.") : "Companies House verification updated. Details above.",
    );
  } catch (e) {
    renderVerificationPanel({ ok: false, error: String(e.message) });
    setStatusLine("Verification request failed.");
  }
};

document.getElementById("btn-route").onclick = async () => {
  try {
    const body = { fields: collectFields() };
    await api("POST", `/v1/onboarding/${uid()}/evaluate-routing`, body);
    const st = await api("GET", `/v1/onboarding/${uid()}/state`);
    renderFeedbackRoutingFull(st);
  } catch (e) {
    renderFeedbackError(String(e.message));
  }
};

document.getElementById("btn-submit").onclick = async () => {
  try {
    const result = await api("POST", `/v1/onboarding/${uid()}/submit`, { fields: collectFields() });
    renderFeedbackSubmit(result);
    setTimeout(() => {
      window.location.href = "/internal/setup-summary.html";
    }, 450);
  } catch (e) {
    renderFeedbackError(String(e.message));
  }
};
