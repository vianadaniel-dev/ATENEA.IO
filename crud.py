"""SQL queries (CRUD).

This module contains only parameterized SQL statements. It does not validate
data, apply business rules, or decide HTTP error codes: that belongs in
services.py.

All functions receive an already-open cursor (`cur`) and return rows
as dictionaries or None.
"""

from typing import Any, Dict, List, Optional

Row = Dict[str, Any]

# Reusable expression for the visible course name.
# In this schema a course is (subject + teacher + term + section).
_CURSO_NOMBRE = "m.nombre || COALESCE(' - ' || c.nombre_seccion, '')"


# ============================ USUARIOS ============================

def insert_usuario(cur, email: str, password_hash: str, nombre: str, rol: str) -> Row:
    cur.execute(
        """
        INSERT INTO usuario (email, password_hash, nombre, rol)
        VALUES (%s, %s, %s, %s)
        RETURNING id, email, nombre, rol, created_at
        """,
        (email, password_hash, nombre, rol),
    )
    return cur.fetchone()


def select_usuario_by_id(cur, usuario_id: int) -> Optional[Row]:
    cur.execute(
        "SELECT id, email, nombre, rol, created_at FROM usuario WHERE id = %s",
        (usuario_id,),
    )
    return cur.fetchone()


def select_usuario_by_email(cur, email: str) -> Optional[Row]:
    cur.execute(
        """
        SELECT id, email, password_hash, nombre, rol, created_at
        FROM usuario
        WHERE email = %s
        """,
        (email,),
    )
    return cur.fetchone()


def select_usuario_id_by_email(cur, email: str, excluir_id: Optional[int] = None) -> Optional[Row]:
    cur.execute(
        """
        SELECT id FROM usuario
        WHERE email = %s AND (%s::int IS NULL OR id <> %s::int)
        """,
        (email, excluir_id, excluir_id),
    )
    return cur.fetchone()


def update_usuario_nombre(cur, usuario_id: int, nombre: str) -> Optional[Row]:
    cur.execute(
        """
        UPDATE usuario SET nombre = %s
        WHERE id = %s
        RETURNING id, email, nombre, rol, created_at
        """,
        (nombre, usuario_id),
    )
    return cur.fetchone()


def update_usuario_perfil(
    cur, usuario_id: int, nombre: Optional[str], email: Optional[str]
) -> Optional[Row]:
    """Actualiza solo los campos recibidos; COALESCE ignora los None."""
    cur.execute(
        """
        UPDATE usuario
        SET nombre = COALESCE(%s, nombre),
            email  = COALESCE(%s, email)
        WHERE id = %s
        RETURNING id, email, nombre, rol, created_at
        """,
        (nombre, email, usuario_id),
    )
    return cur.fetchone()


def delete_usuario(cur, usuario_id: int) -> Optional[Row]:
    cur.execute("DELETE FROM usuario WHERE id = %s RETURNING id", (usuario_id,))
    return cur.fetchone()


# ============================ ESTUDIANTE / PROFESOR ============================

def insert_estudiante(cur, usuario_id: int, fecha_nacimiento=None) -> Row:
    cur.execute(
        """
        INSERT INTO estudiante (usuario_id, fecha_nacimiento)
        VALUES (%s, %s)
        RETURNING id, usuario_id, fecha_nacimiento, estado
        """,
        (usuario_id, fecha_nacimiento),
    )
    return cur.fetchone()


def insert_profesor(cur, usuario_id: int, especialidad: Optional[str] = None) -> Row:
    cur.execute(
        """
        INSERT INTO profesor (usuario_id, especialidad)
        VALUES (%s, %s)
        RETURNING id, usuario_id, especialidad
        """,
        (usuario_id, especialidad),
    )
    return cur.fetchone()


def select_estudiante_by_id(cur, estudiante_id: int) -> Optional[Row]:
    cur.execute(
        """
        SELECT e.id, e.usuario_id, e.fecha_nacimiento, e.estado,
               u.email, u.nombre, u.rol, u.created_at
        FROM estudiante e
        JOIN usuario u ON u.id = e.usuario_id
        WHERE e.id = %s
        """,
        (estudiante_id,),
    )
    return cur.fetchone()


def select_estudiante_by_usuario_id(cur, usuario_id: int) -> Optional[Row]:
    cur.execute(
        """
        SELECT e.id, e.usuario_id, e.fecha_nacimiento, e.estado,
               u.email, u.nombre, u.rol
        FROM estudiante e
        JOIN usuario u ON u.id = e.usuario_id
        WHERE e.usuario_id = %s
        """,
        (usuario_id,),
    )
    return cur.fetchone()


