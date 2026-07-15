from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import date

from app.database import get_db, get_cursor
from app.models import RolUsuario
from app.schemas import (
    CursoResponse, EstudianteResponse, CalificacionCreate, CalificacionUpdate, CalificacionResponse,
    PuntajeCreate, PuntajeResponse, AnuncioResponse, TipoPuntoResponse,
    TareaCreate, TareaUpdate, TareaResponse, AsistenciaBulkCreate, AsistenciaResponse
)
from app.auth_utils import RoleChecker, get_current_usuario

router = APIRouter()

# Dependency to check if current user is Profesor
profesor_required = RoleChecker(allowed_roles=["profesor"])

# Helper to verify professor teaches the course
def verify_profesor_teaches_course(cur, profesor_id: int, curso_id: int):
    cur.execute("SELECT id FROM curso WHERE id = %s AND profesor_id = %s", (curso_id, profesor_id))
    if not cur.fetchone():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso sobre este curso o el curso no existe"
        )

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

# Helper to recalculate boletin average for a student in a course
def recalculate_boletin_raw(cur, estudiante_id: int, curso_id: int, periodo: str):
    # Get student enrollment ID
    cur.execute("SELECT id FROM inscripcion WHERE estudiante_id = %s AND curso_id = %s", (estudiante_id, curso_id))
    insc = cur.fetchone()
    if not insc:
        return
        
    insc_id = insc["id"]
    
    # Get published grades
    cur.execute("SELECT valor FROM calificacion WHERE inscripcion_id = %s AND estado = 'publicada'", (insc_id,))
    grades = cur.fetchall()
    
    if not grades:
        # Delete boletin if exists
        cur.execute(
            "DELETE FROM boletin WHERE estudiante_id = %s AND curso_id = %s AND periodo = %s",
            (estudiante_id, curso_id, periodo)
        )
        return

    avg = sum(float(g["valor"]) for g in grades) / len(grades)
    
    # Upsert Boletin
    cur.execute(
        "SELECT id FROM boletin WHERE estudiante_id = %s AND curso_id = %s AND periodo = %s",
        (estudiante_id, curso_id, periodo)
    )
    boletin = cur.fetchone()
    
    if boletin:
        cur.execute(
            "UPDATE boletin SET promedio_final = %s, fecha_generacion = CURRENT_DATE WHERE id = %s",
            (avg, boletin["id"])
        )
    else:
        cur.execute(
            """
            INSERT INTO boletin (estudiante_id, curso_id, periodo, promedio_final, fecha_generacion)
            VALUES (%s, %s, %s, %s, CURRENT_DATE)
            """,
            (estudiante_id, curso_id, periodo, avg)
        )

# ==========================================
# 1. CURSOS Y HORARIO (US-09, US-12)
# ==========================================

