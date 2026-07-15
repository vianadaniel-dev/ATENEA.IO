from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import date, time, datetime

from app.database import get_db, get_cursor
from app.models import RolUsuario
from app.schemas import (
    BoletinResponse, CursoMateriaResponse, AnuncioResponse,
    RecompensaResponse, CanjeResponse, CanjeCreate, UsuarioUpdate, UsuarioResponse
)
from app.auth_utils import RoleChecker, get_current_usuario, verify_password, get_password_hash

router = APIRouter()

# Dependency to check if current user is Estudiante
estudiante_required = RoleChecker(allowed_roles=["estudiante"])

# Helper to calculate performance tier
def calculate_desempeno(valor: float) -> str:
    if valor < 3.0:
        return "Insuficiente"
    elif valor < 4.0:
        return "Mínimo"
    elif valor < 4.5:
        return "Satisfactorio"
    else:
        return "Avanzado"

# Helper to format a plain Recompensa row (used by listar_recompensas)
def format_recompensa_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "nombre": row["nombre"],
        "costo_puntos": row["costo_puntos"],
        "tipo_punto_id": row["tipo_punto_id"],
        "descripcion": row["descripcion"],
        "estado": row["estado"],
        "created_at": row["created_at"],
        "tipo_punto": {
            "id": row["tp_id"],
            "nombre": row["tp_nombre"],
            "descripcion": row["tp_desc"],
            "icono": row["icono"],
            "color": row["color"],
            "estado": row["tp_estado"]
        }
    }

# Helper to format a Canje row joined with its Recompensa + TipoPunto (used by canjear_recompensa, listar_mis_canjes)
def format_canje_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "estudiante_id": row["estudiante_id"],
        "puntos_usados": row["puntos_usados"],
        "estado": row["estado"],
        "created_at": row["created_at"],
        "recompensa": {
            "id": row["rec_id"],
            "nombre": row["rec_nombre"],
            "costo_puntos": row["costo_puntos"],
            "tipo_punto_id": row["tipo_punto_id"],
            "descripcion": row["descripcion"],
            "estado": row["rec_estado"],
            "created_at": row["rec_created"],
            "tipo_punto": {
                "id": row["tp_id"],
                "nombre": row["tp_nombre"],
                "descripcion": row["tp_desc"],
                "icono": row["icono"],
                "color": row["color"],
                "estado": row["tp_estado"]
            }
        }
    }

# ==========================================
# 1. BOLETÍN DE NOTAS (US-13)
# ==========================================

