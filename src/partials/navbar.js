export function navbar() {
    return`
     <header id="header">
        <div class="header__title">
            <span class="header-page-title">
                <a href="">
                    Home
                </a>
            </span>
            <span>></span>
            <span class="header-page-title location">
                Home
            </span>
        </div>

        <div class="header__user">
            <div class="header__balance">
                <div class="header__balance-icon">
                    <img src="../../assents/Imagenes/Coin.svg" alt="">
                </div>

                <span
                    class="header__balance-value"
                    id="header-balance-value">
                    000
                </span>
            </div>

            <div class="header__profile">
                <div class="header__profile-image">
                    <img
                        src="../../assents/Imagenes/Group 55 (1).svg"
                        alt="Foto de perfil"
                        id="header-profile-avatar"
                    >
                </div>
                <a
                    href="#"
                    class="header__profile-name user_name"
                    id="header-profile-name">
                </a>
            </div>
        </div>
    </header>

    `
};