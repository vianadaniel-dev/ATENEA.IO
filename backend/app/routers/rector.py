from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime

from app.database import get_db, get_cursor
from app.models import RolUsuario
from app.schemas import (
    UsuarioResponse, EstudianteResponse, ProfesorResponse,
    EstudianteCreateRector, EstudianteUpdateRector, ProfesorCreateRector, ProfesorUpdateRector,
    CursoCreate, CursoUpdate, CursoResponse, MateriaResponse, HorarioResponse,
    AnuncioCreate, AnuncioResponse,
    TipoPuntoCreate, TipoPuntoResponse,
    RecompensaCreate, RecompensaResponse,
    CanjeResponse, CanjeEstadoUpdate,
    DashboardStats
)
from app.auth_utils import RoleChecker, get_password_hash

router = APIRouter()

# Dependency to check if current user is Rector
rector_required = RoleChecker(allowed_roles=["rector"])

# Helper function to check overlapping schedules
def check_schedule_overlap(cur, profesor_id: int, horarios_data: list, exclude_curso_id: Optional[int] = None) -> bool:
    if not profesor_id or not horarios_data:
        return False
    
    # Query schedules for all active courses of this professor
    sql = """
        SELECT h.dia_semana, h.hora_inicio, h.hora_fin 
        FROM horario h
        JOIN curso c ON c.id = h.curso_id
        WHERE c.profesor_id = %s AND c.estado = 'activo'
    """
    params = [profesor_id]
    if exclude_curso_id:
        sql += " AND c.id != %s"
        params.append(exclude_curso_id)
        
    cur.execute(sql, tuple(params))
    existing_horarios = cur.fetchall()
    
    for new_h in horarios_data:
        new_start = new_h.hora_inicio
        new_end = new_h.hora_fin
        
        # Convert time objects to strings for comparison if needed, or psycopg2 returns datetime.time objects
        for ext_h in existing_horarios:
            if new_h.dia_semana == ext_h["dia_semana"]:
                # Overlap condition: (StartA < EndB) and (EndA > StartB)
                if (new_start < ext_h["hora_fin"]) and (new_end > ext_h["hora_inicio"]):
                    return True
    return False

# Helper to fetch a single Course with nested details (Materia, Profesor, Horarios)
def fetch_curso_details(cur, curso_id: int) -> dict:
    cur.execute("""
        SELECT c.id, c.periodo, c.nombre_seccion, c.cupo_maximo, c.estado, c.sede_id,
               c.materia_id, m.nombre AS materia_nombre,
               c.profesor_id, p.especialidad AS prof_especialidad, p.estado AS prof_estado,
               pu.id AS prof_user_id, pu.email AS prof_email, pu.nombre AS prof_nombre, pu.rol AS prof_rol, pu.foto_url AS prof_foto, pu.created_at AS prof_created
        FROM curso c
        JOIN materia m ON m.id = c.materia_id
        LEFT JOIN profesor p ON p.id = c.profesor_id
        LEFT JOIN usuario pu ON pu.id = p.usuario_id
        WHERE c.id = %s
    """, (curso_id,))
    
    row = cur.fetchone()
    if not row:
        return None
        
    # Get schedules
    cur.execute(
        "SELECT id, dia_semana, hora_inicio, hora_fin, aula FROM horario WHERE curso_id = %s",
        (curso_id,)
    )
    horarios = cur.fetchall()
    
    # Structure nesting manually to match Pydantic CursoResponse schema
    materia_data = {
        "id": row["materia_id"],
        "nombre": row["materia_nombre"]
    }
    
    profesor_data = None
    if row["profesor_id"]:
        profesor_data = {
            "id": row["profesor_id"],
            "especialidad": row["prof_especialidad"],
            "estado": row["prof_estado"],
            "usuario": {
                "id": row["prof_user_id"],
                "email": row["prof_email"],
                "nombre": row["prof_nombre"],
                "rol": row["prof_rol"],
                "foto_url": row["prof_foto"],
                "created_at": row["prof_created"]
            }
        }
        
    horarios_data = [
        {
            "id": h["id"],
            "curso_id": curso_id,
            "dia_semana": h["dia_semana"],
            "hora_inicio": h["hora_inicio"],
            "hora_fin": h["hora_fin"],
            "aula": h["aula"]
        }
        for h in horarios
    ]
    
    return {
        "id": row["id"],
        "materia": materia_data,
        "profesor": profesor_data,
        "periodo": row["periodo"],
        "nombre_seccion": row["nombre_seccion"],
        "cupo_maximo": row["cupo_maximo"],
        "estado": row["estado"],
        "sede_id": row["sede_id"],
        "horarios": horarios_data
    }