def update_estudiante_perfil(
    cur, estudiante_id: int, fecha_nacimiento=None, estado: Optional[str] = None
) -> Optional[Row]:
    cur.execute(
        """
        UPDATE estudiante
        SET fecha_nacimiento = COALESCE(%s, fecha_nacimiento),
            estado           = COALESCE(%s, estado)
        WHERE id = %s
        RETURNING id, usuario_id, fecha_nacimiento, estado
        """,
        (fecha_nacimiento, estado, estudiante_id),
    )
    return cur.fetchone()


def lock_estudiante(cur, estudiante_id: int) -> Optional[Row]:
    """Bloquea la fila del estudiante hasta el fin de la transaccion.

    Serializa operaciones concurrentes sobre su saldo de puntos.
    """
    cur.execute("SELECT id FROM estudiante WHERE id = %s FOR UPDATE", (estudiante_id,))
    return cur.fetchone()


# ============================ CURSOS ============================

def select_curso_by_id(cur, curso_id: int) -> Optional[Row]:
    cur.execute(
        f"""
        SELECT c.id, c.materia_id, c.profesor_id, c.periodo, c.nombre_seccion,
               m.nombre AS materia, {_CURSO_NOMBRE} AS curso,
               up.nombre AS profesor
        FROM curso c
        JOIN materia m ON m.id = c.materia_id
        LEFT JOIN profesor p ON p.id = c.profesor_id
        LEFT JOIN usuario up ON up.id = p.usuario_id
        WHERE c.id = %s
        """,
        (curso_id,),
    )
    return cur.fetchone()


def select_cursos_by_periodo_seccion(
    cur, periodo: str, nombre_seccion: Optional[str]
) -> List[Row]:
    """Todos los cursos (materias) que componen una seccion de un periodo.

    Es la base de la asignacion automatica al inscribir un estudiante.
    """
    cur.execute(
        f"""
        SELECT c.id, c.materia_id, c.periodo, c.nombre_seccion,
               m.nombre AS materia, {_CURSO_NOMBRE} AS curso
        FROM curso c
        JOIN materia m ON m.id = c.materia_id
        WHERE c.periodo = %s
          AND c.nombre_seccion IS NOT DISTINCT FROM %s
        ORDER BY m.nombre
        """,
        (periodo, nombre_seccion),
    )
    return cur.fetchall()


def select_cursos_by_estudiante(cur, estudiante_id: int, periodo: Optional[str] = None) -> List[Row]:
    cur.execute(
        f"""
        SELECT c.id AS curso_id, m.nombre AS materia, {_CURSO_NOMBRE} AS curso,
               c.periodo, c.nombre_seccion, up.nombre AS profesor,
               i.id AS inscripcion_id, i.fecha_inscripcion
        FROM inscripcion i
        JOIN curso c ON c.id = i.curso_id
        JOIN materia m ON m.id = c.materia_id
        LEFT JOIN profesor p ON p.id = c.profesor_id
        LEFT JOIN usuario up ON up.id = p.usuario_id
        WHERE i.estudiante_id = %s
          AND (%s::varchar IS NULL OR c.periodo = %s::varchar)
        ORDER BY c.periodo DESC, m.nombre
        """,
        (estudiante_id, periodo, periodo),
    )
    return cur.fetchall()


# ============================ INSCRIPCIONES ============================

def insert_inscripcion(cur, estudiante_id: int, curso_id: int) -> Optional[Row]:
    """Crea la inscripcion. Si ya existe no hace nada y devuelve None."""
    cur.execute(
        """
        INSERT INTO inscripcion (estudiante_id, curso_id)
        VALUES (%s, %s)
        ON CONFLICT (estudiante_id, curso_id) DO NOTHING
        RETURNING id, estudiante_id, curso_id, fecha_inscripcion
        """,
        (estudiante_id, curso_id),
    )
    return cur.fetchone()


def select_inscripcion(cur, estudiante_id: int, curso_id: int) -> Optional[Row]:
    cur.execute(
        """
        SELECT id, estudiante_id, curso_id, fecha_inscripcion
        FROM inscripcion
        WHERE estudiante_id = %s AND curso_id = %s
        """,
        (estudiante_id, curso_id),
    )
    return cur.fetchone()


