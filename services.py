"""Logica de negocio.

Aqui viven las reglas del dominio: validaciones, calculos y orquestacion de
transacciones. Este modulo no escribe SQL: siempre delega en crud.py.

Los errores de dominio se expresan con las excepciones definidas abajo; es
routes.py quien las traduce a codigos HTTP.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import psycopg2

import crud
from config import settings
from database import get_cursor

logger = logging.getLogger(__name__)

ROLES_VALIDOS = ("rector", "profesor", "estudiante")

# Escala institucional 0.0 - 5.0
_ESCALA_DESEMPENO = (
    (Decimal("4.6"), "Superior"),
    (Decimal("4.0"), "Alto"),
    (Decimal("3.0"), "Basico"),
)


# ============================ EXCEPCIONES DE DOMINIO ============================

class ServiceError(Exception):
    """Error de negocio generico."""


class NotFoundError(ServiceError):
    """El recurso solicitado no existe."""


class ValidationError(ServiceError):
    """Los datos recibidos no cumplen una regla de negocio."""


class ConflictError(ServiceError):
    """La operacion choca con el estado actual (duplicados, saldo, stock)."""


# ============================ HELPERS ============================

def _normalizar_paginacion(limit: Optional[int], offset: Optional[int]) -> tuple[int, int]:
    """Acota la paginacion a los limites configurados."""
    limite = limit if limit is not None else settings.DEFAULT_PAGE_SIZE
    limite = max(1, min(limite, settings.MAX_PAGE_SIZE))
    desplazamiento = max(0, offset or 0)
    return limite, desplazamiento


def nivel_desempeno(valor: Decimal) -> str:
    """Traduce una calificacion numerica a su nivel cualitativo."""
    for minimo, etiqueta in _ESCALA_DESEMPENO:
        if valor >= minimo:
            return etiqueta
    return "Bajo"


def _obtener_estudiante_id(cur, usuario_id: int) -> int:
    """Resuelve el estudiante asociado al usuario autenticado."""
    estudiante = crud.select_estudiante_by_usuario_id(cur, usuario_id)
    if not estudiante:
        raise NotFoundError("El usuario autenticado no tiene un perfil de estudiante")
    return estudiante["id"]


# ============================ USUARIOS ============================

def crear_usuario(
    conn,
    email: str,
    password_hash: str,
    nombre: str,
    rol: str,
    fecha_nacimiento=None,
    especialidad: Optional[str] = None,
) -> Dict[str, Any]:
    """Crea el usuario y su perfil (estudiante/profesor) en una transaccion."""
    if rol not in ROLES_VALIDOS:
        raise ValidationError(f"Rol invalido. Valores permitidos: {', '.join(ROLES_VALIDOS)}")

    with get_cursor(conn) as cur:
        if crud.select_usuario_by_email(cur, email):
            raise ConflictError("El correo ya esta registrado")

        try:
            usuario = crud.insert_usuario(cur, email, password_hash, nombre, rol)
        except psycopg2.errors.UniqueViolation as exc:
            # Otra peticion pudo insertar el mismo email entre el SELECT y el INSERT.
            raise ConflictError("El correo ya esta registrado") from exc

        # El perfil se crea automaticamente segun el rol.
        if rol == "estudiante":
            perfil = crud.insert_estudiante(cur, usuario["id"], fecha_nacimiento)
            usuario["estudiante_id"] = perfil["id"]
        elif rol == "profesor":
            perfil = crud.insert_profesor(cur, usuario["id"], especialidad)
            usuario["profesor_id"] = perfil["id"]

        return usuario


def obtener_estudiante_id(conn, usuario_id: int) -> int:
    """Resuelve el estudiante del usuario autenticado.

    Los endpoints /me la usan para no aceptar nunca un estudiante_id
    enviado por el cliente.
    """
    with get_cursor(conn) as cur:
        return _obtener_estudiante_id(cur, usuario_id)


def obtener_usuario(conn, usuario_id: int) -> Dict[str, Any]:
    with get_cursor(conn) as cur:
        usuario = crud.select_usuario_by_id(cur, usuario_id)
        if not usuario:
            raise NotFoundError("Usuario no encontrado")
        return usuario


def actualizar_nombre(conn, usuario_id: int, nombre: str) -> Dict[str, Any]:
    nombre_limpio = (nombre or "").strip()
    if not nombre_limpio:
        raise ValidationError("El nombre no puede estar vacio")

    with get_cursor(conn) as cur:
        usuario = crud.update_usuario_nombre(cur, usuario_id, nombre_limpio)
        if not usuario:
            raise NotFoundError("Usuario no encontrado")
        return usuario


def actualizar_perfil(
    conn,
    usuario_id: int,
    nombre: Optional[str] = None,
    email: Optional[str] = None,
    fecha_nacimiento=None,
) -> Dict[str, Any]:
    """Actualiza los datos basicos del usuario y, si aplica, los de estudiante."""
    with get_cursor(conn) as cur:
        if not crud.select_usuario_by_id(cur, usuario_id):
            raise NotFoundError("Usuario no encontrado")

        if email and crud.select_usuario_id_by_email(cur, email, excluir_id=usuario_id):
            raise ConflictError("El correo ya esta en uso por otro usuario")

        nombre_limpio = nombre.strip() if nombre else None
        if nombre is not None and not nombre_limpio:
            raise ValidationError("El nombre no puede estar vacio")

        usuario = crud.update_usuario_perfil(cur, usuario_id, nombre_limpio, email)

        if fecha_nacimiento is not None:
            estudiante = crud.select_estudiante_by_usuario_id(cur, usuario_id)
            if not estudiante:
                raise ValidationError("Solo un estudiante puede tener fecha de nacimiento")
            crud.update_estudiante_perfil(cur, estudiante["id"], fecha_nacimiento, None)
            usuario["fecha_nacimiento"] = fecha_nacimiento

        return usuario


# ============================ INSCRIPCIONES ============================

def inscribir_en_seccion(
    conn, estudiante_id: int, periodo: str, nombre_seccion: Optional[str] = None
) -> Dict[str, Any]:
    """Inscribe al estudiante y le asigna automaticamente todas las materias.

    En este esquema cada curso es una materia dictada en un periodo y seccion.
    Por eso "inscribir en una seccion" equivale a crear de una sola vez las
    inscripciones de todas las materias de esa seccion: el cliente nunca las
    asigna una por una.
    """
    with get_cursor(conn) as cur:
        if not crud.select_estudiante_by_id(cur, estudiante_id):
            raise NotFoundError("Estudiante no encontrado")

        cursos = crud.select_cursos_by_periodo_seccion(cur, periodo, nombre_seccion)
        if not cursos:
            raise NotFoundError(
                f"No hay materias registradas para el periodo '{periodo}'"
                + (f", seccion '{nombre_seccion}'" if nombre_seccion else "")
            )

        asignadas, ya_inscritas = [], []
        for curso in cursos:
            inscripcion = crud.insert_inscripcion(cur, estudiante_id, curso["id"])
            destino = ya_inscritas if inscripcion is None else asignadas
            destino.append({"curso_id": curso["id"], "materia": curso["materia"]})

        if not asignadas:
            raise ConflictError("El estudiante ya estaba inscrito en todas las materias")

        return {
            "estudiante_id": estudiante_id,
            "periodo": periodo,
            "nombre_seccion": nombre_seccion,
            "materias_asignadas": asignadas,
            "materias_ya_inscritas": ya_inscritas,
            "total_asignadas": len(asignadas),
        }


def inscribir_en_curso(conn, estudiante_id: int, curso_id: int) -> Dict[str, Any]:
    """Inscribe al estudiante en un unico curso (materia)."""
    with get_cursor(conn) as cur:
        if not crud.select_estudiante_by_id(cur, estudiante_id):
            raise NotFoundError("Estudiante no encontrado")
        if not crud.select_curso_by_id(cur, curso_id):
            raise NotFoundError("Curso no encontrado")

        inscripcion = crud.insert_inscripcion(cur, estudiante_id, curso_id)
        if inscripcion is None:
            raise ConflictError("El estudiante ya esta inscrito en este curso")
        return inscripcion


def listar_cursos_estudiante(
    conn, estudiante_id: int, periodo: Optional[str] = None
) -> List[Dict[str, Any]]:
    with get_cursor(conn) as cur:
        return crud.select_cursos_by_estudiante(cur, estudiante_id, periodo)


# ============================ SISTEMA DE PUNTOS ============================

def consultar_saldo(conn, estudiante_id: int) -> Dict[str, Any]:
    """Saldo = puntos ganados - puntos gastados en canjes."""
    with get_cursor(conn) as cur:
        if not crud.select_estudiante_by_id(cur, estudiante_id):
            raise NotFoundError("Estudiante no encontrado")

        totales = crud.select_totales_puntos(cur, estudiante_id)
        ganados = int(totales["puntos_ganados"])
        gastados = int(totales["puntos_gastados"])
        return {
            "estudiante_id": estudiante_id,
            "puntos_ganados": ganados,
            "puntos_gastados": gastados,
            "saldo": ganados - gastados,
        }


def actualizar_puntos(
    conn,
    estudiante_id: int,
    tipo_punto: str,
    valor: int,
    origen: Optional[str] = None,
) -> Dict[str, Any]:
    """Registra un movimiento de puntos y devuelve el saldo actualizado."""
    if valor == 0:
        raise ValidationError("El valor de los puntos no puede ser cero")

    with get_cursor(conn) as cur:
        if not crud.select_estudiante_by_id(cur, estudiante_id):
            raise NotFoundError("Estudiante no encontrado")

        tipo = crud.select_tipo_punto_by_nombre(cur, tipo_punto)
        if not tipo:
            raise NotFoundError(f"El tipo de punto '{tipo_punto}' no existe")

        # Bloqueamos al estudiante para que dos ajustes simultaneos no se pisen.
        crud.lock_estudiante(cur, estudiante_id)

        if valor < 0:
            totales = crud.select_totales_puntos(cur, estudiante_id)
            saldo = int(totales["puntos_ganados"]) - int(totales["puntos_gastados"])
            if saldo + valor < 0:
                raise ConflictError(
                    f"Saldo insuficiente: el estudiante tiene {saldo} puntos"
                )

        movimiento = crud.insert_puntaje(cur, estudiante_id, tipo["id"], valor, origen)
        totales = crud.select_totales_puntos(cur, estudiante_id)
        saldo = int(totales["puntos_ganados"]) - int(totales["puntos_gastados"])

        return {"movimiento": movimiento, "saldo": saldo}


def historial_puntos(
    conn, estudiante_id: int, limit: Optional[int] = None, offset: Optional[int] = None
) -> List[Dict[str, Any]]:
    limite, desplazamiento = _normalizar_paginacion(limit, offset)
    with get_cursor(conn) as cur:
        if not crud.select_estudiante_by_id(cur, estudiante_id):
            raise NotFoundError("Estudiante no encontrado")
        return crud.select_historial_puntos(cur, estudiante_id, limite, desplazamiento)


def listar_recompensas(
    conn, limit: Optional[int] = None, offset: Optional[int] = None
) -> List[Dict[str, Any]]:
    limite, desplazamiento = _normalizar_paginacion(limit, offset)
    with get_cursor(conn) as cur:
        return crud.select_recompensas_activas(cur, limite, desplazamiento)


def canjear_puntos(conn, estudiante_id: int, recompensa_id: int) -> Dict[str, Any]:
    """Canjea una recompensa validando saldo y stock.

    Todo ocurre en una sola transaccion: si algo falla no se descuenta nada.
    El bloqueo del estudiante y de la recompensa evita que dos canjes
    simultaneos gasten el mismo saldo.
    """
    with get_cursor(conn) as cur:
        if not crud.select_estudiante_by_id(cur, estudiante_id):
            raise NotFoundError("Estudiante no encontrado")

        crud.lock_estudiante(cur, estudiante_id)

        recompensa = crud.select_recompensa_by_id(cur, recompensa_id)
        if not recompensa:
            raise NotFoundError("Recompensa no encontrada")
        if not recompensa["activo"]:
            raise ConflictError("La recompensa no esta disponible")

        costo = int(recompensa["costo_puntos"])
        totales = crud.select_totales_puntos(cur, estudiante_id)
        saldo = int(totales["puntos_ganados"]) - int(totales["puntos_gastados"])

        # Regla central: no se canjea sin saldo suficiente.
        if saldo < costo:
            raise ConflictError(
                f"Saldo insuficiente: tienes {saldo} puntos y la recompensa cuesta {costo}"
            )

        if recompensa["stock"] is not None:
            if crud.update_recompensa_stock(cur, recompensa_id, 1) is None:
                raise ConflictError("La recompensa esta agotada")

        canje = crud.insert_canje(cur, estudiante_id, recompensa_id, costo)

        return {
            "canje": canje,
            "recompensa": recompensa["nombre"],
            "puntos_gastados": costo,
            "saldo_anterior": saldo,
            "saldo": saldo - costo,
        }


def historial_canjes(
    conn, estudiante_id: int, limit: Optional[int] = None, offset: Optional[int] = None
) -> List[Dict[str, Any]]:
    limite, desplazamiento = _normalizar_paginacion(limit, offset)
    with get_cursor(conn) as cur:
        return crud.select_canjes_by_estudiante(cur, estudiante_id, limite, desplazamiento)


# ============================ TRANSCRIPCION ACADEMICA ============================

def obtener_transcripcion(
    conn, usuario_id: int, periodo: Optional[str] = None
) -> Dict[str, Any]:
    """Transcripcion del estudiante autenticado.

    Solo incluye calificaciones publicadas y solo del propio estudiante: el
    id se deriva del usuario autenticado, nunca se acepta desde el cliente.
    """
    with get_cursor(conn) as cur:
        estudiante_id = _obtener_estudiante_id(cur, usuario_id)

        filas = crud.select_calificaciones_publicadas(cur, estudiante_id, periodo)
        resumen = crud.select_gpa(cur, estudiante_id, periodo)
        periodos = [p["periodo"] for p in crud.select_periodos_by_estudiante(cur, estudiante_id)]

    calificaciones = [
        {
            "curso": fila["curso"],
            "materia": fila["materia"],
            "periodo": fila["periodo"],
            "tipo_evaluacion": fila["tipo_evaluacion"],
            "calificacion": float(fila["valor"]),
            "nivel_desempeno": nivel_desempeno(fila["valor"]),
            "profesor": fila["profesor"],
            "fecha": fila["fecha"],
        }
        for fila in filas
    ]

    gpa = resumen["gpa"]
    return {
        "estudiante_id": estudiante_id,
        "periodo": periodo,
        "periodos_disponibles": periodos,
        "gpa": float(gpa) if gpa is not None else None,
        "nivel_desempeno_gpa": nivel_desempeno(gpa) if gpa is not None else None,
        "total_calificaciones": int(resumen["total_calificaciones"]),
        "calificaciones": calificaciones,
    }


def calcular_gpa(conn, usuario_id: int, periodo: Optional[str] = None) -> Dict[str, Any]:
    """GPA del periodo, calculado por PostgreSQL."""
    with get_cursor(conn) as cur:
        estudiante_id = _obtener_estudiante_id(cur, usuario_id)
        resumen = crud.select_gpa(cur, estudiante_id, periodo)

    gpa = resumen["gpa"]
    return {
        "estudiante_id": estudiante_id,
        "periodo": periodo,
        "gpa": float(gpa) if gpa is not None else None,
        "nivel_desempeno": nivel_desempeno(gpa) if gpa is not None else None,
        "total_calificaciones": int(resumen["total_calificaciones"]),
    }


# ============================ LEADERBOARD ============================

def obtener_leaderboard(
    conn,
    curso_id: int,
    tipo_punto: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Dict[str, Any]:
    """Ranking del curso. Solo devuelve posicion, nombre y curso.

    El calculo lo hace PostgreSQL con SUM + DENSE_RANK, de modo que no se
    traen a Python los puntajes de todos los estudiantes.
    """
    limite, desplazamiento = _normalizar_paginacion(limit, offset)

    with get_cursor(conn) as cur:
        curso = crud.select_curso_by_id(cur, curso_id)
        if not curso:
            raise NotFoundError("Curso no encontrado")

        tipo_punto_id = None
        if tipo_punto:
            tipo = crud.select_tipo_punto_by_nombre(cur, tipo_punto)
            if not tipo:
                raise NotFoundError(f"El tipo de punto '{tipo_punto}' no existe")
            tipo_punto_id = tipo["id"]

        ranking = crud.select_leaderboard_por_curso(
            cur, curso_id, tipo_punto_id, limite, desplazamiento
        )

    return {
        "curso_id": curso_id,
        "curso": curso["curso"],
        "tipo_punto": tipo_punto or "general",
        "ranking": ranking,
    }


def obtener_mi_posicion(
    conn, usuario_id: int, curso_id: int, tipo_punto: Optional[str] = None
) -> Dict[str, Any]:
    with get_cursor(conn) as cur:
        estudiante_id = _obtener_estudiante_id(cur, usuario_id)

        tipo_punto_id = None
        if tipo_punto:
            tipo = crud.select_tipo_punto_by_nombre(cur, tipo_punto)
            if not tipo:
                raise NotFoundError(f"El tipo de punto '{tipo_punto}' no existe")
            tipo_punto_id = tipo["id"]

        posicion = crud.select_posicion_estudiante_en_curso(
            cur, curso_id, estudiante_id, tipo_punto_id
        )

    if not posicion:
        raise NotFoundError("El estudiante no esta inscrito en este curso")
    return posicion


# ============================ ANUNCIOS ============================

def listar_anuncios(
    conn,
    rol: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Anuncios ordenados por fecha descendente, paginados para scroll continuo."""
    if rol is not None and rol not in ROLES_VALIDOS:
        raise ValidationError(f"Rol invalido. Valores permitidos: {', '.join(ROLES_VALIDOS)}")

    limite, desplazamiento = _normalizar_paginacion(limit, offset)
    with get_cursor(conn) as cur:
        return crud.select_anuncios(cur, limite, desplazamiento, rol)


