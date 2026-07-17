from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional

# Asumiendo que tienes estos en tu proyecto:
from database import get_db, get_cursor  # tus dependencias
from auth import login
# from models import CursoCreate, CursoResponse  # etc.

router = APIRouter(prefix="/rector", tags=["Rector"])  # O el prefijo que uses

login()
# ====================== MODELOS ======================
class EstudianteUpdateRector(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    estado: Optional[str] = None
    fecha_nacimiento: Optional[date] = None

class RolUsuario(str,enum.e)
# ====================== HELPERS ======================
def check_schedule_overlap(cur, profesor_id: int, horarios_data: list, exclude_curso_materia_id: Optional[int] = None) -> bool:
    if not profesor_id or not horarios_data:
        return False

    sql = """
        SELECT h.dia_semana, h.hora_inicio, h.hora_fin
        FROM horario h
        JOIN curso_materia cm ON cm.id = h.curso_materia_id
        WHERE cm.profesor_id = %s AND cm.estado = 'activo'
    """
    params = [profesor_id]
    if exclude_curso_materia_id:
        sql += " AND cm.id != %s"
        params.append(exclude_curso_materia_id)

    cur.execute(sql, tuple(params))
    existing_horarios = cur.fetchall()

    for new_h in horarios_data:
        for ext_h in existing_horarios:
            if new_h.dia_semana == ext_h["dia_semana"]:
                if (new_h.hora_inicio < ext_h["hora_fin"]) and (new_h.hora_fin > ext_h["hora_inicio"]):
                    return True
    return False


def fetch_estudiante_details(cur, estudiante_id: int) -> dict:
    cur.execute("""
        SELECT e.id, e.fecha_nacimiento, e.estado, e.total_puntos,
               u.id AS user_id, u.email, u.nombre, u.rol, u.foto_url, u.created_at
        FROM estudiante e
        JOIN usuario u ON u.id = e.usuario_id
        WHERE e.id = %s
    """, (estudiante_id,))
    row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "fecha_nacimiento": row["fecha_nacimiento"],
        "estado": row["estado"],
        "total_puntos": row["total_puntos"],
        "usuario": {
            "id": row["user_id"],
            "email": row["email"],
            "nombre": row["nombre"],
            "rol": row["rol"],
            "foto_url": row["foto_url"],
            "created_at": row["created_at"]
        }
    }


def fetch_profesor_details(cur, profesor_id: int) -> dict:
    cur.execute("""
        SELECT p.id, p.especialidad, p.estado,
               u.id AS user_id, u.email, u.nombre, u.rol, u.foto_url, u.created_at
        FROM profesor p
        JOIN usuario u ON u.id = p.usuario_id
        WHERE p.id = %s
    """, (profesor_id,))
    row = cur.fetchone()
    if not row:
        return None
    return { ... }  # similar al de estudiante


# ====================== RUTAS ======================
# Definition of dependeces 
class CursoBase(BaseModel):
    nombre: str
    periodo: str
    cupo_maximo: int = Field(default=30, ge=1)
    estado: str = "activo" 
    sede_id: Optional[str] = None
class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        if current_user["rol"] not in self.allowed_roles:
            raise HTTPException(
                status_cod = status.HTTP_403_FORBIDDEN,
                detail= "No tienes permisos suficientes para acceder a este recurso"
            )
        return current_user
rector_required = RoleChecker(allowed_roles=["rector"])
@router.post("/cursos", response_model=dict, dependencies=[Depends(rector_required)])
def crear_curso(curso: CursoCreate, conn=Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM curso WHERE nombre = %s AND periodo = %s", 
                   (curso.nombre, curso.periodo))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Ya existe un curso con ese nombre en ese periodo")

        cur.execute(
            """
            INSERT INTO curso (nombre, periodo, cupo_maximo, estado, sede_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, nombre, periodo, cupo_maximo, estado, sede_id
            """,
            (curso.nombre, curso.periodo, curso.cupo_maximo, curso.estado, curso.sede_id)
        )
        row = cur.fetchone()
        return dict(row) if row else None


@router.put("/estudiantes/{estudiante_id}", response_model=dict, dependencies=[Depends(rector_required)])
def actualizar_estudiante(estudiante_id: int, data: EstudianteUpdateRector, conn=Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id, usuario_id FROM estudiante WHERE id = %s", (estudiante_id,))
        est = cur.fetchone()
        if not est:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")

        user_id = est["usuario_id"]

        if data.nombre:
            cur.execute("UPDATE usuario SET nombre = %s WHERE id = %s", (data.nombre, user_id))

        if data.email:
            cur.execute("SELECT id FROM usuario WHERE email = %s AND id != %s", (data.email, user_id))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="El correo ya está en uso")
            cur.execute("UPDATE usuario SET email = %s WHERE id = %s", (data.email, user_id))

        if data.estado and data.estado in ["activo", "inactivo"]:
            cur.execute("UPDATE estudiante SET estado = %s WHERE id = %s", (data.estado, estudiante_id))

        if data.fecha_nacimiento:
            cur.execute("UPDATE estudiante SET fecha_nacimiento = %s WHERE id = %s", 
                       (data.fecha_nacimiento, estudiante_id))

        details = fetch_estudiante_details(cur, estudiante_id)
        conn.commit()  # Importante si no lo hace el context manager
        return details


@router.get("/mis-cursos", dependencies=[Depends(estudiante_required)])
def ver_mis_cursos(current_user: dict = Depends(get_current_usuario), conn=Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        est_profile = cur.fetchone()
        if not est_profile:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")

        estudiante_id = est_profile["id"]

        cur.execute("""
            SELECT c.id, c.nombre, c.periodo
            FROM inscripcion i
            JOIN curso c ON c.id = i.curso_id
            WHERE i.estudiante_id = %s AND c.estado = 'activo'
        """, (estudiante_id,))
        curso = cur.fetchone()
        if not curso:
            return []

        # ... resto de tu lógica de materias y horarios (la dejé igual, solo corrí indentación)
        cur.execute("""
            SELECT cm.id AS curso_materia_id, m.nombre AS materia, u.nombre AS profesor
            FROM curso_materia cm
            JOIN materia m ON m.id = cm.materia_id
            LEFT JOIN profesor p ON p.id = cm.profesor_id
            LEFT JOIN usuario u ON u.id = p.usuario_id
            WHERE cm.curso_id = %s AND cm.estado = 'activo'
        """, (curso["id"],))
        materias = cur.fetchall()

        results = []
        for cmr in materias:
            cur.execute("""
                SELECT id, dia_semana, hora_inicio, hora_fin, aula 
                FROM horario WHERE curso_materia_id = %s
            """, (cmr["curso_materia_id"],))
            horarios = cur.fetchall()

            horarios_formatted = [
                {
                    "id": h["id"],
                    "dia_semana": h["dia_semana"],
                    "hora_inicio": str(h["hora_inicio"]),
                    "hora_fin": str(h["hora_fin"]),
                    "aula": h["aula"]
                } for h in horarios
            ]

            results.append({
                "curso_materia_id": cmr["curso_materia_id"],
                "materia": cmr["materia"],
                "curso": curso["nombre"],
                "profesor": cmr["profesor"] if cmr.get("profesor") else "Por asignar",
                "periodo": curso["periodo"],
                "horarios": horarios_formatted
            })

    return results