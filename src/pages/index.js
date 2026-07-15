/**
 * Atenea.io — Login / Authentication
 * persists the session ("Remember me") and redirects to the dashboard.
 */

"use strict";

const STORAGE_KEY = "atenea.session";
const REDIRECT_URL = "...\frontend\pages\Home\home.html";
const REDIRECT_DELAY = 1800;
const TOAST_DURATION = 3000; 


const ACCOUNTS = {
  "profesor@test.com": { password: "test123", role: "teacher", message: "Successful access" },
  "student@test.com": { password: "test123", role: "student", message: "Welcome student, check your progress" },
};

const form = document.getElementById("login-form");
const emailInput = document.getElementById("login-username");
const passwordInput = document.getElementById("login-password");
const rememberInput = document.getElementById("login-remember");

const showToast = (message, type = "success") => {
  const toast = document.createElement("div");
  toast.className = `toast toast--${type}`;
  toast.setAttribute("role", "status");
  toast.textContent = message;
  document.body.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add("toast--visible"));

  setTimeout(() => {
    toast.classList.remove("toast--visible");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
  }, TOAST_DURATION);
};

const saveSession = (email, role) =>
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ email, role, remember: true }));

const restoreSession = () => {
  const session = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
  if (!session?.remember) return;
  emailInput.value = session.email;
  rememberInput.checked = true;
};

const handleSubmit = (event) => {
  event.preventDefault();

  const email = emailInput.value.trim().toLowerCase();
  const account = ACCOUNTS[email];

  if (!account || passwordInput.value !== account.password) {
    return showToast("Invalid credentials", "error");
  }

  rememberInput.checked ? saveSession(email, account.role) : localStorage.removeItem(STORAGE_KEY);
  showToast(account.message);
  setTimeout(() => (window.location.href = REDIRECT_URL), REDIRECT_DELAY);
};
restoreSession();
form.addEventListener("submit", handleSubmit);
