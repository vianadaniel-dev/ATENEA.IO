export function initSidebar() {

    const sidebar = document.getElementById("main-sidebar");
    const toggle = document.getElementById("sidebar-toggle-container");
    const title = document.getElementById("sidebar-title-container");
    const logoutText = document.getElementById("sidebar-btn-logout-text");

    // Si la página no tiene sidebar (ej. login), salir sin hacer nada
    if (!sidebar || !toggle || !title || !logoutText) {
        return;
    }

    sidebar.classList.add("closed");
    toggle.classList.add("closed");
    title.classList.add("closed");
    logoutText.classList.add("closed");

    document.querySelectorAll(".sidebar__link-wrapper")
        .forEach(el => el.classList.add("closed"));

    document.querySelectorAll(".sidebar__text")
        .forEach(el => el.classList.add("closed"));

    toggle.addEventListener("click", () => {

        sidebar.classList.toggle("closed");
        toggle.classList.toggle("closed");
        title.classList.toggle("closed");
        logoutText.classList.toggle("closed");

        document.querySelectorAll(".sidebar__link-wrapper")
            .forEach(el => el.classList.toggle("closed"));

        document.querySelectorAll(".sidebar__text")
            .forEach(el => el.classList.toggle("closed"));
    });
}
