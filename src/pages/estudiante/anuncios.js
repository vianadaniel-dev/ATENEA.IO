import { estudianteSidebar } from "../../partials/sidebar-estudiante.js";
const sidebarContainer = document.getElementById("sidebar");
if (sidebarContainer) {
    sidebarContainer.innerHTML = estudianteSidebar();
}