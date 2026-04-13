import { apiUrl } from "./api.js";
import { requireAuthForSummary, logoutApi, APP_ACCESS_STATUSES, getToken } from "./gate.js";

document.getElementById("btn-logout")?.addEventListener("click", async () => {
  await logoutApi();
  window.location.href = "/internal/login.html";
});

const me = await requireAuthForSummary();
if (!me) {
  throw new Error("auth");
}

const uid = me.user_id;
const token = getToken();

const banner = document.getElementById("banner");
const incomplete = document.getElementById("incomplete-panel");
const root = document.getElementById("summary-root");
const cta = document.getElementById("cta-wrap");

/** Onboarding field keys → client-facing labels */
const FIELD_LABELS = {
  acting_as: "Acting as",
  business_type: "Business type",
  company_registration_status: "Company registration",
  company_name_or_number: "Company name or number",
  company_trade_status: "Trading status",
  income_types: "Income types",
  self_assessment_registered: "Self Assessment",
  vat_status: "VAT",
  payroll_status: "Payroll",
  preferred_reminder_channel: "Reminder channel",
  email: "Email",
  phone_number: "Phone",
  estimated_12_month_taxable_turnover: "Estimated annual turnover (taxable)",
  business_start_date: "Business start date",
  utr_available: "UTR available",
  government_gateway_access: "Government Gateway access",
  vat_number: "VAT number",
  first_payday_date: "First payday",
  paye_reference_available: "PAYE reference available",
  employee_count: "Number of employees",
  uk_nation: "Nation (UK)",
  estimated_annual_self_employment_income: "Estimated self-employment income",
  estimated_annual_property_income: "Estimated property income",
};

/** Enum-like values → readable text */
const VALUE_LABELS = {
  // acting_as
  self: "Yourself only",
  my_business: "My business",
  my_company_and_me: "My company and me",
  accountant_or_bookkeeper_for_clients: "Accountant or bookkeeper (for clients)",
  // business_type
  sole_trader: "Sole trader",
  limited_company: "Limited company",
  landlord: "Landlord",
  sole_trader_and_landlord: "Sole trader and landlord",
  partnership: "Partnership",
  accountant_or_bookkeeper: "Accountant or bookkeeper",
  not_sure: "Not sure yet",
  // company_registration_status
  already_registered: "Already registered",
  want_to_register: "Planning to register",
  registration_in_progress: "Registration in progress",
  // company_trade_status
  actively_trading: "Actively trading",
  not_yet_trading: "Not yet trading",
  dormant: "Dormant",
  // self_assessment / yes-no style
  yes: "Yes",
  no: "No",
  // vat
  vat_registered: "VAT registered",
  not_vat_registered: "Not VAT registered",
  monitor_threshold: "Monitoring VAT threshold",
  // payroll
  no_employees: "No employees",
  director_only: "Director only (no other staff)",
  has_employees: "Has employees",
  // reminders
  in_app: "In the app",
  email: "Email",
  whatsapp: "WhatsApp",
  slack: "Slack",
  // income_types (common)
  self_employment_income: "Self-employment income",
  rental_property_income: "Rental property income",
  limited_company_income: "Limited company income",
};

const ONBOARDING_STATUS_LABELS = {
  not_started: "Not started",
  in_progress: "In progress",
  complete: "Complete",
  complete_with_review_flags: "Complete (with items to review)",
  blocked_missing_critical_data: "Waiting on important details",
};

const FLAG_HEADLINES = {
  self_assessment_uncertain: "Self Assessment",
  ambiguous_company_match: "Company details",
  possible_vat_review: "VAT",
  reminder_setup_incomplete: "Reminders",
};

const PIPELINE_TITLES = {
  companies_house: "Companies House",
  company_formation: "Company formation",
  self_assessment: "Self Assessment",
  property_income: "Property income",
  vat: "VAT",
  payroll: "Payroll",
  mtd_income_tax: "Making Tax Digital (Income Tax)",
  reminders: "Reminders",
};

