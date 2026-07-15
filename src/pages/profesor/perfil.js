import { profesorSidebar } from "../../partials/sidebar-profesor.js";
const sidebarContainer = document.getElementById("sidebar");
if (sidebarContainer) {
    sidebarContainer.innerHTML = profesorSidebar();
}