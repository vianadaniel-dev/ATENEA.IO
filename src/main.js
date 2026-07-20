import "./styles/main.scss";
import { navbar } from "../partials/navbar.js";
initSidebar();

import { navbar } from "../src/partials/navbar.js";
const sidebarContainer = document.getElementById("header");
if (sidebarContainer) {
    sidebarContainer.innerHTML = navbar();
}