/** Short client-friendly line under each pipeline card (when active) */
const PIPELINE_HELP = {
  companies_house:
    "We’ll use your verified company record for filing dates and official details where relevant.",
  company_formation:
    "Guidance and reminders if you’re forming or registering a new company.",
  self_assessment:
    "Supports Self Assessment timing and record-keeping nudges based on what you told us.",
  property_income:
    "Rental and property income workflows when that applies to your situation.",
  vat:
    "VAT registration, returns, and threshold awareness aligned with your answers.",
  payroll:
    "Payroll and PAYE-related prompts when you run payroll—for example paying directors or staff through PAYE.",
  mtd_income_tax:
    "Making Tax Digital for Income Tax (MTD ITSA): HMRC’s rules for digital records and periodic updates when you’re in scope—so you’re not caught out at filing time.",
  reminders:
    "Friendly nudges in your chosen channel so important dates are easier to keep track of.",
};

/** When a workflow is off or waiting—plain-English context */
const PIPELINE_HELP_IDLE = {
  companies_house: "Usually activates once a limited company is verified with Companies House.",
  company_formation: "Relevant when you’re still setting up a new company.",
  payroll: "Turns on when payroll or director PAYE applies to you.",
  mtd_income_tax: "HMRC will bring more sole traders and landlords into MTD over time—we’ll align prompts when it applies.",
  vat: "Can switch on if you register for VAT or your situation changes.",
};