def delete_inscripcion(cur, inscripcion_id: int) -> Optional[Row]:
    cur.execute("DELETE FROM inscripcion WHERE id = %s RETURNING id", (inscripcion_id,))
    return cur.fetchone()


# ============================ PUNTOS ============================

def select_tipo_punto_by_nombre(cur, nombre: str) -> Optional[Row]:
    cur.execute("SELECT id, nombre, descripcion FROM tipo_punto WHERE nombre = %s", (nombre,))
    return cur.fetchone()


def select_tipos_punto(cur) -> List[Row]:
    cur.execute("SELECT id, nombre, descripcion FROM tipo_punto ORDER BY nombre")
    return cur.fetchall()


def insert_puntaje(
    cur, estudiante_id: int, tipo_punto_id: int, valor: int, origen: Optional[str]
) -> Row:
    """Registra un movimiento en el historial de puntos (libro append-only)."""
    cur.execute(
        """
        INSERT INTO puntaje (estudiante_id, tipo_punto_id, valor, origen)
        VALUES (%s, %s, %s, %s)
        RETURNING id, estudiante_id, tipo_punto_id, valor, origen, fecha
        """,
        (estudiante_id, tipo_punto_id, valor, origen),
    )
    return cur.fetchone()


def select_totales_puntos(cur, estudiante_id: int) -> Row:
    """Puntos ganados y gastados. El saldo lo calcula services.py."""
    cur.execute(
        """
        SELECT
            COALESCE((SELECT SUM(valor) FROM puntaje WHERE estudiante_id = %s), 0)
                AS puntos_ganados,
            COALESCE((SELECT SUM(puntos_gastados) FROM canje
                      WHERE estudiante_id = %s AND estado <> 'cancelado'), 0)
                AS puntos_gastados
        """,
        (estudiante_id, estudiante_id),
    )
    return cur.fetchone()


def select_historial_puntos(
    cur, estudiante_id: int, limit: int, offset: int
) -> List[Row]:
    cur.execute(
        """
        SELECT p.id, p.valor, p.origen, p.fecha, tp.nombre AS tipo_punto
        FROM puntaje p
        JOIN tipo_punto tp ON tp.id = p.tipo_punto_id
        WHERE p.estudiante_id = %s
        ORDER BY p.fecha DESC, p.id DESC
        LIMIT %s OFFSET %s
        """,
        (estudiante_id, limit, offset),
    )
    return cur.fetchall()


# ============================ CANJE DE PUNTOS ============================

def select_recompensa_by_id(cur, recompensa_id: int) -> Optional[Row]:
    cur.execute(
        """
        SELECT id, nombre, descripcion, costo_puntos, stock, activo
        FROM recompensa
        WHERE id = %s
        FOR UPDATE
        """,
        (recompensa_id,),
    )
    return cur.fetchone()


