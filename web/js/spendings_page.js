import { requireAppAccess, logoutApi } from "./gate.js";
import * as api from "./api.js";

const me = await requireAppAccess();
if (!me) {
  throw new Error("gate");
}

const uidField = document.getElementById("user-id");
if (uidField) uidField.value = me.user_id;

const ad = document.getElementById("auth-display");
if (ad) ad.textContent = me.email || `${me.user_id.slice(0, 8)}…`;

document.getElementById("btn-logout")?.addEventListener("click", async () => {
  await logoutApi();
  window.location.href = "/internal/login.html";
});

function money(amount, currency) {
  const c = currency || "GBP";
  const n = typeof amount === "number" ? amount : parseFloat(amount);
  if (Number.isNaN(n)) return "—";
  try {
    return new Intl.NumberFormat("en-GB", { style: "currency", currency: c }).format(n);
  } catch {
    return `${n.toFixed(2)} ${c}`;
  }
}

function showBanner(msg) {
  const b = document.getElementById("banner");
  if (!b) return;
  b.textContent = msg;
  b.classList.toggle("hidden", !msg);
}

async function loadTransactions() {
  const uid = me.user_id;
  showBanner("");
  const tbody = document.getElementById("tx-body");
  const emptyEl = document.getElementById("tx-empty");
  if (tbody) tbody.innerHTML = "";

  let rows;
  try {
    rows = await api.getJson("/v1/transactions", { user_id: uid });
  } catch (e) {
    showBanner(e.message || String(e));
    return;
  }

  const total = rows.reduce((s, r) => s + (parseFloat(r.amount) || 0), 0);
  const cc = document.getElementById("tx-count");
  const tt = document.getElementById("tx-total");
  if (cc) cc.textContent = String(rows.length);
  if (tt) {
    const cur = rows[0]?.currency || "GBP";
    tt.textContent = money(total, cur);
  }

  if (!rows.length) {
    emptyEl?.classList.remove("hidden");
    return;
  }
  emptyEl?.classList.add("hidden");

  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid var(--color-border)";
    const cells = [
      r.reference_code || "—",
      r.txn_date || "—",
      money(r.amount, r.currency),
      r.description || "—",
      r.source || "—",
    ];
    for (const text of cells) {
      const td = document.createElement("td");
      td.style.padding = "0.5rem 0.65rem";
      td.textContent = text;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

document.getElementById("btn-refresh-tx")?.addEventListener("click", () => {
  void loadTransactions();
});

await loadTransactions();
