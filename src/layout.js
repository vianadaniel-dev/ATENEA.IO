
document.getElementById("main-sidebar").classList.add('closed');
document.getElementById("sidebar-toggle-container").classList.add('closed');
document.getElementById("sidebar-title-container").classList.add('closed');
document.querySelectorAll(".sidebar__link-wrapper").forEach(element => {
    element.classList.add('closed');
})
document.querySelectorAll(".sidebar__text").forEach(element => {
    element.classList.add('closed');
})
document.getElementById("sidebar-btn-logout-text").classList.add('closed');

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

}