def select_recompensas_activas(cur, limit: int, offset: int) -> List[Row]:
    cur.execute(
        """
        SELECT id, nombre, descripcion, costo_puntos, stock, activo
        FROM recompensa
        WHERE activo = TRUE
        ORDER BY costo_puntos ASC, nombre ASC
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )
    return cur.fetchall()


def update_recompensa_stock(cur, recompensa_id: int, cantidad: int) -> Optional[Row]:
    """Descuenta stock solo si hay existencias. Devuelve None si no alcanza."""
    cur.execute(
        """
        UPDATE recompensa
        SET stock = stock - %s
        WHERE id = %s AND (stock IS NULL OR stock >= %s)
        RETURNING id, stock
        """,
        (cantidad, recompensa_id, cantidad),
    )
    return cur.fetchone()


def insert_canje(
    cur, estudiante_id: int, recompensa_id: int, puntos_gastados: int
) -> Row:
    cur.execute(
        """
        INSERT INTO canje (estudiante_id, recompensa_id, puntos_gastados)
        VALUES (%s, %s, %s)
        RETURNING id, estudiante_id, recompensa_id, puntos_gastados, estado, fecha
        """,
        (estudiante_id, recompensa_id, puntos_gastados),
    )
    return cur.fetchone()


def select_canjes_by_estudiante(cur, estudiante_id: int, limit: int, offset: int) -> List[Row]:
    cur.execute(
        """
        SELECT ca.id, ca.puntos_gastados, ca.estado, ca.fecha,
               r.nombre AS recompensa, r.descripcion
        FROM canje ca
        JOIN recompensa r ON r.id = ca.recompensa_id
        WHERE ca.estudiante_id = %s
        ORDER BY ca.fecha DESC, ca.id DESC
        LIMIT %s OFFSET %s
        """,
        (estudiante_id, limit, offset),
    )
    return cur.fetchall()


# ============================ TRANSCRIPCION / GPA ============================

def select_calificaciones_publicadas(
    cur, estudiante_id: int, periodo: Optional[str] = None
) -> List[Row]:
    """Solo calificaciones 'published' del estudiante indicado."""
    cur.execute(
        f"""
        SELECT cal.id, cal.tipo_evaluacion, cal.valor, cal.fecha,
               c.periodo, m.nombre AS materia, {_CURSO_NOMBRE} AS curso,
               COALESCE(up.nombre, 'Por asignar') AS profesor
        FROM calificacion cal
        JOIN inscripcion i ON i.id = cal.inscripcion_id
        JOIN curso c ON c.id = i.curso_id
        JOIN materia m ON m.id = c.materia_id
        LEFT JOIN profesor p ON p.id = c.profesor_id
        LEFT JOIN usuario up ON up.id = p.usuario_id
        WHERE i.estudiante_id = %s
          AND cal.estado = 'published'
          AND (%s::varchar IS NULL OR c.periodo = %s::varchar)
        ORDER BY c.periodo DESC, m.nombre ASC, cal.fecha ASC
        """,
        (estudiante_id, periodo, periodo),
    )
    return cur.fetchall()


def select_gpa(cur, estudiante_id: int, periodo: Optional[str] = None) -> Row:
    """GPA calculado en el servidor sobre calificaciones publicadas."""
    cur.execute(
        """
        SELECT ROUND(AVG(cal.valor), 2) AS gpa,
               COUNT(*) AS total_calificaciones
        FROM calificacion cal
        JOIN inscripcion i ON i.id = cal.inscripcion_id
        JOIN curso c ON c.id = i.curso_id
        WHERE i.estudiante_id = %s
          AND cal.estado = 'published'
          AND (%s::varchar IS NULL OR c.periodo = %s::varchar)
        """,
        (estudiante_id, periodo, periodo),
    )
    return cur.fetchone()


def select_periodos_by_estudiante(cur, estudiante_id: int) -> List[Row]:
    cur.execute(
        """
        SELECT DISTINCT c.periodo
        FROM inscripcion i
        JOIN curso c ON c.id = i.curso_id
        WHERE i.estudiante_id = %s
        ORDER BY c.periodo DESC
        """,
        (estudiante_id,),
    )
    return cur.fetchall()


# ============================ LEADERBOARD ============================

def select_leaderboard_por_curso(
    cur, curso_id: int, tipo_punto_id: Optional[int], limit: int, offset: int
) -> List[Row]:
    """Ranking de los estudiantes inscritos en un curso.

    El calculo (SUM + DENSE_RANK) ocurre integramente en PostgreSQL. No se
    expone el saldo de puntos: solo posicion, nombre y curso.
    """
    cur.execute(
        f"""
        SELECT posicion, nombre, curso
        FROM (
            SELECT
                DENSE_RANK() OVER (ORDER BY COALESCE(SUM(p.valor), 0) DESC) AS posicion,
                u.nombre AS nombre,
                {_CURSO_NOMBRE} AS curso
            FROM inscripcion i
            JOIN curso c      ON c.id = i.curso_id
            JOIN materia m    ON m.id = c.materia_id
            JOIN estudiante e ON e.id = i.estudiante_id
            JOIN usuario u    ON u.id = e.usuario_id
            LEFT JOIN puntaje p
                   ON p.estudiante_id = e.id
                  AND (%s::int IS NULL OR p.tipo_punto_id = %s::int)
            WHERE i.curso_id = %s
            GROUP BY e.id, u.nombre, m.nombre, c.nombre_seccion
        ) AS ranking
        ORDER BY posicion ASC, nombre ASC
        LIMIT %s OFFSET %s
        """,
        (tipo_punto_id, tipo_punto_id, curso_id, limit, offset),
    )
    return cur.fetchall()


def select_posicion_estudiante_en_curso(
    cur, curso_id: int, estudiante_id: int, tipo_punto_id: Optional[int]
) -> Optional[Row]:
    """Posicion de un estudiante concreto dentro del ranking de su curso."""
    cur.execute(
        f"""
        SELECT posicion, nombre, curso
        FROM (
            SELECT
                DENSE_RANK() OVER (ORDER BY COALESCE(SUM(p.valor), 0) DESC) AS posicion,
                u.nombre AS nombre,
                {_CURSO_NOMBRE} AS curso,
                e.id AS estudiante_id
            FROM inscripcion i
            JOIN curso c      ON c.id = i.curso_id
            JOIN materia m    ON m.id = c.materia_id
            JOIN estudiante e ON e.id = i.estudiante_id
            JOIN usuario u    ON u.id = e.usuario_id
            LEFT JOIN puntaje p
                   ON p.estudiante_id = e.id
                  AND (%s::int IS NULL OR p.tipo_punto_id = %s::int)
            WHERE i.curso_id = %s
            GROUP BY e.id, u.nombre, m.nombre, c.nombre_seccion
        ) AS ranking
        WHERE estudiante_id = %s
        """,
        (tipo_punto_id, tipo_punto_id, curso_id, estudiante_id),
    )
    return cur.fetchone()


# ============================ ANUNCIOS ============================

def select_anuncios(
    cur, limit: int, offset: int, rol: Optional[str] = None
) -> List[Row]:
    """Anuncios visibles para un rol, ordenados por fecha descendente."""
    cur.execute(
        f"""
        SELECT a.id, a.titulo, a.contenido, a.rol_destinatario, a.curso_id,
               a.fecha_publicacion, u.nombre AS autor,
               {_CURSO_NOMBRE} AS curso
        FROM anuncio a
        JOIN usuario u ON u.id = a.autor_id
        LEFT JOIN curso c   ON c.id = a.curso_id
        LEFT JOIN materia m ON m.id = c.materia_id
        WHERE (%s::rol_usuario IS NULL
               OR a.rol_destinatario IS NULL
               OR a.rol_destinatario = %s::rol_usuario)
        ORDER BY a.fecha_publicacion DESC, a.id DESC
        LIMIT %s OFFSET %s
        """,
        (rol, rol, limit, offset),
    )
    return cur.fetchall()


def select_anuncios_by_curso(cur, curso_id: int, limit: int, offset: int) -> List[Row]:
    cur.execute(
        f"""
        SELECT a.id, a.titulo, a.contenido, a.rol_destinatario, a.curso_id,
               a.fecha_publicacion, u.nombre AS autor,
               {_CURSO_NOMBRE} AS curso
        FROM anuncio a
        JOIN usuario u ON u.id = a.autor_id
        JOIN curso c   ON c.id = a.curso_id
        JOIN materia m ON m.id = c.materia_id
        WHERE a.curso_id = %s
        ORDER BY a.fecha_publicacion DESC, a.id DESC
        LIMIT %s OFFSET %s
        """,
        (curso_id, limit, offset),
    )
    return cur.fetchall()


def select_anuncios_recientes(cur, dias: int, limit: int) -> List[Row]:
    cur.execute(
        f"""
        SELECT a.id, a.titulo, a.contenido, a.rol_destinatario, a.curso_id,
               a.fecha_publicacion, u.nombre AS autor,
               {_CURSO_NOMBRE} AS curso
        FROM anuncio a
        JOIN usuario u ON u.id = a.autor_id
        LEFT JOIN curso c   ON c.id = a.curso_id
        LEFT JOIN materia m ON m.id = c.materia_id
        WHERE a.fecha_publicacion >= now() - (%s * INTERVAL '1 day')
        ORDER BY a.fecha_publicacion DESC, a.id DESC
        LIMIT %s
        """,
        (dias, limit),
    )
    return cur.fetchall()


def insert_anuncio(
    cur,
    autor_id: int,
    titulo: str,
    contenido: str,
    rol_destinatario: Optional[str],
    curso_id: Optional[int],
) -> Row:
    cur.execute(
        """
        INSERT INTO anuncio (autor_id, titulo, contenido, rol_destinatario, curso_id)
        VALUES (%s, %s, %s, %s::rol_usuario, %s)
        RETURNING id, autor_id, titulo, contenido, rol_destinatario, curso_id,
                  fecha_publicacion
        """,
        (autor_id, titulo, contenido, rol_destinatario, curso_id),
    )
    return cur.fetchone()


def delete_anuncio(cur, anuncio_id: int) -> Optional[Row]:
    cur.execute("DELETE FROM anuncio WHERE id = %s RETURNING id", (anuncio_id,))
    return cur.fetchone()