@router.get("/cursos", dependencies=[Depends(profesor_required)])
def listar_cursos_asignados(current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        # Get professor profile
        cur.execute("SELECT id, estado FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        prof_profile = cur.fetchone()
        if not prof_profile or prof_profile["estado"] != "activo":
            raise HTTPException(status_code=403, detail="Perfil de profesor inactivo o no encontrado")
            
        profesor_id = prof_profile["id"]
        
        # Get courses
        cur.execute(
            "SELECT c.id, m.nombre AS materia, c.periodo, c.nombre_seccion FROM curso c JOIN materia m ON m.id = c.materia_id WHERE c.profesor_id = %s AND c.estado = 'activo'",
            (profesor_id,)
        )
        cursos = cur.fetchall()
        
        results = []
        for c in cursos:
            # Count enrolled students
            cur.execute("SELECT COUNT(*) FROM inscripcion WHERE curso_id = %s", (c["id"],))
            student_count = cur.fetchone()["count"]
            
            # Format horarios
            cur.execute("SELECT id, dia_semana, hora_inicio, hora_fin, aula FROM horario WHERE curso_id = %s", (c["id"],))
            horarios = cur.fetchall()
            
            horarios_formatted = [{
                "id": h["id"],
                "dia_semana": h["dia_semana"],
                "hora_inicio": str(h["hora_inicio"]),
                "hora_fin": str(h["hora_fin"]),
                "aula": h["aula"]
            } for h in horarios]
            
            results.append({
                "id": c["id"],
                "materia": c["materia"],
                "periodo": c["periodo"],
                "nombre_seccion": c["nombre_seccion"],
                "estudiantes_matriculados": student_count,
                "horarios": horarios_formatted
            })
            
    return results

@router.get("/cursos/{curso_id}/estudiantes", dependencies=[Depends(profesor_required)])
def ver_estudiantes_curso(curso_id: int, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        # Get professor profile
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        verify_profesor_teaches_course(cur, profesor_id, curso_id)
        
        # Get all enrolled students
        cur.execute(
            """
            SELECT e.id AS estudiante_id, u.nombre, u.email, enc.fecha_inscripcion, e.total_puntos
            FROM inscripcion enc
            JOIN estudiante e ON e.id = enc.estudiante_id
            JOIN usuario u ON u.id = e.usuario_id
            WHERE enc.curso_id = %s
            """,
            (curso_id,)
        )
        enrollments = cur.fetchall()
        
        results = []
        for enc in enrollments:
            results.append({
                "estudiante_id": enc["estudiante_id"],
                "nombre": enc["nombre"],
                "email": enc["email"],
                "fecha_inscripcion": str(enc["fecha_inscripcion"]),
                "total_puntos": enc["total_puntos"]
            })
    return results

@router.get("/horario", dependencies=[Depends(profesor_required)])
def ver_mi_horario(current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        # Get professor profile
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        
        cur.execute(
            """
            SELECT h.dia_semana, h.hora_inicio, h.hora_fin, h.aula, m.nombre AS materia, c.nombre_seccion AS seccion
            FROM horario h
            JOIN curso c ON c.id = h.curso_id
            JOIN materia m ON m.id = c.materia_id
            WHERE c.profesor_id = %s AND c.estado = 'activo'
            ORDER BY h.dia_semana, h.hora_inicio
            """,
            (profesor_id,)
        )
        horarios = cur.fetchall()
        
        results = []
        for h in horarios:
            results.append({
                "dia_semana": h["dia_semana"],
                "hora_inicio": str(h["hora_inicio"]),
                "hora_fin": str(h["hora_fin"]),
                "aula": h["aula"],
                "materia": h["materia"],
                "seccion": h["seccion"]
            })
    return results

# ==========================================
# 2. CARGA Y GESTIÓN DE NOTAS (US-10)
# ==========================================

@router.post("/calificaciones", response_model=CalificacionResponse, dependencies=[Depends(profesor_required)])
def registrar_nota(calificacion: CalificacionCreate, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        
        # Find enrollment
        cur.execute("SELECT id, estudiante_id, curso_id FROM inscripcion WHERE id = %s", (calificacion.inscripcion_id,))
        insc = cur.fetchone()
        if not insc:
            raise HTTPException(status_code=404, detail="Inscripción no encontrada")
            
        # Verify course belongs to this professor
        verify_profesor_teaches_course(cur, profesor_id, insc["curso_id"])
        
        cur.execute("SELECT periodo FROM curso WHERE id = %s", (insc["curso_id"],))
        periodo = cur.fetchone()["periodo"]

        # Create grade
        cur.execute(
            """
            INSERT INTO calificacion (inscripcion_id, tipo_evaluacion, valor, estado, fecha)
            VALUES (%s, %s, %s, %s, CURRENT_DATE) RETURNING id, inscripcion_id, tipo_evaluacion, valor, estado, fecha
            """,
            (calificacion.inscripcion_id, calificacion.tipo_evaluacion, calificacion.valor, calificacion.estado)
        )
        db_cal = dict(cur.fetchone())
        db_cal["desempeno"] = calculate_desempeno(float(db_cal["valor"]))

        # If published, recalculate boletin
        if db_cal["estado"] == "publicada":
            recalculate_boletin_raw(cur, insc["estudiante_id"], insc["curso_id"], periodo)

    return db_cal

@router.put("/calificaciones/{calificacion_id}", response_model=CalificacionResponse, dependencies=[Depends(profesor_required)])
def editar_nota(calificacion_id: int, cal_data: CalificacionUpdate, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        
        cur.execute("SELECT id, inscripcion_id, tipo_evaluacion, valor, estado, fecha FROM calificacion WHERE id = %s", (calificacion_id,))
        db_cal = cur.fetchone()
        if not db_cal:
            raise HTTPException(status_code=404, detail="Calificación no encontrada")

        cur.execute("SELECT estudiante_id, curso_id FROM inscripcion WHERE id = %s", (db_cal["inscripcion_id"],))
        insc = cur.fetchone()
        
        verify_profesor_teaches_course(cur, profesor_id, insc["curso_id"])
        
        cur.execute("SELECT periodo FROM curso WHERE id = %s", (insc["curso_id"],))
        periodo = cur.fetchone()["periodo"]
        
        # Update fields dynamically
        update_fields = []
        params = []
        for key, val in cal_data.model_dump(exclude_unset=True).items():
            update_fields.append(f"{key} = %s")
            params.append(val)
            
        if update_fields:
            params.append(calificacion_id)
            cur.execute(
                f"UPDATE calificacion SET {', '.join(update_fields)} WHERE id = %s RETURNING id, inscripcion_id, tipo_evaluacion, valor, estado, fecha",
                tuple(params)
            )
            updated_cal = dict(cur.fetchone())
        else:
            updated_cal = dict(db_cal)
        updated_cal["desempeno"] = calculate_desempeno(float(updated_cal["valor"]))

        # Recalculate boletin
        recalculate_boletin_raw(cur, insc["estudiante_id"], insc["curso_id"], periodo)

    return updated_cal

@router.delete("/calificaciones/{calificacion_id}", dependencies=[Depends(profesor_required)])
def eliminar_nota(calificacion_id: int, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        
        cur.execute("SELECT id, inscripcion_id, estado FROM calificacion WHERE id = %s", (calificacion_id,))
        db_cal = cur.fetchone()
        if not db_cal:
            raise HTTPException(status_code=404, detail="Calificación no encontrada")
            
        # US-10: "Se puede eliminar una nota propia solo si está en estado 'Borrador'."
        if db_cal["estado"] != "borrador":
            raise HTTPException(
                status_code=400,
                detail="Solo se pueden eliminar calificaciones que estén en estado 'Borrador'"
            )
            
        cur.execute("SELECT estudiante_id, curso_id FROM inscripcion WHERE id = %s", (db_cal["inscripcion_id"],))
        insc = cur.fetchone()
        
        verify_profesor_teaches_course(cur, profesor_id, insc["curso_id"])
        
        cur.execute("SELECT periodo FROM curso WHERE id = %s", (insc["curso_id"],))
        periodo = cur.fetchone()["periodo"]
        
        cur.execute("DELETE FROM calificacion WHERE id = %s", (calificacion_id,))
        
        # Recalculate boletin
        recalculate_boletin_raw(cur, insc["estudiante_id"], insc["curso_id"], periodo)
        
    return {"message": "Calificación eliminada correctamente"}

@router.get("/calificaciones", dependencies=[Depends(profesor_required)])
def consultar_notas(
    curso_id: int,
    estudiante_id: Optional[int] = None,
    current_user: dict = Depends(get_current_usuario),
    conn = Depends(get_db)
):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        verify_profesor_teaches_course(cur, profesor_id, curso_id)
        
        sql = """
            SELECT g.id, i.estudiante_id, u.nombre AS estudiante_nombre, g.tipo_evaluacion, g.valor, g.fecha, g.estado
            FROM calificacion g
            JOIN inscripcion i ON i.id = g.inscripcion_id
            JOIN estudiante e ON e.id = i.estudiante_id
            JOIN usuario u ON u.id = e.usuario_id
            WHERE i.curso_id = %s
        """
        params = [curso_id]
        if estudiante_id:
            sql += " AND i.estudiante_id = %s"
            params.append(estudiante_id)
            
        cur.execute(sql, tuple(params))
        grades = cur.fetchall()
        
        results = []
        for g in grades:
            results.append({
                "id": g["id"],
                "estudiante_id": g["estudiante_id"],
                "estudiante_nombre": g["estudiante_nombre"],
                "tipo_evaluacion": g["tipo_evaluacion"],
                "valor": float(g["valor"]),
                "desempeno": calculate_desempeno(float(g["valor"])),
                "fecha": str(g["fecha"]),
                "estado": g["estado"]
            })
            
    return results

# ==========================================
# 3. ASIGNAR GAMIFICACIÓN (US-11)
# ==========================================

@router.get("/tipos-puntos", response_model=List[TipoPuntoResponse], dependencies=[Depends(profesor_required)])
def listar_tipos_puntos_activos(conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute(
            "SELECT id, nombre, descripcion, icono, color, estado FROM tipo_punto WHERE estado = 'activo' ORDER BY id"
        )
        rows = cur.fetchall()
    return rows

@router.post("/puntajes", response_model=PuntajeResponse, dependencies=[Depends(profesor_required)])
def asignar_puntos(puntaje: PuntajeCreate, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        
        # Verify professor teaches course
        verify_profesor_teaches_course(cur, profesor_id, puntaje.curso_id)
        
        # Verify student is enrolled
        cur.execute("SELECT id FROM inscripcion WHERE estudiante_id = %s AND curso_id = %s", (puntaje.estudiante_id, puntaje.curso_id))
        is_enrolled = cur.fetchone()
        if not is_enrolled:
            raise HTTPException(
                status_code=400,
                detail="El estudiante seleccionado no está inscrito en este curso"
            )
            
        # Get course name
        cur.execute("SELECT m.nombre FROM curso c JOIN materia m ON m.id = c.materia_id WHERE c.id = %s", (puntaje.curso_id,))
        materia_nombre = cur.fetchone()["nombre"]
            
        # Verify point type is active
        cur.execute("SELECT id, nombre, descripcion, icono, color, estado FROM tipo_punto WHERE id = %s AND estado = 'activo'", (puntaje.tipo_punto_id,))
        tp = cur.fetchone()
        if not tp:
            raise HTTPException(status_code=404, detail="Tipo de punto no encontrado o inactivo")
            
        # Create points transaction
        cur.execute(
            """
            INSERT INTO puntaje (estudiante_id, tipo_punto_id, valor, origen, fecha)
            VALUES (%s, %s, %s, %s, NOW()) RETURNING id, estudiante_id, tipo_punto_id, valor, origen, fecha
            """,
            (
                puntaje.estudiante_id,
                tp["id"],
                puntaje.valor,
                f"Otorgado por Prof. {current_user['nombre']} en {materia_nombre}. Motivo: {puntaje.origen}",
            )
        )
        db_puntaje = cur.fetchone()
        
        # Update student total points cache
        cur.execute("UPDATE estudiante SET total_puntos = total_puntos + %s WHERE id = %s", (puntaje.valor, puntaje.estudiante_id))
        
    return {
        "id": db_puntaje["id"],
        "estudiante_id": db_puntaje["estudiante_id"],
        "valor": db_puntaje["valor"],
        "origen": db_puntaje["origen"],
        "fecha": db_puntaje["fecha"],
        "tipo_punto": {
            "id": tp["id"],
            "nombre": tp["nombre"],
            "descripcion": tp["descripcion"],
            "icono": tp["icono"],
            "color": tp["color"],
            "estado": tp["estado"]
        }
    }

# ==========================================
# 4. COMUNICADOS E INSTITUCIONALES (US-12)
# ==========================================

@router.get("/comunicados", response_model=List[AnuncioResponse], dependencies=[Depends(profesor_required)])
def ver_comunicados(conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute(
            """
            SELECT a.id, a.autor_id, a.titulo, a.contenido, a.rol_destinatario, a.curso_id, a.fecha_publicacion,
                   u.id AS user_id, u.email, u.nombre, u.rol, u.foto_url, u.created_at
            FROM anuncio a
            JOIN usuario u ON u.id = a.autor_id
            WHERE a.estado = 'publicado' AND (a.rol_destinatario = 'profesor' OR a.rol_destinatario IS NULL)
            ORDER BY a.fecha_publicacion DESC
            """
        )
        anuncios = cur.fetchall()
        
        results = []
        for row in anuncios:
            results.append({
                "id": row["id"],
                "autor_id": row["autor_id"],
                "titulo": row["titulo"],
                "contenido": row["contenido"],
                "rol_destinatario": row["rol_destinatario"],
                "curso_id": row["curso_id"],
                "fecha_publicacion": row["fecha_publicacion"],
                "autor": {
                    "id": row["user_id"],
                    "email": row["email"],
                    "nombre": row["nombre"],
                    "rol": row["rol"],
                    "foto_url": row["foto_url"],
                    "created_at": row["created_at"]
                }
            })

    return results

# ==========================================
# 5. TAREAS
# ==========================================

@router.post("/tareas", response_model=TareaResponse, dependencies=[Depends(profesor_required)])
def crear_tarea(tarea: TareaCreate, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        verify_profesor_teaches_course(cur, profesor_id, tarea.curso_id)

        cur.execute(
            """
            INSERT INTO tarea (curso_id, titulo, descripcion, fecha_entrega, estado)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, curso_id, titulo, descripcion, fecha_entrega, estado, created_at
            """,
            (tarea.curso_id, tarea.titulo, tarea.descripcion, tarea.fecha_entrega, tarea.estado)
        )
        db_tarea = cur.fetchone()

    return db_tarea

@router.get("/tareas", response_model=List[TareaResponse], dependencies=[Depends(profesor_required)])
def listar_tareas_curso(curso_id: int, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        verify_profesor_teaches_course(cur, profesor_id, curso_id)

        cur.execute(
            """
            SELECT id, curso_id, titulo, descripcion, fecha_entrega, estado, created_at
            FROM tarea WHERE curso_id = %s ORDER BY fecha_entrega
            """,
            (curso_id,)
        )
        rows = cur.fetchall()

    return rows

@router.put("/tareas/{tarea_id}", response_model=TareaResponse, dependencies=[Depends(profesor_required)])
def editar_tarea(tarea_id: int, tarea_data: TareaUpdate, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]

        cur.execute("SELECT id, curso_id FROM tarea WHERE id = %s", (tarea_id,))
        db_tarea = cur.fetchone()
        if not db_tarea:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        verify_profesor_teaches_course(cur, profesor_id, db_tarea["curso_id"])

        update_fields = []
        params = []
        for key, val in tarea_data.model_dump(exclude_unset=True).items():
            update_fields.append(f"{key} = %s")
            params.append(val)

        if update_fields:
            params.append(tarea_id)
            cur.execute(
                f"UPDATE tarea SET {', '.join(update_fields)} WHERE id = %s "
                "RETURNING id, curso_id, titulo, descripcion, fecha_entrega, estado, created_at",
                tuple(params)
            )
            row = cur.fetchone()
        else:
            cur.execute(
                "SELECT id, curso_id, titulo, descripcion, fecha_entrega, estado, created_at FROM tarea WHERE id = %s",
                (tarea_id,)
            )
            row = cur.fetchone()

    return row

@router.delete("/tareas/{tarea_id}", dependencies=[Depends(profesor_required)])
def eliminar_tarea(tarea_id: int, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]

        cur.execute("SELECT id, curso_id FROM tarea WHERE id = %s", (tarea_id,))
        db_tarea = cur.fetchone()
        if not db_tarea:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        verify_profesor_teaches_course(cur, profesor_id, db_tarea["curso_id"])

        cur.execute("DELETE FROM tarea WHERE id = %s", (tarea_id,))

    return {"message": "Tarea eliminada correctamente"}

# ==========================================
# 6. ASISTENCIA
# ==========================================

@router.post("/asistencia", response_model=List[AsistenciaResponse], dependencies=[Depends(profesor_required)])
def registrar_asistencia(asistencia: AsistenciaBulkCreate, current_user: dict = Depends(get_current_usuario), conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        verify_profesor_teaches_course(cur, profesor_id, asistencia.curso_id)

        resultados = []
        for registro in asistencia.registros:
            cur.execute(
                "SELECT id FROM inscripcion WHERE estudiante_id = %s AND curso_id = %s",
                (registro.estudiante_id, asistencia.curso_id)
            )
            insc = cur.fetchone()
            if not insc:
                raise HTTPException(
                    status_code=400,
                    detail=f"El estudiante {registro.estudiante_id} no está inscrito en este curso"
                )

            cur.execute(
                """
                INSERT INTO asistencia (inscripcion_id, fecha, estado)
                VALUES (%s, %s, %s)
                ON CONFLICT (inscripcion_id, fecha) DO UPDATE SET estado = EXCLUDED.estado
                RETURNING id, inscripcion_id, fecha, estado
                """,
                (insc["id"], asistencia.fecha, registro.estado)
            )
            db_asistencia = cur.fetchone()
            resultados.append({
                "id": db_asistencia["id"],
                "inscripcion_id": db_asistencia["inscripcion_id"],
                "estudiante_id": registro.estudiante_id,
                "fecha": db_asistencia["fecha"],
                "estado": db_asistencia["estado"]
            })

    return resultados

@router.get("/asistencia", response_model=List[AsistenciaResponse], dependencies=[Depends(profesor_required)])
def consultar_asistencia_curso(
    curso_id: int,
    fecha: Optional[date] = None,
    current_user: dict = Depends(get_current_usuario),
    conn = Depends(get_db)
):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM profesor WHERE usuario_id = %s", (current_user["id"],))
        profesor_id = cur.fetchone()["id"]
        verify_profesor_teaches_course(cur, profesor_id, curso_id)

        sql = """
            SELECT a.id, a.inscripcion_id, i.estudiante_id, a.fecha, a.estado
            FROM asistencia a
            JOIN inscripcion i ON i.id = a.inscripcion_id
            WHERE i.curso_id = %s
        """
        params = [curso_id]
        if fecha:
            sql += " AND a.fecha = %s"
            params.append(fecha)
        sql += " ORDER BY a.fecha DESC"

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

    return rows
