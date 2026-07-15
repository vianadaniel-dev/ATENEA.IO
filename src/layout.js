
export function initSidebar() {

    const sidebar_toggle_container = document.getElementById("sidebar-toggle-container");

    sidebar_toggle_container.addEventListener('click', () => {
        document.getElementById("main-sidebar").classList.toggle('closed');

        document.getElementById("sidebar-toggle-container").classList.toggle('closed');

        document.getElementById("sidebar-title-container").classList.toggle('closed');

        document.querySelectorAll(".sidebar__link-wrapper").forEach(element => {
            element.classList.toggle('closed');
        })
        document.querySelectorAll(".sidebar__text").forEach(element => {
            element.classList.toggle('closed');
        })

        document.getElementById("sidebar-btn-logout-text").classList.toggle('closed');
    })

    const rootHtml = document.documentElement;
    const buttonTheme = document.getElementById("button-theme");

    const btnLogout = document.getElementById("theme-toggle__slider");
    const mooIcon = document.getElementById("moon_icon");
    const sunIcon = document.getElementById("sun_icon");

    /*==================================================
    =          CAMBIAR ENTRE MODO CLARO Y OSCURO      =
    ==================================================*/

    buttonTheme.addEventListener("click", () => {

        if (theme === "light" || rootHtml.getAttribute("data-theme") == "") {

            btnLogout.classList.add("theme");
            mooIcon.classList.add("theme");
            sunIcon.classList.add("theme");

            rootHtml.setAttribute("data-theme", "dark");

            theme = "dark";
            user.theme = "dark";

        } else {

            btnLogout.classList.remove("theme");
            mooIcon.classList.remove("theme");
            sunIcon.classList.remove("theme");

            rootHtml.removeAttribute("data-theme");

            theme = "light";
            user.theme = "light";

        }

        localStorage.setItem(
            "userPreferences",
            JSON.stringify(user)
        );
    });

    /*==================================================
    =      CARGAR EL TEMA AL INICIAR LA PÁGINA        =
    ==================================================*/

    document.addEventListener("DOMContentLoaded", () => {

        // Si el tema guardado es oscuro
        if (theme === "dark" || rootHtml.getAttribute("data-theme") === "dark") {
            btnLogout.classList.add('theme')
            mooIcon.classList.add('theme')
            sunIcon.classList.add('theme')
            rootHtml.setAttribute("data-theme", "dark");
        }else{
            btnLogout.classList.remove('theme')
            mooIcon.classList.remove('theme')
            sunIcon.classList.remove('theme')
        }

    });

}