def listar_anuncios_por_curso(
    conn, curso_id: int, limit: Optional[int] = None, offset: Optional[int] = None
) -> List[Dict[str, Any]]:
    limite, desplazamiento = _normalizar_paginacion(limit, offset)
    with get_cursor(conn) as cur:
        if not crud.select_curso_by_id(cur, curso_id):
            raise NotFoundError("Curso no encontrado")
        return crud.select_anuncios_by_curso(cur, curso_id, limite, desplazamiento)


def listar_anuncios_recientes(
    conn, dias: int = 7, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    if dias < 1:
        raise ValidationError("El numero de dias debe ser mayor a cero")

    limite, _ = _normalizar_paginacion(limit, 0)
    with get_cursor(conn) as cur:
        return crud.select_anuncios_recientes(cur, dias, limite)


def crear_anuncio(
    conn,
    autor_id: int,
    titulo: str,
    contenido: str,
    rol_destinatario: Optional[str] = None,
    curso_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not (titulo or "").strip():
        raise ValidationError("El titulo es obligatorio")
    if not (contenido or "").strip():
        raise ValidationError("El contenido es obligatorio")
    if rol_destinatario is not None and rol_destinatario not in ROLES_VALIDOS:
        raise ValidationError(f"Rol invalido. Valores permitidos: {', '.join(ROLES_VALIDOS)}")

    with get_cursor(conn) as cur:
        if curso_id is not None and not crud.select_curso_by_id(cur, curso_id):
            raise NotFoundError("Curso no encontrado")
        return crud.insert_anuncio(
            cur, autor_id, titulo.strip(), contenido.strip(), rol_destinatario, curso_id
        )
