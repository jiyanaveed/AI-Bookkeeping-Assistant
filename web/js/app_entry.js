import { requireAppAccess, logoutApi } from "./gate.js";

const me = await requireAppAccess();
if (!me) {
  throw new Error("gate");
}

const uidField = document.getElementById("user-id");
if (uidField) uidField.value = me.user_id;

const ad = document.getElementById("auth-display");
if (ad) ad.textContent = me.email || `${me.user_id.slice(0, 8)}…`;

const wsText = document.getElementById("workspace-context-text");
if (wsText && me.workspace?.display_line) {
  wsText.textContent = me.workspace.display_line;
}

document.getElementById("btn-logout")?.addEventListener("click", async () => {
  await logoutApi();
  window.location.href = "/internal/login.html";
});

await import("./main.js");
