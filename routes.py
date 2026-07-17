"""Endpoints de la API.

Cada endpoint solo: recibe la peticion, llama a services.py y devuelve JSON.
No contiene logica de negocio ni consultas SQL.

Las excepciones de dominio de services.py se traducen aqui a codigos HTTP.
"""

from datetime import date
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, EmailStr, Field

import services
from auth import get_current_usuario, require_roles
from database import get_db
from services import ConflictError, NotFoundError, ServiceError, ValidationError

router = APIRouter(prefix="/api")

# En este esquema el rol administrador se llama 'rector'.
rector_required = require_roles("rector")
staff_required = require_roles("rector", "profesor")
estudiante_required = require_roles("estudiante")


# ============================ MANEJO DE ERRORES ============================

_HTTP_POR_ERROR = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    (ValidationError, status.HTTP_400_BAD_REQUEST),
)


def ejecutar(accion: Callable[[], Any]) -> Any:
    """Ejecuta una llamada a services traduciendo sus errores a HTTP."""
    try:
        return accion()
    except ServiceError as exc:
        for tipo, codigo in _HTTP_POR_ERROR:
            if isinstance(exc, tipo):
                raise HTTPException(status_code=codigo, detail=str(exc)) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


# ============================ ESQUEMAS DE PETICION ============================

class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nombre: str = Field(min_length=1, max_length=150)
    rol: str = Field(description="rector | profesor | estudiante")
    fecha_nacimiento: Optional[date] = None
    especialidad: Optional[str] = Field(default=None, max_length=150)


class NombreUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)


class PerfilUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=150)
    email: Optional[EmailStr] = None
    fecha_nacimiento: Optional[date] = None


class InscripcionSeccionCreate(BaseModel):
    estudiante_id: int
    periodo: str = Field(max_length=20, description="Ej: '2026-1'")
    nombre_seccion: Optional[str] = Field(default=None, max_length=50)


class InscripcionCursoCreate(BaseModel):
    estudiante_id: int
    curso_id: int


class PuntosUpdate(BaseModel):
    estudiante_id: int
    tipo_punto: str = Field(description="Ej: 'asistencia', 'participacion'")
    valor: int = Field(description="Positivo suma, negativo descuenta")
    origen: Optional[str] = Field(default=None, max_length=100)


class CanjeCreate(BaseModel):
    recompensa_id: int


class AnuncioCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    contenido: str = Field(min_length=1)
    rol_destinatario: Optional[str] = Field(default=None, description="NULL = todos")
    curso_id: Optional[int] = None


# ============================ USUARIOS ============================

@router.post("/usuarios", status_code=status.HTTP_201_CREATED, tags=["Usuarios"])
def crear_usuario(
    datos: UsuarioCreate,
    conn=Depends(get_db),
    _=Depends(rector_required),
) -> Dict[str, Any]:
    from auth import hash_password  # el hashing es responsabilidad de auth.py

    return ejecutar(
        lambda: services.crear_usuario(
            conn,
            email=datos.email,
            password_hash=hash_password(datos.password),
            nombre=datos.nombre,
            rol=datos.rol,
            fecha_nacimiento=datos.fecha_nacimiento,
            especialidad=datos.especialidad,
        )
    )


