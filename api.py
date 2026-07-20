"""Punto de entrada de la aplicación FastAPI.

Inicializa la aplicación, carga la configuración, establece el pool de conexiones,
e incluye los routers de la API.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr

import database
import routes
from auth import create_access_token, verify_password
import crud
from database import get_cursor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación."""
    # Startup
    database.init_pool()
    yield
    # Shutdown
    database.close_pool()


app = FastAPI(lifespan=lifespan)


# ============================ ENDPOINTS BASICOS ============================

@app.get("/", tags=["Info"])
def read_root():
    """Endpoint de bienvenida."""
    return {"message": "Bienvenido a la API de Atenea.io"}


# ============================ AUTENTICACION ============================

class LoginRequest(BaseModel):
    """Esquema de solicitud de login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Esquema de respuesta de token."""
    access_token: str
    token_type: str
    rol: str
    nombre: str


@app.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK, tags=["Auth"])
def login(datos: LoginRequest, conn=Depends(database.get_db)):
    """Autentica un usuario con email y contraseña, retorna un JWT."""
    with get_cursor(conn) as cur:
        usuario = crud.select_usuario_by_email(cur, datos.email)

    if not usuario or not verify_password(datos.password, usuario["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    access_token = create_access_token(
        data={
            "sub": usuario["email"],
            "rol": usuario["rol"],
            "usuario_id": usuario["id"]
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "rol": usuario["rol"],
        "nombre": usuario["nombre"]
    }


# ============================ ROUTERS ============================

app.include_router(routes.router)
