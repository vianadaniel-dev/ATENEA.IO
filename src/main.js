import "./styles/main.scss";
import { navbar } from "../partials/navbar.js";
initSidebar();
const sidebarContainer = document.getElementById("header");
if (sidebarContainer) {
    sidebarContainer.innerHTML = navbar();
}
