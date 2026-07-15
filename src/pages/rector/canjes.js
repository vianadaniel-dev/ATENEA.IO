import { sidebarRector } from "../../partials/sidebar-rector.js";
const sidebarContainer = document.getElementById("sidebar");
if (sidebarContainer) {
    sidebarContainer.innerHTML = sidebarRector();
}