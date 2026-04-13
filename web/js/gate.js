/**
 * v1 demo auth + onboarding gates. Replace with OAuth/session cookies for production.
 */

import { apiUrl } from "./api.js";

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user_id";
const EMAIL_KEY = "auth_email";

export const APP_ACCESS_STATUSES = new Set(["complete", "complete_with_review_flags"]);

export function setSession(res) {
  localStorage.setItem(TOKEN_KEY, res.access_token);
  localStorage.setItem(USER_KEY, res.user_id);
  if (res.email) localStorage.setItem(EMAIL_KEY, res.email);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(EMAIL_KEY);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export async function fetchMe() {
  const t = getToken();
  if (!t) return null;
  const r = await fetch(apiUrl("/v1/auth/me"), { headers: { Authorization: `Bearer ${t}` } });
  if (!r.ok) {
    clearSession();
    return null;
  }
  return r.json();
}

/** @returns {object|null} null when redirecting to login */
export async function requireAuth(redirectTo = "/internal/login.html") {
  const me = await fetchMe();
  if (!me) {
    window.location.href = redirectTo;
    return null;
  }
  return me;
}

/** Main product: null when redirecting (login or onboarding). */
export async function requireAppAccess() {
  const me = await requireAuth();
  if (!me) return null;
  if (!APP_ACCESS_STATUSES.has(me.onboarding.status)) {
    window.location.replace("/internal/onboarding.html");
    return null;
  }
  return me;
}

/**
 * Dev/testing: `?force=1` on the onboarding URL skips redirecting completed users to the app.
 * Standard visits still send complete profiles to app.html (requireAppAccess unchanged).
 */
function onboardingDevForceEdit() {
  try {
    return new URLSearchParams(window.location.search).get("force") === "1";
  } catch {
    return false;
  }
}

/** Onboarding shell: null when redirecting (login or already allowed into app). */
export async function bootOnboardingShell() {
  const me = await requireAuth();
  if (!me) return null;
  if (!onboardingDevForceEdit() && APP_ACCESS_STATUSES.has(me.onboarding.status)) {
    window.location.replace("/internal/app.html");
    return null;
  }
  return me;
}

export async function requireAuthForSummary() {
  return requireAuth();
}

export async function logoutApi() {
  const t = getToken();
  if (t) {
    await fetch(apiUrl("/v1/auth/logout"), {
      method: "POST",
      headers: { Authorization: `Bearer ${t}` },
    }).catch(() => {});
  }
  clearSession();
}
