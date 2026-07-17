"""Autenticación y autorización por roles.

Proporciona:
- hash_password: hashear contraseñas con bcrypt
- get_current_usuario: obtener el usuario autenticado desde el JWT
- require_roles: validar que el usuario tenga uno de los roles requeridos
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from bcrypt import checkpw, gensalt, hashpw
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings


security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hashea una contraseña con bcrypt."""
    return hashpw(password.encode(), gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash."""
    return checkpw(password.encode(), password_hash.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un JWT con los datos proporcionados."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_usuario(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Extrae y valida el JWT del header Authorization.

    Retorna un diccionario con 'id', 'email' y 'rol' del usuario.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        rol: str = payload.get("rol")
        usuario_id: int = payload.get("usuario_id")

        if email is None or rol is None or usuario_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"id": usuario_id, "email": email, "rol": rol}


def require_roles(*allowed_roles: str):
    """Retorna una función de dependencia que valida que el usuario tenga uno de los roles.

    Uso:
        rector_required = require_roles("rector")
        staff_required = require_roles("rector", "profesor")

        @router.post("/users")
        def create_user(_=Depends(rector_required)):
            ...
    """
    def check_role(current_user: dict = Depends(get_current_usuario)) -> dict:
        if current_user["rol"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de los siguientes roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return check_role