# Helper to fetch Student details
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

# Helper to fetch Professor details
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
    return {
        "id": row["id"],
        "especialidad": row["especialidad"],
        "estado": row["estado"],
        "usuario": {
            "id": row["user_id"],
            "email": row["email"],
            "nombre": row["nombre"],
            "rol": row["rol"],
            "foto_url": row["foto_url"],
            "created_at": row["created_at"]
        }
    }

# ==========================================
# 1. GESTIÓN DE CURSOS (US-04)
# ==========================================

@router.post("/cursos", response_model=CursoResponse, dependencies=[Depends(rector_required)])
def crear_curso(curso_data: CursoCreate, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        # Verify materia exists
        cur.execute("SELECT id FROM materia WHERE id = %s", (curso_data.materia_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Materia no encontrada")
            
        # Verify professor exists and is active
        if curso_data.profesor_id:
            cur.execute("SELECT id FROM profesor WHERE id = %s AND estado = 'activo'", (curso_data.profesor_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Profesor no encontrado o inactivo")
                
            # Check schedule overlap
            if check_schedule_overlap(cur, curso_data.profesor_id, curso_data.horarios):
                raise HTTPException(
                    status_code=400,
                    detail="El profesor tiene un conflicto de horario (solapamiento)"
                )
                
        # Check unique constraint (materia, periodo, nombre_seccion)
        cur.execute(
            "SELECT id FROM curso WHERE materia_id = %s AND periodo = %s AND nombre_seccion = %s",
            (curso_data.materia_id, curso_data.periodo, curso_data.nombre_seccion)
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail="Ya existe este curso (misma materia, periodo y sección)"
            )

        # Create Curso
        cur.execute(
            """
            INSERT INTO curso (materia_id, profesor_id, periodo, nombre_seccion, cupo_maximo, estado, sede_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (
                curso_data.materia_id,
                curso_data.profesor_id,
                curso_data.periodo,
                curso_data.nombre_seccion,
                curso_data.cupo_maximo,
                curso_data.estado,
                curso_data.sede_id
            )
        )
        curso_id = cur.fetchone()["id"]

        # Add Horarios
        for h in curso_data.horarios:
            cur.execute(
                """
                INSERT INTO horario (curso_id, dia_semana, hora_inicio, hora_fin, aula)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (curso_id, h.dia_semana, h.hora_inicio, h.hora_fin, h.aula)
            )
            
        # Fetch complete course info
        course_details = fetch_curso_details(cur, curso_id)
        
    return course_details

@router.put("/cursos/{curso_id}", response_model=CursoResponse, dependencies=[Depends(rector_required)])
def actualizar_curso(curso_id: int, curso_data: CursoUpdate, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        # Check if course exists
        cur.execute("SELECT id, estado, profesor_id FROM curso WHERE id = %s", (curso_id,))
        existing_curso = cur.fetchone()
        if not existing_curso:
            raise HTTPException(status_code=404, detail="Curso no encontrado")

        # If deactivating, notify students
        deactivating = False
        if curso_data.estado == "inactivo" and existing_curso["estado"] == "activo":
            deactivating = True

        # Check schedule overlap
        profesor_id = curso_data.profesor_id if curso_data.profesor_id is not None else existing_curso["profesor_id"]
        
        if profesor_id and (curso_data.profesor_id is not None or curso_data.horarios is not None):
            # Check overlap
            check_list = curso_data.horarios
            if check_list is None:
                # Get current schedules
                cur.execute("SELECT dia_semana, hora_inicio, hora_fin, aula FROM horario WHERE curso_id = %s", (curso_id,))
                curr_horarios = cur.fetchall()
                class MockHorario:
                    def __init__(self, d, s, e, a):
                        self.dia_semana = d
                        self.hora_inicio = s
                        self.hora_fin = e
                        self.aula = a
                check_list = [MockHorario(h["dia_semana"], h["hora_inicio"], h["hora_fin"], h["aula"]) for h in curr_horarios]
                
            if check_schedule_overlap(cur, profesor_id, check_list, exclude_curso_id=curso_id):
                raise HTTPException(
                    status_code=400,
                    detail="Conflicto de horario para el profesor asignado"
                )

        # Build dynamic update statement for curso
        update_fields = []
        params = []
        for key, val in curso_data.model_dump(exclude_unset=True, exclude={"horarios"}).items():
            update_fields.append(f"{key} = %s")
            params.append(val)
            
        if update_fields:
            params.append(curso_id)
            cur.execute(
                f"UPDATE curso SET {', '.join(update_fields)} WHERE id = %s",
                tuple(params)
            )

        # Update schedules if provided
        if curso_data.horarios is not None:
            cur.execute("DELETE FROM horario WHERE curso_id = %s", (curso_id,))
            for h in curso_data.horarios:
                cur.execute(
                    """
                    INSERT INTO horario (curso_id, dia_semana, hora_inicio, hora_fin, aula)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (curso_id, h.dia_semana, h.hora_inicio, h.hora_fin, h.aula)
                )

        # Notify students if deactivated
        if deactivating:
            cur.execute("SELECT estudiante_id FROM inscripcion WHERE curso_id = %s", (curso_id,))
            enrollments = cur.fetchall()
            
            cur.execute("SELECT m.nombre FROM curso c JOIN materia m ON m.id = c.materia_id WHERE c.id = %s", (curso_id,))
            materia_nombre = cur.fetchone()["nombre"]
            
            for enc in enrollments:
                cur.execute(
                    """
                    INSERT INTO anuncio (autor_id, titulo, contenido, rol_destinatario, fecha_publicacion, estado)
                    VALUES (1, %s, %s, %s, %s, 'publicado')
                    """,
                    (
                        f"Curso desactivado: {materia_nombre}",
                        f"El curso {materia_nombre} ha sido desactivado.",
                        RolUsuario.estudiante.value,
                        datetime.now()
                    )
                )

        course_details = fetch_curso_details(cur, curso_id)
        
    return course_details

@router.delete("/cursos/{curso_id}", dependencies=[Depends(rector_required)])
def eliminar_curso(curso_id: int, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM curso WHERE id = %s", (curso_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Curso no encontrado")
            
        # Check if course has grades
        cur.execute(
            """
            SELECT c.id FROM calificacion c
            JOIN inscripcion i ON i.id = c.inscripcion_id
            WHERE i.curso_id = %s LIMIT 1
            """,
            (curso_id,)
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar un curso con calificaciones registradas. Debe desactivarlo."
            )

        # Delete schedules, enrollments, and course
        cur.execute("DELETE FROM horario WHERE curso_id = %s", (curso_id,))
        cur.execute("DELETE FROM inscripcion WHERE curso_id = %s", (curso_id,))
        cur.execute("DELETE FROM curso WHERE id = %s", (curso_id,))
        
    return {"message": "Curso eliminado correctamente"}

@router.get("/cursos", response_model=List[CursoResponse], dependencies=[Depends(rector_required)])
def listar_cursos(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1),
    conn = Depends(get_db)
):
    results = []
    with get_cursor(conn) as cur:
        offset = (page - 1) * limit
        cur.execute("SELECT id FROM curso ORDER BY id LIMIT %s OFFSET %s", (limit, offset))
        course_ids = [c["id"] for c in cur.fetchall()]
        for cid in course_ids:
            results.append(fetch_curso_details(cur, cid))
    return results

# ==========================================
# 2. GESTIÓN DE ESTUDIANTES (US-05)
# ==========================================

@router.post("/estudiantes", response_model=EstudianteResponse, dependencies=[Depends(rector_required)])
def crear_estudiante(data: EstudianteCreateRector, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        # Check if email is already taken
        cur.execute("SELECT id FROM usuario WHERE email = %s", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El correo ya está registrado")

        # Create Usuario
        cur.execute(
            """
            INSERT INTO usuario (email, nombre, password_hash, rol)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (data.email, data.nombre, get_password_hash(data.password_temporal), RolUsuario.estudiante.value)
        )
        user_id = cur.fetchone()["id"]

        # Create Estudiante Profile
        cur.execute(
            """
            INSERT INTO estudiante (usuario_id, fecha_nacimiento, estado, total_puntos)
            VALUES (%s, %s, 'activo', 0) RETURNING id
            """,
            (user_id, data.fecha_nacimiento)
        )
        estudiante_id = cur.fetchone()["id"]

        # Initial Course Assignment
        if data.curso_inicial_id:
            cur.execute("SELECT id, cupo_maximo FROM curso WHERE id = %s AND estado = 'activo'", (data.curso_inicial_id,))
            curso = cur.fetchone()
            if not curso:
                raise HTTPException(status_code=404, detail="Curso inicial no encontrado o inactivo")

            cur.execute("SELECT COUNT(*) FROM inscripcion WHERE curso_id = %s", (data.curso_inicial_id,))
            count = cur.fetchone()["count"]
            if count >= curso["cupo_maximo"]:
                raise HTTPException(status_code=400, detail="El curso seleccionado ya alcanzó su cupo máximo")

            cur.execute(
                "INSERT INTO inscripcion (estudiante_id, curso_id) VALUES (%s, %s)",
                (estudiante_id, data.curso_inicial_id)
            )

        details = fetch_estudiante_details(cur, estudiante_id)

    return details

@router.get("/estudiantes", response_model=List[EstudianteResponse], dependencies=[Depends(rector_required)])
def buscar_estudiantes(
    nombre: Optional[str] = None,
    curso_id: Optional[int] = None,
    estado: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1),
    conn = Depends(get_db)
):
    results = []
    with get_cursor(conn) as cur:
        # Build dynamic sql query
        sql = """
            SELECT DISTINCT e.id 
            FROM estudiante e
            JOIN usuario u ON u.id = e.usuario_id
        """
        where_clauses = []
        params = []
        
        if curso_id:
            sql += " JOIN inscripcion i ON i.estudiante_id = e.id "
            where_clauses.append("i.curso_id = %s")
            params.append(curso_id)
            
        if nombre:
            where_clauses.append("u.nombre ILIKE %s")
            params.append(f"%{nombre}%")
            
        if estado:
            where_clauses.append("e.estado = %s")
            params.append(estado)
            
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
            
        sql += " ORDER BY e.id"
        
        # Pagination
        offset = (page - 1) * limit
        sql += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(sql, tuple(params))
        estudiante_ids = [r["id"] for r in cur.fetchall()]
        
        for eid in estudiante_ids:
            results.append(fetch_estudiante_details(cur, eid))
            
    return results

@router.put("/estudiantes/{estudiante_id}", response_model=EstudianteResponse, dependencies=[Depends(rector_required)])
def actualizar_estudiante(estudiante_id: int, data: EstudianteUpdateRector, conn = Depends(get_db)):
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

        if data.estado:
            if data.estado in ["activo", "inactivo"]:
                cur.execute("UPDATE estudiante SET estado = %s WHERE id = %s", (data.estado, estudiante_id))
        if data.fecha_nacimiento:
            cur.execute("UPDATE estudiante SET fecha_nacimiento = %s WHERE id = %s", (data.fecha_nacimiento, estudiante_id))

        details = fetch_estudiante_details(cur, estudiante_id)

    return details

# ==========================================
# 3. GESTIÓN DE PROFESORES (US-06)
# ==========================================

@router.post("/profesores", response_model=ProfesorResponse, dependencies=[Depends(rector_required)])
def crear_profesor(data: ProfesorCreateRector, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM usuario WHERE email = %s", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El correo ya está en uso")

        cur.execute(
            """
            INSERT INTO usuario (email, nombre, password_hash, rol)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (data.email, data.nombre, get_password_hash(data.password_temporal), RolUsuario.profesor.value)
        )
        user_id = cur.fetchone()["id"]

        cur.execute(
            """
            INSERT INTO profesor (usuario_id, especialidad, estado)
            VALUES (%s, %s, 'activo') RETURNING id
            """,
            (user_id, data.especialidad)
        )
        profesor_id = cur.fetchone()["id"]

        details = fetch_profesor_details(cur, profesor_id)

    return details

@router.put("/profesores/{profesor_id}", response_model=ProfesorResponse, dependencies=[Depends(rector_required)])
def actualizar_profesor(profesor_id: int, data: ProfesorUpdateRector, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id, usuario_id FROM profesor WHERE id = %s", (profesor_id,))
        prof = cur.fetchone()
        if not prof:
            raise HTTPException(status_code=404, detail="Profesor no encontrado")

        user_id = prof["usuario_id"]

        if data.nombre:
            cur.execute("UPDATE usuario SET nombre = %s WHERE id = %s", (data.nombre, user_id))
        if data.email:
            cur.execute("SELECT id FROM usuario WHERE email = %s AND id != %s", (data.email, user_id))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="El correo ya está en uso")
            cur.execute("UPDATE usuario SET email = %s WHERE id = %s", (data.email, user_id))

        if data.especialidad:
            cur.execute("UPDATE profesor SET especialidad = %s WHERE id = %s", (data.especialidad, profesor_id))

        if data.estado:
            if data.estado == "inactivo":
                # Ensure no active courses
                cur.execute("SELECT id FROM curso WHERE profesor_id = %s AND estado = 'activo' LIMIT 1", (profesor_id,))
                if cur.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail="No se puede desactivar un profesor con cursos activos asignados. Reasigne los cursos primero."
                    )
            if data.estado in ["activo", "inactivo"]:
                cur.execute("UPDATE profesor SET estado = %s WHERE id = %s", (data.estado, profesor_id))

        details = fetch_profesor_details(cur, profesor_id)

    return details

@router.get("/profesores", response_model=List[ProfesorResponse], dependencies=[Depends(rector_required)])
def listar_profesores(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1),
    conn = Depends(get_db)
):
    results = []
    with get_cursor(conn) as cur:
        offset = (page - 1) * limit
        cur.execute("SELECT id FROM profesor ORDER BY id LIMIT %s OFFSET %s", (limit, offset))
        prof_ids = [p["id"] for p in cur.fetchall()]
        for pid in prof_ids:
            results.append(fetch_profesor_details(cur, pid))
    return results

# ==========================================
# 4. GESTIÓN DE ANUNCIOS (US-03)
# ==========================================

@router.post("/anuncios", response_model=AnuncioResponse)
def crear_anuncio(
    anuncio: AnuncioCreate,
    current_rector: dict = Depends(rector_required),
    conn = Depends(get_db)
):
    with get_cursor(conn) as cur:
        cur.execute(
            """
            INSERT INTO anuncio (autor_id, titulo, contenido, rol_destinatario, curso_id, estado, fecha_publicacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (
                current_rector["id"],
                anuncio.titulo,
                anuncio.contenido,
                anuncio.rol_destinatario.value if anuncio.rol_destinatario else None,
                anuncio.curso_id,
                anuncio.estado,
                datetime.now()
            )
        )
        anuncio_id = cur.fetchone()["id"]
        
        cur.execute("""
            SELECT a.id, a.autor_id, a.titulo, a.contenido, a.rol_destinatario, a.curso_id, a.estado, a.fecha_publicacion,
                   u.id AS user_id, u.email, u.nombre, u.rol, u.foto_url, u.created_at
            FROM anuncio a
            JOIN usuario u ON u.id = a.autor_id
            WHERE a.id = %s
        """, (anuncio_id,))
        row = cur.fetchone()
        
    return {
        "id": row["id"],
        "autor_id": row["autor_id"],
        "titulo": row["titulo"],
        "contenido": row["contenido"],
        "rol_destinatario": row["rol_destinatario"],
        "curso_id": row["curso_id"],
        "estado": row["estado"],
        "fecha_publicacion": row["fecha_publicacion"],
        "autor": {
            "id": row["user_id"],
            "email": row["email"],
            "nombre": row["nombre"],
            "rol": row["rol"],
            "foto_url": row["foto_url"],
            "created_at": row["created_at"]
        }
    }

@router.put("/anuncios/{anuncio_id}", response_model=AnuncioResponse, dependencies=[Depends(rector_required)])
def actualizar_anuncio(anuncio_id: int, anuncio_data: AnuncioCreate, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM anuncio WHERE id = %s", (anuncio_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Anuncio no encontrado")
            
        cur.execute(
            """
            UPDATE anuncio 
            SET titulo = %s, contenido = %s, rol_destinatario = %s, curso_id = %s, estado = %s
            WHERE id = %s
            """,
            (
                anuncio_data.titulo,
                anuncio_data.contenido,
                anuncio_data.rol_destinatario.value if anuncio_data.rol_destinatario else None,
                anuncio_data.curso_id,
                anuncio_data.estado,
                anuncio_id
            )
        )
        
        cur.execute("""
            SELECT a.id, a.autor_id, a.titulo, a.contenido, a.rol_destinatario, a.curso_id, a.estado, a.fecha_publicacion,
                   u.id AS user_id, u.email, u.nombre, u.rol, u.foto_url, u.created_at
            FROM anuncio a
            JOIN usuario u ON u.id = a.autor_id
            WHERE a.id = %s
        """, (anuncio_id,))
        row = cur.fetchone()
        
    return {
        "id": row["id"],
        "autor_id": row["autor_id"],
        "titulo": row["titulo"],
        "contenido": row["contenido"],
        "rol_destinatario": row["rol_destinatario"],
        "curso_id": row["curso_id"],
        "estado": row["estado"],
        "fecha_publicacion": row["fecha_publicacion"],
        "autor": {
            "id": row["user_id"],
            "email": row["email"],
            "nombre": row["nombre"],
            "rol": row["rol"],
            "foto_url": row["foto_url"],
            "created_at": row["created_at"]
        }
    }

@router.delete("/anuncios/{anuncio_id}", dependencies=[Depends(rector_required)])
def eliminar_anuncio(anuncio_id: int, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM anuncio WHERE id = %s", (anuncio_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Anuncio no encontrado")
        cur.execute("DELETE FROM anuncio WHERE id = %s", (anuncio_id,))
    return {"message": "Anuncio eliminado correctamente"}

# ==========================================
# 5. CONFIGURACIÓN DE PUNTOS (US-08)
# ==========================================

@router.get("/tipos-puntos", response_model=List[TipoPuntoResponse], dependencies=[Depends(rector_required)])
def listar_tipos_puntos(conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id, nombre, descripcion, icono, color, estado FROM tipo_punto ORDER BY id")
        rows = cur.fetchall()
    return rows

@router.post("/tipos-puntos", response_model=TipoPuntoResponse, dependencies=[Depends(rector_required)])
def crear_tipo_punto(tipo: TipoPuntoCreate, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        # Check uniqueness of name
        cur.execute("SELECT id FROM tipo_punto WHERE nombre = %s", (tipo.nombre,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El nombre del tipo de punto ya existe")
            
        cur.execute(
            """
            INSERT INTO tipo_punto (nombre, descripcion, icono, color, estado)
            VALUES (%s, %s, %s, %s, %s) RETURNING id, nombre, descripcion, icono, color, estado
            """,
            (tipo.nombre, tipo.descripcion, tipo.icono, tipo.color, tipo.estado)
        )
        row = cur.fetchone()
    return row

@router.put("/tipos-puntos/{tipo_id}", response_model=TipoPuntoResponse, dependencies=[Depends(rector_required)])
def actualizar_tipo_punto(tipo_id: int, tipo_data: TipoPuntoCreate, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM tipo_punto WHERE id = %s", (tipo_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Tipo de punto no encontrado")
            
        cur.execute(
            """
            UPDATE tipo_punto 
            SET nombre = %s, descripcion = %s, icono = %s, color = %s, estado = %s
            WHERE id = %s RETURNING id, nombre, descripcion, icono, color, estado
            """,
            (tipo_data.nombre, tipo_data.descripcion, tipo_data.icono, tipo_data.color, tipo_data.estado, tipo_id)
        )
        row = cur.fetchone()
    return row

# ==========================================
# 6. DASHBOARD DE ESTADÍSTICAS (US-07)
# ==========================================

@router.get("/dashboard/stats", response_model=DashboardStats, dependencies=[Depends(rector_required)])
def obtener_estadisticas_dashboard(periodo: str, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        # 1. GPA per Course and Period
        cur.execute(
            """
            SELECT c.id AS curso_id, m.nombre AS materia_nombre, c.nombre_seccion AS seccion, AVG(cal.valor) AS promedio
            FROM curso c
            JOIN materia m ON m.id = c.materia_id
            JOIN inscripcion i ON i.curso_id = c.id
            JOIN calificacion cal ON cal.inscripcion_id = i.id
            WHERE c.periodo = %s AND cal.estado = 'publicada'
            GROUP BY c.id, m.nombre, c.nombre_seccion
            """,
            (periodo,)
        )
        gpa_query = cur.fetchall()
        
        promedios = [
            {
                "curso_id": r["curso_id"],
                "materia": r["materia_nombre"],
                "seccion": r["seccion"],
                "promedio": float(round(r["promedio"], 2)) if r["promedio"] else 0.0
            }
            for r in gpa_query
        ]
        
        # 2. Number of active/inactive students
        cur.execute("SELECT COUNT(*) FROM estudiante WHERE estado = 'activo'")
        activos = cur.fetchone()["count"]
        
        cur.execute("SELECT COUNT(*) FROM estudiante WHERE estado != 'activo'")
        inactivos = cur.fetchone()["count"]
        
        # 3. Top 5 students in points
        cur.execute(
            """
            SELECT e.id AS estudiante_id, u.nombre, e.total_puntos AS puntos
            FROM estudiante e
            JOIN usuario u ON u.id = e.usuario_id
            ORDER BY e.total_puntos DESC LIMIT 5
            """
        )
        top_query = cur.fetchall()
        
        top_students = [
            {
                "estudiante_id": r["estudiante_id"],
                "nombre": r["nombre"],
                "puntos": r["puntos"]
            }
            for r in top_query
        ]
        
    return {
        "promedio_general_por_curso": promedios,
        "total_estudiantes_activos": activos,
        "total_estudiantes_inactivos": inactivos,
        "top_gamificacion": top_students
    }

# ==========================================
# 7. CATÁLOGO DE RECOMPENSAS (US-16)
# ==========================================

# Helper to fetch a Recompensa with nested TipoPunto details
def fetch_recompensa_details(cur, recompensa_id: int) -> dict:
    cur.execute("""
        SELECT r.id, r.nombre, r.costo_puntos, r.tipo_punto_id, r.descripcion, r.estado, r.created_at,
               tp.id AS tp_id, tp.nombre AS tp_nombre, tp.descripcion AS tp_desc, tp.icono, tp.color, tp.estado AS tp_estado
        FROM recompensa r
        JOIN tipo_punto tp ON tp.id = r.tipo_punto_id
        WHERE r.id = %s
    """, (recompensa_id,))
    row = cur.fetchone()
    if not row:
        return None
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

@router.get("/recompensas", response_model=List[RecompensaResponse], dependencies=[Depends(rector_required)])
def listar_recompensas(conn = Depends(get_db)):
    results = []
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM recompensa ORDER BY id")
        recompensa_ids = [r["id"] for r in cur.fetchall()]
        for rid in recompensa_ids:
            results.append(fetch_recompensa_details(cur, rid))
    return results

@router.post("/recompensas", response_model=RecompensaResponse, dependencies=[Depends(rector_required)])
def crear_recompensa(recompensa: RecompensaCreate, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM tipo_punto WHERE id = %s", (recompensa.tipo_punto_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Tipo de punto no encontrado")

        cur.execute(
            """
            INSERT INTO recompensa (nombre, costo_puntos, tipo_punto_id, descripcion, estado)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
            (recompensa.nombre, recompensa.costo_puntos, recompensa.tipo_punto_id, recompensa.descripcion, recompensa.estado)
        )
        recompensa_id = cur.fetchone()["id"]
        details = fetch_recompensa_details(cur, recompensa_id)

    return details

@router.put("/recompensas/{recompensa_id}", response_model=RecompensaResponse, dependencies=[Depends(rector_required)])
def actualizar_recompensa(recompensa_id: int, recompensa_data: RecompensaCreate, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id FROM recompensa WHERE id = %s", (recompensa_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Recompensa no encontrada")

        cur.execute("SELECT id FROM tipo_punto WHERE id = %s", (recompensa_data.tipo_punto_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Tipo de punto no encontrado")

        cur.execute(
            """
            UPDATE recompensa
            SET nombre = %s, costo_puntos = %s, tipo_punto_id = %s, descripcion = %s, estado = %s
            WHERE id = %s
            """,
            (
                recompensa_data.nombre, recompensa_data.costo_puntos, recompensa_data.tipo_punto_id,
                recompensa_data.descripcion, recompensa_data.estado, recompensa_id
            )
        )
        details = fetch_recompensa_details(cur, recompensa_id)

    return details

# ==========================================
# 8. APROBACIÓN DE CANJES (US-16)
# ==========================================

# Helper to fetch a Canje with nested Recompensa + TipoPunto details
def fetch_canje_details(cur, canje_id: int) -> dict:
    cur.execute("""
        SELECT c.id, c.estudiante_id, c.puntos_usados, c.estado, c.created_at,
               r.id AS rec_id, r.nombre AS rec_nombre, r.costo_puntos, r.tipo_punto_id, r.descripcion AS rec_desc,
               r.estado AS rec_estado, r.created_at AS rec_created,
               tp.id AS tp_id, tp.nombre AS tp_nombre, tp.descripcion AS tp_desc, tp.icono, tp.color, tp.estado AS tp_estado
        FROM canje c
        JOIN recompensa r ON r.id = c.recompensa_id
        JOIN tipo_punto tp ON tp.id = r.tipo_punto_id
        WHERE c.id = %s
    """, (canje_id,))
    row = cur.fetchone()
    if not row:
        return None
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
            "descripcion": row["rec_desc"],
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

@router.get("/canjes", response_model=List[CanjeResponse], dependencies=[Depends(rector_required)])
def listar_canjes(estado: Optional[str] = None, conn = Depends(get_db)):
    results = []
    with get_cursor(conn) as cur:
        sql = "SELECT id FROM canje"
        params = []
        if estado:
            sql += " WHERE estado = %s"
            params.append(estado)
        sql += " ORDER BY created_at DESC"
        cur.execute(sql, tuple(params))
        canje_ids = [r["id"] for r in cur.fetchall()]
        for cid in canje_ids:
            results.append(fetch_canje_details(cur, cid))
    return results

@router.put("/canjes/{canje_id}", response_model=CanjeResponse, dependencies=[Depends(rector_required)])
def resolver_canje(canje_id: int, resolucion: CanjeEstadoUpdate, conn = Depends(get_db)):
    with get_cursor(conn) as cur:
        cur.execute("SELECT id, estado FROM canje WHERE id = %s", (canje_id,))
        canje = cur.fetchone()
        if not canje:
            raise HTTPException(status_code=404, detail="Canje no encontrado")

        if canje["estado"] != "pendiente":
            raise HTTPException(status_code=400, detail="Este canje ya fue resuelto")

        cur.execute("UPDATE canje SET estado = %s WHERE id = %s", (resolucion.estado, canje_id))
        details = fetch_canje_details(cur, canje_id)

    return details

# ==========================================
# 9. AUDITORÍA DE PUNTOS OTORGADOS (US-11)
# ==========================================

@router.get("/puntajes", dependencies=[Depends(rector_required)])
def auditar_puntajes(
    estudiante_id: Optional[int] = None,
    curso_id: Optional[int] = None,
    tipo_punto_id: Optional[int] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1),
    conn = Depends(get_db)
):
    with get_cursor(conn) as cur:
        sql = """
            SELECT p.id, p.estudiante_id, u.nombre AS estudiante_nombre,
                   p.tipo_punto_id, tp.nombre AS tipo_punto_nombre,
                   p.valor, p.origen, p.fecha
            FROM puntaje p
            JOIN estudiante e ON e.id = p.estudiante_id
            JOIN usuario u ON u.id = e.usuario_id
            JOIN tipo_punto tp ON tp.id = p.tipo_punto_id
        """
        where_clauses = []
        params = []

        if estudiante_id:
            where_clauses.append("p.estudiante_id = %s")
            params.append(estudiante_id)
        if tipo_punto_id:
            where_clauses.append("p.tipo_punto_id = %s")
            params.append(tipo_punto_id)
        if curso_id:
            where_clauses.append(
                "EXISTS (SELECT 1 FROM inscripcion i WHERE i.estudiante_id = p.estudiante_id AND i.curso_id = %s)"
            )
            params.append(curso_id)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY p.fecha DESC LIMIT %s OFFSET %s"
        offset = (page - 1) * limit
        params.extend([limit, offset])

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "estudiante_id": r["estudiante_id"],
            "estudiante_nombre": r["estudiante_nombre"],
            "tipo_punto_id": r["tipo_punto_id"],
            "tipo_punto_nombre": r["tipo_punto_nombre"],
            "valor": r["valor"],
            "motivo": r["origen"],
            "fecha": str(r["fecha"])
        }
        for r in rows
    ]