function humanizeKey(snake) {
  if (!snake) return "";
  const k = String(snake).trim();
  if (FIELD_LABELS[k]) return FIELD_LABELS[k];
  return k
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

function humanizeToken(raw) {
  const v = String(raw).trim().toLowerCase();
  if (!v) return "";
  if (VALUE_LABELS[v]) return VALUE_LABELS[v];
  if (VALUE_LABELS[String(raw).trim()]) return VALUE_LABELS[String(raw).trim()];
  return humanizeKey(v);
}

function formatFieldValue(f) {
  if (f.value_json != null) {
    if (Array.isArray(f.value_json)) {
      return f.value_json.map((x) => humanizeToken(x)).filter(Boolean).join(", ") || "—";
    }
    if (typeof f.value_json === "object") {
      return JSON.stringify(f.value_json);
    }
    return humanizeToken(f.value_json);
  }
  if (f.value_text != null && String(f.value_text).trim() !== "") {
    const t = String(f.value_text).trim();
    if (t.includes(",")) {
      return t
        .split(",")
        .map((s) => humanizeToken(s.trim()))
        .filter(Boolean)
        .join(", ");
    }
    return humanizeToken(t);
  }
  return "—";
}

function formatFieldLine(f) {
  const title = humanizeKey(f.field_name);
  const val = formatFieldValue(f);
  return `${title}: ${val}`;
}

function section(title, node) {
  const s = document.createElement("section");
  s.className = "surface surface-pad";
  const h = document.createElement("h2");
  h.className = "form-section-title";
  h.textContent = title;
  s.appendChild(h);
  s.appendChild(node);
  return s;
}

function listFromLabels(items, empty) {
  const ul = document.createElement("ul");
  ul.className = "summary-list";
  ul.style.margin = "0";
  ul.style.paddingLeft = "1.2rem";
  if (!items.length) {
    const li = document.createElement("li");
    li.style.color = "var(--color-muted)";
    li.textContent = empty;
    ul.appendChild(li);
    return ul;
  }
  for (const t of items) {
    const li = document.createElement("li");
    li.textContent = t;
    ul.appendChild(li);
  }
  return ul;
}

try {
  const r = await fetch(apiUrl(`/v1/onboarding/${encodeURIComponent(uid)}/state`), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(await r.text());

  const st = await r.json();
  const canEnter = APP_ACCESS_STATUSES.has(me.onboarding.status);

  if (!canEnter) {
    incomplete.classList.remove("hidden");
    const statusLabel =
      ONBOARDING_STATUS_LABELS[me.onboarding.status] || me.onboarding.status.replace(/_/g, " ");
    document.getElementById("subhead").textContent =
      `${statusLabel} — you’re about ${me.onboarding.completion_percent}% through. Finish setup to open your workspace.`;
    root.classList.add("hidden");
    cta.classList.add("hidden");
  } else {
    incomplete.classList.add("hidden");
    root.classList.remove("hidden");

    const flags = st.review_flags || [];
    const openFlags = flags.filter((f) => !f.resolved);
    const verified = [];
    const userProvided = [];
    const review = [];

    for (const rf of openFlags) {
      const headline = FLAG_HEADLINES[rf.flag_type] || humanizeKey(rf.flag_type);
      review.push(`${headline}: ${rf.message}`);
    }

    for (const f of st.fields || []) {
      const vs = (f.verification_status || "unverified").toLowerCase();
      const line = formatFieldLine(f);
      if (vs === "verified" || vs === "system_verified") {
        verified.push(`${line} (Verified)`);
      } else {
        userProvided.push(line);
      }
    }

    const cl = st.company_link;
    if (cl?.companies_house_verified) {
      const cn = cl.matched_company_name || "";
      const num = cl.matched_company_number || "";
      verified.push(`Companies House verified: ${cn}${num ? ` · ${num}` : ""}`);
    }

    root.appendChild(
      section("What we’ve verified", listFromLabels(verified, "Nothing verified yet — official checks will appear here when available.")),
    );
    root.appendChild(section("What you told us", listFromLabels(userProvided, "No saved answers in this section.")));
    root.appendChild(
      section(
        "Worth a quick look",
        listFromLabels(
          review,
          openFlags.length
            ? ""
            : "No open items — we’ll flag anything important in the workspace if it comes up.",
        ),
      ),
    );

    const pipeBox = document.createElement("div");
    pipeBox.className = "pipeline-board";
    for (const p of st.pipelines || []) {
      const pill = document.createElement("div");
      pill.className = "pipeline-pill";
      const title = PIPELINE_TITLES[p.pipeline_name] || humanizeKey(p.pipeline_name);
      const strong = document.createElement("strong");
      strong.textContent = title;
      pill.appendChild(strong);
      const sub = document.createElement("div");
      sub.className = "pipeline-pill-status";
      sub.style.marginTop = "0.25rem";
      sub.style.fontSize = "0.8rem";
      sub.style.color = "var(--color-muted)";
      const state = p.enabled ? "On" : "Off";
      const statusNice = String(p.status || "").replace(/_/g, " ");
      sub.textContent = `${state}${statusNice ? ` · ${statusNice}` : ""}`;
      pill.appendChild(sub);
      const desc = document.createElement("p");
      desc.className = "pipeline-pill-desc";
      if (p.enabled) {
        desc.textContent = PIPELINE_HELP[p.pipeline_name] || "";
      } else {
        desc.textContent =
          PIPELINE_HELP_IDLE[p.pipeline_name] || "Not active for your current answers—you can update setup if this should apply.";
      }
      if (desc.textContent) pill.appendChild(desc);
    }
    if (!st.pipelines?.length) {
      const p = document.createElement("p");
      p.className = "empty-panel";
      p.textContent = "Workflows will appear here after routing runs.";
      pipeBox.appendChild(p);
    }
    root.appendChild(section("Active workflows", pipeBox));

    const notesWrap = document.createElement("div");
    notesWrap.className = "setup-summary-notes";
    const p1 = document.createElement("p");
    p1.textContent = "Your workspace is ready.";
    const p2 = document.createElement("p");
    p2.textContent =
      "We’ve activated the relevant workflows based on your setup, so you can focus on your business instead of guessing what applies to you.";
    const p3 = document.createElement("p");
    p3.textContent =
      "You can update these details later if anything changes—use Edit onboarding whenever you need to.";
    notesWrap.appendChild(p1);
    notesWrap.appendChild(p2);
    notesWrap.appendChild(p3);
    if (me.onboarding.status === "complete_with_review_flags" && openFlags.length) {
      const p4 = document.createElement("p");
      p4.className = "setup-summary-notes-aside";
      p4.textContent =
        "There are a few items above you may want to double-check when convenient—they won’t stop you opening the workspace.";
      notesWrap.appendChild(p4);
    }

    root.appendChild(section("Before you go", notesWrap));

    cta.classList.remove("hidden");
  }
} catch (e) {
  banner.textContent = e.message || String(e);
  banner.classList.remove("hidden");
}
