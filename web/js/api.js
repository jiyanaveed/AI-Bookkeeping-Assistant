import { API_BASE } from "./runtime-config.js";

/** Absolute or same-origin URL for API paths (must start with `/`). */
export function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  const base = String(API_BASE || "").replace(/\/$/, "");
  return `${base}${p}`;
}

function authHeaders(extra = {}) {
  const t = localStorage.getItem("auth_token");
  const h = { ...extra };
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

export function getJson(path, params = {}) {
  const q = new URLSearchParams(params);
  const url = q.toString() ? `${apiUrl(path)}?${q}` : apiUrl(path);
  return fetch(url, { headers: authHeaders() }).then(async (r) => {
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  });
}

export function postJson(path, body) {
  return fetch(apiUrl(path), {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  }).then(async (r) => {
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  });
}

export function patchJson(path, params, body) {
  const q = new URLSearchParams(params);
  return fetch(`${apiUrl(path)}?${q}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  }).then(async (r) => {
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  });
}

export function postEmpty(path, params) {
  const q = new URLSearchParams(params);
  return fetch(`${apiUrl(path)}?${q}`, { method: "POST", headers: authHeaders() }).then(async (r) => {
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  });
}

export async function uploadFiles(userId, fileList) {
  const fd = new FormData();
  fd.append("user_id", userId);
  for (const f of fileList) fd.append("files", f);
  const r = await fetch(apiUrl("/v1/uploads"), { method: "POST", headers: authHeaders(), body: fd });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export function fileUrl(fileId, userId) {
  return `${apiUrl("/v1/files")}/${encodeURIComponent(fileId)}/content?user_id=${encodeURIComponent(userId)}`;
}
