import "./styles/main.scss";
import { initSidebar } from "./layout.js";
initSidebar();

import { navbar } from "../src/partials/navbar.js";
const sidebarContainer = document.getElementById("header");
if (sidebarContainer) {
    sidebarContainer.innerHTML = navbar();
}
