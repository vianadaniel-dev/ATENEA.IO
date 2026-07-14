const userPreferences = {
    id: 15,
    name: "José Ramírez",
    role: "student",
    theme: "dark",
    sidebar: "closed",
    language: "es",
    lastPage: "/subjects",
    notifications: true
};

localStorage.setItem(
    "userPreferences",
    JSON.stringify(userPreferences)
);

/*==================================================
=                  ICONOS DEL TEMA                 =
==================================================*/

const lightIcon = `
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 24 24" transform="scale(-1,1)">
    <path d="M12 17.01c2.76 0 5.01-2.25 5.01-5.01S14.76 6.99 12 6.99 6.99 9.24 6.99 12s2.25 5.01 5.01 5.01M12 9c1.66 0 3.01 1.35 3.01 3.01s-1.35 3.01-3.01 3.01-3.01-1.35-3.01-3.01S10.34 9 12 9m1 10h-2v3h2zm0-17h-2v3h2zM2 11h3v2H2zm17 0h3v2h-3zM4.22 18.36l.71.71.71.71 1.06-1.06 1.06-1.06-.71-.71-.71-.71-1.06 1.06M19.78 5.64l-.71-.71-.71-.71-1.06 1.06-1.06 1.06.71.71.71.71 1.06-1.06zm-12.02.7L6.7 5.28 5.64 4.22l-.71.71-.71.71L5.28 6.7l1.06 1.06.71-.71zm8.48 11.32 1.06 1.06 1.06 1.06.71-.71.71-.71-1.06-1.06-1.06-1.06-.71.71"></path>
</svg>`;

const darkIcon = `
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12.2 22c4.53 0 8.45-2.91 9.76-7.24a1.002 1.002 0 0 0-1.25-1.25c-.78.23-1.58.35-2.38.35-4.52 0-8.2-3.68-8.2-8.2 0-.8.12-1.6.35-2.38.11-.35.01-.74-.25-1s-.64-.36-1-.25A10.17 10.17 0 0 0 2 11.8C2 17.42 6.57 22 12.2 22M8.18 4.65c-.03.34-.05.68-.05 1.02 0 5.62 4.57 10.2 10.2 10.2.34 0 .68-.02 1.02-.05C17.93 18.38 15.23 20 12.2 20 7.68 20 4 16.32 4 11.8a8.15 8.15 0 0 1 4.18-7.15"></path>
</svg>`;


/*==================================================
=              REFERENCIAS DEL DOM                =
==================================================*/

const BtnTtheme = document.getElementById("sidebar-btn-theme");
const rootHtml = document.documentElement;


/*==================================================
=           CONFIGURACIÓN DEL USUARIO             =
==================================================*/

const user = JSON.parse(localStorage.getItem("userPreferences"));
let theme = user.theme;


/*==================================================
=      CARGAR EL TEMA AL INICIAR LA PÁGINA        =
==================================================*/

document.addEventListener("DOMContentLoaded", () => {

    // Si el tema guardado es oscuro
    if (theme === "dark") {

        BtnTtheme.innerHTML = lightIcon;
        rootHtml.setAttribute("data-theme", "dark");

    } else {

        BtnTtheme.innerHTML = darkIcon;

    }

});


/*==================================================
=          CAMBIAR ENTRE MODO CLARO Y OSCURO      =
==================================================*/

BtnTtheme.addEventListener("click", () => {

    // Cambiar de claro a oscuro
    if (theme === "light") {

        BtnTtheme.innerHTML = lightIcon;
        rootHtml.setAttribute("data-theme", "dark");

        user.theme = "dark";
        theme = "dark";

        localStorage.setItem(
            "userPreferences",
            JSON.stringify(user)
        );

    }
    // Cambiar de oscuro a claro
    else {

        BtnTtheme.innerHTML = darkIcon;
        rootHtml.removeAttribute("data-theme");

        user.theme = "light";
        theme = "light";

        localStorage.setItem(
            "userPreferences",
            JSON.stringify(user)
        );

    }

});

const userName = document.querySelectorAll(".user_name");
const userRol = document.querySelectorAll(".user_rol");

document.addEventListener("DOMContentLoaded", () => {

    const user = JSON.parse(localStorage.getItem("userPreferences"));

    userRol.forEach(date => {
        date.textContent = user.role
    });
    userName.forEach(date => {
        date.textContent = user.name
    });
});

const sidebar_toggle_container = document.getElementById("sidebar-toggle-container");

sidebar_toggle_container.addEventListener('click', () => {
    document.getElementById("main-sidebar").classList.toggle('closed');

    document.getElementById("sidebar-toggle-container").classList.toggle('closed');
    document.getElementById("sidebar-toggle-icon").classList.toggle('closed');

    document.getElementById("sidebar-title-container").classList.toggle('closed');

    document.querySelectorAll(".sidebar__link-wrapper").forEach(element => {
        element.classList.toggle('closed');
    })
    document.querySelectorAll(".sidebar__text").forEach(element => {
        element.classList.toggle('closed');
    })

    document.getElementById("sidebar-btn-logout-text").classList.toggle('closed');
})