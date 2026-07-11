from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db, get_cursor
from app.schemas import LoginRequest, Token, UsuarioResponse
from app.auth_utils import verify_password, create_access_token, get_current_usuario

router = APIRouter()

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        # 1. Search user by email
        cur.execute(
            "SELECT id, email, password_hash, nombre, rol FROM usuario WHERE email = %s",
            (login_data.email,)
        )
        usuario = cur.fetchone()
        
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    # 2. Verify password
    if not verify_password(login_data.password, usuario["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    # 3. Create access token
    access_token = create_access_token(data={"sub": usuario["email"], "rol": usuario["rol"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "rol": usuario["rol"],
        "nombre": usuario["nombre"]
    }

@router.get("/me", response_model=UsuarioResponse)
def get_me(current_user: dict = Depends(get_current_usuario)):
    return current_user
