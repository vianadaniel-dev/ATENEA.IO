import os
from dotenv import load_dotenv

# Cargar variables desde .env si existe
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "La variable de entorno DATABASE_URL no está configurada."
    )

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "atenea_super_secret_key_change_me_in_production"
)

ALGORITHM = os.getenv(
    "ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)