@router.get("/usuarios/me", tags=["Usuarios"])
def obtener_mi_usuario(
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    return ejecutar(lambda: services.obtener_usuario(conn, current_user["id"]))


@router.patch("/usuarios/me/nombre", tags=["Usuarios"])
def actualizar_mi_nombre(
    datos: NombreUpdate,
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    return ejecutar(lambda: services.actualizar_nombre(conn, current_user["id"], datos.nombre))


@router.patch("/usuarios/me", tags=["Usuarios"])
def actualizar_mi_perfil(
    datos: PerfilUpdate,
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    return ejecutar(
        lambda: services.actualizar_perfil(
            conn,
            current_user["id"],
            nombre=datos.nombre,
            email=datos.email,
            fecha_nacimiento=datos.fecha_nacimiento,
        )
    )


@router.get("/usuarios/{usuario_id}", tags=["Usuarios"])
def obtener_usuario(
    usuario_id: int = Path(ge=1),
    conn=Depends(get_db),
    _=Depends(staff_required),
) -> Dict[str, Any]:
    return ejecutar(lambda: services.obtener_usuario(conn, usuario_id))


@router.patch("/usuarios/{usuario_id}", tags=["Usuarios"])
def actualizar_usuario(
    datos: PerfilUpdate,
    usuario_id: int = Path(ge=1),
    conn=Depends(get_db),
    _=Depends(rector_required),
) -> Dict[str, Any]:
    return ejecutar(
        lambda: services.actualizar_perfil(
            conn,
            usuario_id,
            nombre=datos.nombre,
            email=datos.email,
            fecha_nacimiento=datos.fecha_nacimiento,
        )
    )


# ============================ INSCRIPCIONES ============================

@router.post("/inscripciones", status_code=status.HTTP_201_CREATED, tags=["Inscripciones"])
def inscribir_en_seccion(
    datos: InscripcionSeccionCreate,
    conn=Depends(get_db),
    _=Depends(rector_required),
) -> Dict[str, Any]:
    """Inscribe al estudiante y le asigna automaticamente todas las materias."""
    return ejecutar(
        lambda: services.inscribir_en_seccion(
            conn, datos.estudiante_id, datos.periodo, datos.nombre_seccion
        )
    )


@router.post(
    "/inscripciones/curso", status_code=status.HTTP_201_CREATED, tags=["Inscripciones"]
)
def inscribir_en_curso(
    datos: InscripcionCursoCreate,
    conn=Depends(get_db),
    _=Depends(rector_required),
) -> Dict[str, Any]:
    return ejecutar(
        lambda: services.inscribir_en_curso(conn, datos.estudiante_id, datos.curso_id)
    )


@router.get("/estudiantes/{estudiante_id}/cursos", tags=["Inscripciones"])
def listar_cursos_estudiante(
    estudiante_id: int = Path(ge=1),
    periodo: Optional[str] = Query(default=None),
    conn=Depends(get_db),
    _=Depends(staff_required),
) -> List[Dict[str, Any]]:
    return ejecutar(lambda: services.listar_cursos_estudiante(conn, estudiante_id, periodo))


# ============================ PUNTOS ============================

@router.get("/puntos/me", tags=["Puntos"])
def consultar_mi_saldo(
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
) -> Dict[str, Any]:
    def accion():
        estudiante_id = services.obtener_estudiante_id(conn, current_user["id"])
        return services.consultar_saldo(conn, estudiante_id)

    return ejecutar(accion)


@router.get("/puntos/me/historial", tags=["Puntos"])
def historial_mis_puntos(
    limit: Optional[int] = Query(default=None, ge=1),
    offset: Optional[int] = Query(default=None, ge=0),
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
) -> List[Dict[str, Any]]:
    def accion():
        estudiante_id = services.obtener_transcripcion(conn, current_user["id"])["estudiante_id"]
        return services.historial_puntos(conn, estudiante_id, limit, offset)

    return ejecutar(accion)


@router.get("/puntos/{estudiante_id}", tags=["Puntos"])
def consultar_saldo(
    estudiante_id: int = Path(ge=1),
    conn=Depends(get_db),
    _=Depends(staff_required),
) -> Dict[str, Any]:
    return ejecutar(lambda: services.consultar_saldo(conn, estudiante_id))


@router.get("/puntos/{estudiante_id}/historial", tags=["Puntos"])
def historial_puntos(
    estudiante_id: int = Path(ge=1),
    limit: Optional[int] = Query(default=None, ge=1),
    offset: Optional[int] = Query(default=None, ge=0),
    conn=Depends(get_db),
    _=Depends(staff_required),
) -> List[Dict[str, Any]]:
    return ejecutar(lambda: services.historial_puntos(conn, estudiante_id, limit, offset))


@router.post("/puntos", status_code=status.HTTP_201_CREATED, tags=["Puntos"])
def actualizar_puntos(
    datos: PuntosUpdate,
    conn=Depends(get_db),
    _=Depends(staff_required),
) -> Dict[str, Any]:
    return ejecutar(
        lambda: services.actualizar_puntos(
            conn, datos.estudiante_id, datos.tipo_punto, datos.valor, datos.origen
        )
    )


# ============================ CANJE DE PUNTOS ============================

@router.get("/recompensas", tags=["Canjes"])
def listar_recompensas(
    limit: Optional[int] = Query(default=None, ge=1),
    offset: Optional[int] = Query(default=None, ge=0),
    conn=Depends(get_db),
    _=Depends(get_current_usuario),
) -> List[Dict[str, Any]]:
    return ejecutar(lambda: services.listar_recompensas(conn, limit, offset))


@router.post("/canjes", status_code=status.HTTP_201_CREATED, tags=["Canjes"])
def canjear_puntos(
    datos: CanjeCreate,
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
    _=Depends(estudiante_required),
) -> Dict[str, Any]:
    def accion():
        estudiante_id = services.obtener_transcripcion(conn, current_user["id"])["estudiante_id"]
        return services.canjear_puntos(conn, estudiante_id, datos.recompensa_id)

    return ejecutar(accion)


@router.get("/canjes/me", tags=["Canjes"])
def historial_mis_canjes(
    limit: Optional[int] = Query(default=None, ge=1),
    offset: Optional[int] = Query(default=None, ge=0),
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
    _=Depends(estudiante_required),
) -> List[Dict[str, Any]]:
    def accion():
        estudiante_id = services.obtener_transcripcion(conn, current_user["id"])["estudiante_id"]
        return services.historial_canjes(conn, estudiante_id, limit, offset)

    return ejecutar(accion)


# ============================ TRANSCRIPCION ============================

@router.get("/transcripcion/me", tags=["Transcripcion"])
def obtener_mi_transcripcion(
    periodo: Optional[str] = Query(default=None, description="Ej: '2026-1'"),
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
    _=Depends(estudiante_required),
) -> Dict[str, Any]:
    """Transcripcion del estudiante autenticado (solo notas publicadas)."""
    return ejecutar(lambda: services.obtener_transcripcion(conn, current_user["id"], periodo))


@router.get("/transcripcion/me/gpa", tags=["Transcripcion"])
def obtener_mi_gpa(
    periodo: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
    _=Depends(estudiante_required),
) -> Dict[str, Any]:
    return ejecutar(lambda: services.calcular_gpa(conn, current_user["id"], periodo))


# ============================ LEADERBOARD ============================

@router.get("/leaderboard/cursos/{curso_id}", tags=["Leaderboard"])
def obtener_leaderboard(
    curso_id: int = Path(ge=1),
    tipo_punto: Optional[str] = Query(default=None, description="NULL = ranking general"),
    limit: Optional[int] = Query(default=None, ge=1),
    offset: Optional[int] = Query(default=None, ge=0),
    conn=Depends(get_db),
    _=Depends(get_current_usuario),
) -> Dict[str, Any]:
    return ejecutar(
        lambda: services.obtener_leaderboard(conn, curso_id, tipo_punto, limit, offset)
    )


@router.get("/leaderboard/cursos/{curso_id}/mi-posicion", tags=["Leaderboard"])
def obtener_mi_posicion(
    curso_id: int = Path(ge=1),
    tipo_punto: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
    _=Depends(estudiante_required),
) -> Dict[str, Any]:
    return ejecutar(
        lambda: services.obtener_mi_posicion(conn, current_user["id"], curso_id, tipo_punto)
    )


# ============================ ANUNCIOS ============================

@router.get("/anuncios", tags=["Anuncios"])
def listar_anuncios(
    limit: Optional[int] = Query(default=None, ge=1),
    offset: Optional[int] = Query(default=None, ge=0),
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
) -> List[Dict[str, Any]]:
    """Anuncios del rol del usuario, por fecha descendente (scroll continuo)."""
    return ejecutar(lambda: services.listar_anuncios(conn, current_user["rol"], limit, offset))


@router.get("/anuncios/recientes", tags=["Anuncios"])
def listar_anuncios_recientes(
    dias: int = Query(default=7, ge=1, le=365),
    limit: Optional[int] = Query(default=None, ge=1),
    conn=Depends(get_db),
    _=Depends(get_current_usuario),
) -> List[Dict[str, Any]]:
    return ejecutar(lambda: services.listar_anuncios_recientes(conn, dias, limit))


@router.get("/anuncios/cursos/{curso_id}", tags=["Anuncios"])
def listar_anuncios_por_curso(
    curso_id: int = Path(ge=1),
    limit: Optional[int] = Query(default=None, ge=1),
    offset: Optional[int] = Query(default=None, ge=0),
    conn=Depends(get_db),
    _=Depends(get_current_usuario),
) -> List[Dict[str, Any]]:
    return ejecutar(lambda: services.listar_anuncios_por_curso(conn, curso_id, limit, offset))


@router.post("/anuncios", status_code=status.HTTP_201_CREATED, tags=["Anuncios"])
def crear_anuncio(
    datos: AnuncioCreate,
    current_user: dict = Depends(get_current_usuario),
    conn=Depends(get_db),
    _=Depends(staff_required),
) -> Dict[str, Any]:
    return ejecutar(
        lambda: services.crear_anuncio(
            conn,
            autor_id=current_user["id"],
            titulo=datos.titulo,
            contenido=datos.contenido,
            rol_destinatario=datos.rol_destinatario,
            curso_id=datos.curso_id,
        )
    )
