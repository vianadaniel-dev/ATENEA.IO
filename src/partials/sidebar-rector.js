export function sidebarRector() {
    return `<nav id="main-sidebar" class="sidebar">
        <!-- Bloque Superior: Logo, Título y Botón de colapso -->
        <div id="sidebar-header" class="sidebar__header">
            <div class="sidebar__header-absolut">
                <div id="sidebar-logo-container" class="sidebar__logo-container">
                    <svg viewBox="0 0 122 175" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                        <path d="M0.219531 115.642C-0.150545 116.366 -0.0462272 117.241 0.483479 117.857L48.2629 173.43C49.4814 174.848 51.8051 173.968 51.7793 172.099L51.3593 141.727C51.3523 141.226 51.1577 140.746 50.8138 140.382L32.7075 121.202C31.5033 119.926 32.4077 117.829 34.1619 117.829H87.0533C88.8075 117.829 89.7119 119.926 88.5077 121.202L70.4014 140.382C70.0575 140.746 69.8629 141.226 69.8559 141.727L69.4359 172.099C69.4101 173.968 71.7338 174.848 72.9523 173.43L120.732 117.857C121.261 117.241 121.366 116.366 120.996 115.642L62.3881 1.08906C61.6452 -0.363018 59.57 -0.363026 58.8271 1.08906L0.219531 115.642ZM84.3135 94.7963C84.9703 96.1256 84.0031 97.6823 82.5204 97.6823H38.6948C37.2121 97.6823 36.2449 96.1256 36.9017 94.7963L58.8145 50.4487C59.5485 48.9634 61.6667 48.9634 62.4007 50.4487L84.3135 94.7963Z"/>
                    </svg>
                </div>
                <div id="sidebar-title-container" class="sidebar__title-container">
                    <span id="sidebar-title" class="sidebar__title">Name of the institution</span>
                    <span id="sidebar-subtitle" class="sidebar__subtitle">student: Name</span>
                </div>
            </div>
            <div id="sidebar-toggle-container" class="sidebar__toggle-container">
                <i class="bx bx-caret-left"></i>
            </div>
        </div>

        <!-- Bloque Central: Opciones del menú/slider bar -->
        <div id="sidebar-menu-container" class="sidebar__menu-container">
            <ul id="sidebar-menu-list" class="sidebar__menu-list">
                <a href="/rector/dashboard.html">
                    <li class="sidebar__menu-item">
                        <div class="sidebar__link-wrapper">
                            <i class="bx bx-grid-alt"></i>
                            <span class="sidebar__text">dashboard</span>
                        </div>
                        <div class="sidebar__link-wrapper-li"></div>
                    </li>
                </a>
                <a href="/rector/cursos.html">
                    <li class="sidebar__menu-item">
                        <div class="sidebar__link-wrapper">
                            <i class="bx bx-book-open"></i>
                            <span class="sidebar__text">courses</span>
                        </div>
                        <div class="sidebar__link-wrapper-li"></div>
                    </li>
                </a>
                <a href="/rector/estudiantes.html">
                    <li class="sidebar__menu-item">
                        <div class="sidebar__link-wrapper">
                            <i class="bx bx-user"></i>
                            <span class="sidebar__text">students</span>
                        </div>
                        <div class="sidebar__link-wrapper-li"></div>
                    </li>
                </a>
                <a href="/rector/profesores.html">
                    <li class="sidebar__menu-item">
                        <div class="sidebar__link-wrapper">
                            <i class="bx bx-chalkboard"></i>
                            <span class="sidebar__text">teachers</span>
                        </div>
                        <div class="sidebar__link-wrapper-li"></div>
                    </li>
                </a>
                <a href="/rector/anuncios.html">
                    <li class="sidebar__menu-item">
                        <div class="sidebar__link-wrapper">
                            <i class="bx bx-news"></i>
                            <span class="sidebar__text">announcements</span>
                        </div>
                        <div class="sidebar__link-wrapper-li"></div>
                    </li>
                </a>
                <a href="/rector/auditoria.html">
                    <li class="sidebar__menu-item">
                        <div class="sidebar__link-wrapper">
                            <i class="bx bx-history"></i>
                            <span class="sidebar__text">audit log</span>
                        </div>
                        <div class="sidebar__link-wrapper-li"></div>
                    </li>
                </a>
                <a href="/rector/canjes.html">
                    <li class="sidebar__menu-item">
                        <div class="sidebar__link-wrapper">
                            <i class="bx bx-gift"></i>
                            <span class="sidebar__text">reward claims</span>
                        </div>
                        <div class="sidebar__link-wrapper-li"></div>
                    </li>
                </a>
                <a href="/rector/perfil.html">
                    <li class="sidebar__menu-item">
                        <div class="sidebar__link-wrapper">
                            <i class="bx bx-user-circle"></i>
                            <span class="sidebar__text">profile</span>
                        </div>
                        <div class="sidebar__link-wrapper-li"></div>
                    </li>
                </a>
            </ul>
        </div>

        <!-- Bloque Inferior: Cambio de modo y Salida -->
        <div id="sidebar-footer" class="sidebar__footer">
            <div id="button-theme" class="theme-toggle">
                <div class="theme-toggle__icons">
                    <span id="sun_icon" class="theme-toggle__icon">
                        <i class="bx bx-sun"></i>
                    </span>

                    <span id="moon_icon" class="theme-toggle__icon">
                        <i class="bx bx-moon"></i>
                    </span>
                </div>
                <div id="theme-toggle__slider"></div>
            </div>            
            <button id="sidebar-btn-logout" class="sidebar__button sidebar__button--logout" type="button">
                <i class="bx bx-arrow-out-right-square-half"></i>
                <span id="sidebar-btn-logout-text">Exit</span>
            </button>
        </div>
    </nav> 
    <script type="module" src="../main.js"></script>
</body>
</html>`;
}