@router.get("/boletin", dependencies=[Depends(estudiante_required)])
def ver_boletin(
    periodo: str,
    current_user: dict = Depends(get_current_usuario),
    conn = Depends(get_db)
):
    with get_cursor(conn) as cur:
        # Get student profile
        cur.execute("SELECT id, estado FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        est_profile = cur.fetchone()
        if not est_profile or est_profile["estado"] != "activo":
            raise HTTPException(status_code=403, detail="Perfil de estudiante inactivo o no encontrado")

        estudiante_id = est_profile["id"]

        # Query published grades
        cur.execute(
            """
            SELECT m.nombre AS materia, cur.periodo, cal.valor AS nota_numerica, cal.fecha, u.nombre AS profesor_nombre
            FROM calificacion cal
            JOIN inscripcion i ON i.id = cal.inscripcion_id
            JOIN curso_materia cm ON cm.id = cal.curso_materia_id
            JOIN curso cur ON cur.id = cm.curso_id
            JOIN materia m ON m.id = cm.materia_id
            LEFT JOIN profesor p ON p.id = cm.profesor_id
            LEFT JOIN usuario u ON u.id = p.usuario_id
            WHERE i.estudiante_id = %s AND cur.periodo = %s AND cal.estado = 'publicada'
            """,
            (estudiante_id, periodo)
        )
        grades = cur.fetchall()

    results = []
    totales_valor = 0.0

    for g in grades:
        valor_float = float(g["nota_numerica"])
        totales_valor += valor_float

        results.append({
            "materia": g["materia"],
            "periodo": g["periodo"],
            "nota_numerica": valor_float,
            "desempeno": calculate_desempeno(valor_float),
            "profesor": g["profesor_nombre"] if g["profesor_nombre"] else "Por asignar",
            "fecha": str(g["fecha"])
        })

    gpa = (totales_valor / len(grades)) if grades else 0.0

    return {
        "periodo": periodo,
        "promedio_general": round(gpa, 2),
        "calificaciones": results
    }

# ==========================================
# 2. CURSOS Y COMUNICADOS (US-14)
# ==========================================

@router.get("/cursos", dependencies=[Depends(estudiante_required)])
def ver_mis_cursos(current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        est_profile = cur.fetchone()
        estudiante_id = est_profile["id"]

        # Get the student's curso through their single inscripcion
        cur.execute(
            """
            SELECT c.id, c.nombre, c.periodo
            FROM inscripcion i
            JOIN curso c ON c.id = i.curso_id
            WHERE i.estudiante_id = %s AND c.estado = 'activo'
            """,
            (estudiante_id,)
        )
        curso = cur.fetchone()
        if not curso:
            return []

        # List all materias offered within that curso
        cur.execute(
            """
            SELECT cm.id AS curso_materia_id, m.nombre AS materia, u.nombre AS profesor
            FROM curso_materia cm
            JOIN materia m ON m.id = cm.materia_id
            LEFT JOIN profesor p ON p.id = cm.profesor_id
            LEFT JOIN usuario u ON u.id = p.usuario_id
            WHERE cm.curso_id = %s AND cm.estado = 'activo'
            """,
            (curso["id"],)
        )
        materias = cur.fetchall()

        results = []
        for cmr in materias:
            cur.execute("SELECT id, dia_semana, hora_inicio, hora_fin, aula FROM horario WHERE curso_materia_id = %s", (cmr["curso_materia_id"],))
            horarios = cur.fetchall()

            horarios_formatted = [{
                "id": h["id"],
                "dia_semana": h["dia_semana"],
                "hora_inicio": str(h["hora_inicio"]),
                "hora_fin": str(h["hora_fin"]),
                "aula": h["aula"]
            } for h in horarios]

            results.append({
                "curso_materia_id": cmr["curso_materia_id"],
                "materia": cmr["materia"],
                "curso": curso["nombre"],
                "profesor": cmr["profesor"] if cmr["profesor"] else "Por asignar",
                "periodo": curso["periodo"],
                "horarios": horarios_formatted
            })

    return results

@router.get("/anuncios", dependencies=[Depends(estudiante_required)])
def ver_anuncios(current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        est_profile = cur.fetchone()
        estudiante_id = est_profile["id"]

        cur.execute(
            """
            SELECT a.id, a.titulo, a.contenido, a.fecha_publicacion, u.nombre AS autor, a.curso_materia_id
            FROM anuncio a
            JOIN usuario u ON u.id = a.autor_id
            LEFT JOIN curso_materia cm ON cm.id = a.curso_materia_id
            LEFT JOIN inscripcion i ON i.curso_id = cm.curso_id AND i.estudiante_id = %s
            WHERE a.estado = 'publicado'
              AND (
                (a.rol_destinatario = 'estudiante' OR a.rol_destinatario IS NULL)
                OR i.id IS NOT NULL
              )
            ORDER BY a.fecha_publicacion DESC
            """,
            (estudiante_id,)
        )
        anuncios = cur.fetchall()

        results = []
        for a in anuncios:
            results.append({
                "id": a["id"],
                "titulo": a["titulo"],
                "contenido": a["contenido"],
                "fecha_publicacion": str(a["fecha_publicacion"]),
                "autor": a["autor"],
                "tipo": "Curso" if a["curso_materia_id"] else "Institucional"
            })

    return results

# ==========================================
# 3. PUNTOS Y CLASIFICACIÓN (US-15)
# ==========================================

@router.get("/puntos", dependencies=[Depends(estudiante_required)])
def ver_mis_puntos_resumen(current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        est_profile = cur.fetchone()
        estudiante_id = est_profile["id"]

        cur.execute("SELECT id, nombre, descripcion, icono, color FROM tipo_punto WHERE estado = 'activo'")
        active_types = cur.fetchall()

        results = []
        for tp in active_types:
            # 1. Total points earned of this type
            cur.execute(
                "SELECT SUM(valor) FROM puntaje WHERE estudiante_id = %s AND tipo_punto_id = %s",
                (estudiante_id, tp["id"])
            )
            total_earned = cur.fetchone()["sum"] or 0

            # 2. Total points spent of this type
            cur.execute(
                """
                SELECT SUM(c.puntos_usados) FROM canje c
                JOIN recompensa r ON r.id = c.recompensa_id
                WHERE c.estudiante_id = %s AND r.tipo_punto_id = %s AND c.estado = 'aprobado'
                """,
                (estudiante_id, tp["id"])
            )
            total_spent = cur.fetchone()["sum"] or 0

            balance = total_earned - total_spent

            results.append({
                "tipo_punto_id": tp["id"],
                "nombre": tp["nombre"],
                "icono": tp["icono"],
                "color": tp["color"],
                "saldo": balance
            })

    return results

@router.get("/puntos/desglose", dependencies=[Depends(estudiante_required)])
def ver_desglose_puntos(current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        est_profile = cur.fetchone()
        estudiante_id = est_profile["id"]

        cur.execute(
            """
            SELECT p.id, p.valor, tp.nombre AS tipo_punto, p.origen, p.fecha
            FROM puntaje p
            JOIN tipo_punto tp ON tp.id = p.tipo_punto_id
            WHERE p.estudiante_id = %s
            ORDER BY p.fecha DESC
            """,
            (estudiante_id,)
        )
        puntajes = cur.fetchall()

        results = []
        for p in puntajes:
            results.append({
                "id": p["id"],
                "valor": p["valor"],
                "tipo_punto": p["tipo_punto"],
                "motivo": p["origen"],
                "fecha": str(p["fecha"])
            })

    return results

@router.get("/leaderboard", dependencies=[Depends(estudiante_required)])
def ver_tabla_clasificacion(
    tipo_punto_id: Optional[int] = None,
    current_user: dict = Depends(get_current_usuario),
    conn = Depends(get_db)
):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        est_profile = cur.fetchone()
        current_student_id = est_profile["id"]

        if tipo_punto_id:
            cur.execute(
                """
                SELECT e.id AS estudiante_id, u.nombre, COALESCE(SUM(p.valor), 0) AS puntos_totales
                FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                LEFT JOIN puntaje p ON p.estudiante_id = e.id AND p.tipo_punto_id = %s
                GROUP BY e.id, u.nombre
                ORDER BY puntos_totales DESC
                """,
                (tipo_punto_id,)
            )
        else:
            cur.execute(
                """
                SELECT e.id AS estudiante_id, u.nombre, e.total_puntos AS puntos_totales
                FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                ORDER BY e.total_puntos DESC
                """
            )
        query = cur.fetchall()

    results = []
    for rank, r in enumerate(query, 1):
        is_me = (r["estudiante_id"] == current_student_id)

        # Mask points for other students! US-15 criteria
        puntos = int(r["puntos_totales"]) if is_me else None

        results.append({
            "rank": rank,
            "estudiante_id": r["estudiante_id"],
            "nombre": r["nombre"],
            "puntos": puntos,
            "es_usuario_actual": is_me
        })

    return results

# ==========================================
# 4. TIENDA DE RECOMPENSAS (US-16)
# ==========================================

@router.get("/tienda/recompensas", response_model=List[RecompensaResponse], dependencies=[Depends(estudiante_required)])
def listar_recompensas(conn = Depends(get_db)):
    results = []
    with get_cursor(conn) as cur:
        cur.execute(
            """
            SELECT r.id, r.nombre, r.costo_puntos, r.tipo_punto_id, r.descripcion, r.estado, r.created_at,
                   tp.id AS tp_id, tp.nombre AS tp_nombre, tp.descripcion AS tp_desc, tp.icono, tp.color, tp.estado AS tp_estado
            FROM recompensa r
            JOIN tipo_punto tp ON tp.id = r.tipo_punto_id
            WHERE r.estado = 'activo'
            """
        )
        rows = cur.fetchall()
        for r in rows:
            results.append(format_recompensa_row(r))
    return results

@router.post("/tienda/canjear", response_model=CanjeResponse, dependencies=[Depends(estudiante_required)])
def canjear_recompensa(
    canje_data: CanjeCreate,
    current_user: dict = Depends(get_current_usuario),
    conn = Depends(get_db)
):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id, estado FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        est_profile = cur.fetchone()
        if not est_profile or est_profile["estado"] != "activo":
            raise HTTPException(status_code=403, detail="Perfil de estudiante inactivo o no encontrado")

        estudiante_id = est_profile["id"]

        # Get reward
        cur.execute(
            """
            SELECT r.id, r.nombre, r.costo_puntos, r.tipo_punto_id, tp.nombre AS tp_nombre
            FROM recompensa r
            JOIN tipo_punto tp ON tp.id = r.tipo_punto_id
            WHERE r.id = %s AND r.estado = 'activo'
            """,
            (canje_data.recompensa_id,)
        )
        recompensa = cur.fetchone()
        if not recompensa:
            raise HTTPException(status_code=404, detail="Recompensa no encontrada o inactiva")

        # Check point balance
        # 1. Earned
        cur.execute("SELECT SUM(valor) FROM puntaje WHERE estudiante_id = %s AND tipo_punto_id = %s", (estudiante_id, recompensa["tipo_punto_id"]))
        total_earned = cur.fetchone()["sum"] or 0

        # 2. Spent
        cur.execute(
            """
            SELECT SUM(c.puntos_usados) FROM canje c
            JOIN recompensa r ON r.id = c.recompensa_id
            WHERE c.estudiante_id = %s AND r.tipo_punto_id = %s AND c.estado = 'aprobado'
            """,
            (estudiante_id, recompensa["tipo_punto_id"])
        )
        total_spent = cur.fetchone()["sum"] or 0

        balance = total_earned - total_spent

        if balance < recompensa["costo_puntos"]:
            raise HTTPException(
                status_code=400,
                detail=f"Saldo insuficiente. Requiere {recompensa['costo_puntos']} puntos de '{recompensa['tp_nombre']}', tu saldo es {balance}."
            )

        # Create redemption request
        cur.execute(
            """
            INSERT INTO canje (estudiante_id, recompensa_id, puntos_usados, estado, created_at)
            VALUES (%s, %s, %s, 'pendiente', NOW()) RETURNING id
            """,
            (estudiante_id, recompensa["id"], recompensa["costo_puntos"])
        )
        canje_id = cur.fetchone()["id"]

        # Get complete redemption details
        cur.execute(
            """
            SELECT c.id, c.estudiante_id, c.puntos_usados, c.estado, c.created_at,
                   r.id AS rec_id, r.nombre AS rec_nombre, r.costo_puntos, r.tipo_punto_id, r.descripcion, r.estado AS rec_estado, r.created_at AS rec_created,
                   tp.id AS tp_id, tp.nombre AS tp_nombre, tp.descripcion AS tp_desc, tp.icono, tp.color, tp.estado AS tp_estado
            FROM canje c
            JOIN recompensa r ON r.id = c.recompensa_id
            JOIN tipo_punto tp ON tp.id = r.tipo_punto_id
            WHERE c.id = %s
            """,
            (canje_id,)
        )
        canje_details = format_canje_row(cur.fetchone())

    return canje_details

@router.get("/tienda/canjes", response_model=List[CanjeResponse], dependencies=[Depends(estudiante_required)])
def listar_mis_canjes(current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    results = []
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        est_profile = cur.fetchone()
        estudiante_id = est_profile["id"]

        cur.execute(
            """
            SELECT c.id, c.estudiante_id, c.puntos_usados, c.estado, c.created_at,
                   r.id AS rec_id, r.nombre AS rec_nombre, r.costo_puntos, r.tipo_punto_id, r.descripcion, r.estado AS rec_estado, r.created_at AS rec_created,
                   tp.id AS tp_id, tp.nombre AS tp_nombre, tp.descripcion AS tp_desc, tp.icono, tp.color, tp.estado AS tp_estado
            FROM canje c
            JOIN recompensa r ON r.id = c.recompensa_id
            JOIN tipo_punto tp ON tp.id = r.tipo_punto_id
            WHERE c.estudiante_id = %s
            ORDER BY c.created_at DESC
            """,
            (estudiante_id,)
        )
        rows = cur.fetchall()
        for r in rows:
            results.append(format_canje_row(r))

    return results

# ==========================================
# 5. EDITAR PERFIL (US-17)
# ==========================================

@router.get("/perfil", response_model=UsuarioResponse, dependencies=[Depends(estudiante_required)])
def ver_perfil(current_user: dict = Depends(get_current_usuario)):
    return current_user

@router.put("/perfil", response_model=UsuarioResponse, dependencies=[Depends(estudiante_required)])
def actualizar_perfil(
    perfil_data: UsuarioUpdate,
    current_user: dict = Depends(get_current_usuario),
    conn = Depends(get_db)
):
    with get_cursor(conn) as cur:
        user_id = current_user["id"]

        if perfil_data.nombre:
            cur.execute("UPDATE usuario SET nombre = %s WHERE id = %s", (perfil_data.nombre, user_id))

        if perfil_data.foto_url is not None:
            cur.execute("UPDATE usuario SET foto_url = %s WHERE id = %s", (perfil_data.foto_url, user_id))

        if perfil_data.password:
            if not perfil_data.confirm_password:
                raise HTTPException(
                    status_code=400,
                    detail="Se requiere confirmar la contraseña actual para cambiar la contraseña"
                )

            cur.execute("SELECT password_hash FROM usuario WHERE id = %s", (user_id,))
            current_pw_hash = cur.fetchone()["password_hash"]

            if not verify_password(perfil_data.confirm_password, current_pw_hash):
                raise HTTPException(
                    status_code=400,
                    detail="La contraseña actual confirmada es incorrecta"
                )

            new_hash = get_password_hash(perfil_data.password)
            cur.execute("UPDATE usuario SET password_hash = %s WHERE id = %s", (new_hash, user_id))

        cur.execute("SELECT id, email, nombre, rol, foto_url, created_at FROM usuario WHERE id = %s", (user_id,))
        updated_user = cur.fetchone()

    return updated_user

# ==========================================
# 6. TAREAS
# ==========================================

@router.get("/tareas", dependencies=[Depends(estudiante_required)])
def ver_mis_tareas(current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        estudiante_id = cur.fetchone()["id"]

        cur.execute(
            """
            SELECT t.id, t.titulo, t.descripcion, t.fecha_entrega, t.estado,
                   m.nombre AS materia, cur.nombre AS curso
            FROM tarea t
            JOIN curso_materia cm ON cm.id = t.curso_materia_id
            JOIN materia m ON m.id = cm.materia_id
            JOIN curso cur ON cur.id = cm.curso_id
            JOIN inscripcion i ON i.curso_id = cm.curso_id
            WHERE i.estudiante_id = %s
            ORDER BY t.fecha_entrega
            """,
            (estudiante_id,)
        )
        tareas = cur.fetchall()

    return [
        {
            "id": t["id"],
            "titulo": t["titulo"],
            "descripcion": t["descripcion"],
            "materia": t["materia"],
            "curso": t["curso"],
            "fecha_entrega": str(t["fecha_entrega"]) if t["fecha_entrega"] else None,
            "estado": t["estado"]
        }
        for t in tareas
    ]

# ==========================================
# 7. ASISTENCIA
# ==========================================

@router.get("/asistencia", dependencies=[Depends(estudiante_required)])
def ver_mi_asistencia(periodo: str, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM estudiante WHERE usuario_id = %s", (current_user["id"],))
        estudiante_id = cur.fetchone()["id"]

        cur.execute(
            """
            SELECT m.nombre AS materia, a.estado, COUNT(*) AS total
            FROM asistencia a
            JOIN inscripcion i ON i.id = a.inscripcion_id
            JOIN curso_materia cm ON cm.id = a.curso_materia_id
            JOIN curso cur ON cur.id = cm.curso_id
            JOIN materia m ON m.id = cm.materia_id
            WHERE i.estudiante_id = %s AND cur.periodo = %s
            GROUP BY m.nombre, a.estado
            ORDER BY m.nombre
            """,
            (estudiante_id, periodo)
        )
        rows = cur.fetchall()

    resumen = {}
    for r in rows:
        materia = r["materia"]
        if materia not in resumen:
            resumen[materia] = {"materia": materia, "presente": 0, "ausente": 0, "tarde": 0, "justificado": 0}
        resumen[materia][r["estado"]] = r["total"]

    return list(resumen.values())
