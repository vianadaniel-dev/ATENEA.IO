"use strict"; // Activa el modo estricto para evitar errores comunes en JavaScript.

// ==========================
// CONFIGURACIÓN GENERAL
// ==========================

// Clave utilizada para guardar la sesión en el localStorage.
const STORAGE_KEY = "atenea.session";

// Ruta a la página principal después del inicio de sesión.
const REDIRECT_ROUTES = {
  teacher: "profesor/dashboard.html",
  student: "estudiante/dashboard.html",
  admin: "rector/dashboard.html"
};

// Tiempo de espera antes de redirigir (en milisegundos).
const REDIRECT_DELAY = 1800;

// Tiempo que permanece visible la notificación (toast).
const TOAST_DURATION = 3000;


// ==========================
// USUARIOS SIMULADOS
// ==========================
// Base de datos temporal para pruebas.

const ACCOUNTS = {
  "profesor@test.com": {
    password: "test123",
    role: "teacher",
    message: "Successful access"
  },

  "student@test.com": {
    password: "test123",
    role: "student",
    message: "Welcome student, check your progress"
  },

  "admin@test.com": {
    password: "test123",
    role: "admin",
    message: "Successful access"
  },
};


// ==========================
// ELEMENTOS DEL DOM
// ==========================

// Formulario de inicio de sesión.
const form = document.getElementById("login-form");

// Campo del correo electrónico.
const emailInput = document.getElementById("login-username");

// Campo de la contraseña.
const passwordInput = document.getElementById("login-password");

// Checkbox "Recordarme".
const rememberInput = document.getElementById("login-remember");


// ==========================
// MOSTRAR NOTIFICACIONES
// ==========================
// Crea un mensaje flotante indicando éxito o error.

const showToast = (message, type = "success") => {

  // Crear el elemento.
  const toast = document.querySelector("mensaje_error");

  // Asignar clases CSS.
  toast.className = `toast toast--${type}`;

  // Accesibilidad.
  toast.setAttribute("role", "status");

  // Texto del mensaje.
  toast.innerHTML = `<i class="bx bx-info-octagon"></i><span>${message}</span>`;

  // Agregar al documento.
  document.body.appendChild(toast);

  // Mostrar con animación.
  requestAnimationFrame(() =>
    toast.classList.add("toast--visible")
  );

  // Ocultar después de unos segundos.
  setTimeout(() => {

    toast.classList.remove("toast--visible");

    // Eliminar cuando termine la animación.
    toast.addEventListener(
      "transitionend",
      () => toast.remove(),
      { once: true }
    );

  }, TOAST_DURATION);

};


// ==========================
// GUARDAR SESIÓN
// ==========================
// Guarda los datos del usuario en localStorage.

const saveSession = (email, role) =>

  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      email,
      role,
      remember: true
    })
  );


// ==========================
// RESTAURAR SESIÓN
// ==========================
// Recupera la sesión si el usuario marcó "Recordarme".

const restoreSession = () => {

  // Leer información almacenada.
  const session = JSON.parse(
    localStorage.getItem(STORAGE_KEY) || "null"
  );

  // Si no existe una sesión válida, terminar.
  if (!session?.remember) return;

  // Restaurar correo.
  emailInput.value = session.email;

  // Marcar el checkbox.
  rememberInput.checked = true;

};


// ==========================
// VALIDAR EL LOGIN
// ==========================
// Se ejecuta cuando el usuario envía el formulario.

const handleSubmit = (event) => {

  // Evita que el formulario recargue la página.
  event.preventDefault();

  // Obtener el correo.
  const email = emailInput.value
    .trim()
    .toLowerCase();

  // Buscar el usuario.
  const account = ACCOUNTS[email];

  // Validar usuario y contraseña.
  if (!account || passwordInput.value !== account.password) {

    return showToast(
      "Invalid credentials",
      "error"
    );

  }

  // Guardar sesión si el usuario lo solicitó.
  rememberInput.checked
    ? saveSession(email, account.role)
    : localStorage.removeItem(STORAGE_KEY);

  // Mostrar mensaje de éxito.
  showToast(account.message);

  // Redirigir después del tiempo configurado.
  setTimeout(() => {

    window.location.href = REDIRECT_ROUTES[account.role];

  }, REDIRECT_DELAY);

};


// ==========================
// INICIALIZACIÓN
// ==========================

// Restaurar sesión guardada.
restoreSession();

// Escuchar el envío del formulario.
form.addEventListener("submit", handleSubmit);