
const STORAGE_KEY = "atenea.session";

const REDIRECT_ROUTES = {
  teacher: "/profesor/dashboard",
  student: "/estudiante/dashboard",
  admin: "/rector/dashboard"
};

const REDIRECT_DELAY = 1800;
const TOAST_DURATION = 3000;

const ACCOUNTS = {
  "profesor@test.com": {
    password: "test123",
    role: "teacher",
    message: "Acceso exitoso"
  },
  "student@test.com": {
    password: "test123",
    role: "student",
    message: "Bienvenido estudiante, revisa tu progreso"
  },
  "admin@test.com": {
    password: "test123",
    role: "admin",
    message: "Acceso exitoso"
  },
};

// ==========================
// ELEMENTOS DEL DOM
// ==========================

const form = document.getElementById("login-form");
const emailInput = document.getElementById("login-username");
const passwordInput = document.getElementById("login-password");
const roleSelect = document.getElementById("login-role");      // 🆕 Ahora sí se usa
const rememberInput = document.getElementById("login-remember");

// ==========================
// TOAST (CORREGIDO)
// ==========================

const showToast = (message, type = "success") => {
  // Eliminar toast anterior si existe
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  // Crear elemento desde cero
  const toast = document.createElement("div");
  toast.className = `toast toast--${type}`;
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");
  
  const icon = type === "success" ? "bx-check-circle" : "bx-x-circle";
  toast.innerHTML = `<i class="bx ${icon}"></i><span>${message}</span>`;

  document.body.appendChild(toast);

  // Forzar reflow para que la transición funcione
  requestAnimationFrame(() => {
    toast.classList.add("toast--visible");
  });

  setTimeout(() => {
    toast.classList.remove("toast--visible");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
  }, TOAST_DURATION);
};

// ==========================
// SESIÓN
// ==========================

const saveSession = (email, role) => {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ email, role, remember: true })
  );
};

const restoreSession = () => {
  const session = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
  if (!session?.remember) return;
  
  emailInput.value = session.email;
  rememberInput.checked = true;
};

// ==========================
// LOGIN
// ==========================

const handleSubmit = (event) => {
  event.preventDefault();

  const email = emailInput.value.trim().toLowerCase();
  const password = passwordInput.value;
  const selectedRole = roleSelect.value;                          // 🆕 Leer rol seleccionado
  const account = ACCOUNTS[email];

  // Validaciones
  if (!account) {
    return showToast("Usuario no encontrado", "error");
  }

  if (password !== account.password) {
    return showToast("Contraseña incorrecta", "error");
  }

  // 🆕 Validar que el rol seleccionado coincida (opcional, pero recomendado)
  if (selectedRole && selectedRole !== account.role) {
    return showToast("Rol seleccionado no coincide con el usuario", "error");
  }

  // Guardar sesión
  if (rememberInput.checked) {
    saveSession(email, account.role);
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }

  showToast(account.message, "success");

  setTimeout(() => {
    window.location.href = REDIRECT_ROUTES[account.role];
  }, REDIRECT_DELAY);
};

// ==========================
// INICIALIZACIÓN
// ==========================

restoreSession();
form.addEventListener("submit", handleSubmit);