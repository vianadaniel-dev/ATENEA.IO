export function navbar() {
    return`
     <header id="navbar">
        <div class="header__user">
            <div class="header__balance">
                <div class="header__balance-icon">
                    <img src="../src/assets/images/coin.svg" alt="">
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
                        src="../src/assets/images/perfil.svg"
                        alt="Foto de perfil"
                        id="header-profile-avatar"
                    >
                </div>
                <a
                    href="#"
                    class="header__profile-name user_name"
                    id="header-profile-name"> nombre usuario
                </a>
            </div>
        </div>
    </header>

    `
};