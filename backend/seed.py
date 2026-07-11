import psycopg2
from psycopg2.extras import RealDictCursor
import os
from app.config import DATABASE_URL
from app.auth_utils import get_password_hash
from app.models import RolUsuario
from datetime import date, time

def run_sql_file(cur, filepath):
    if not os.path.exists(filepath):
        print(f"Advertencia: El archivo SQL no existe en {filepath}")
        return
    print(f"Ejecutando archivo SQL: {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    # Execute the file as a single transaction block
    cur.execute(sql)

def seed_data():
    print(f"Conectándose a la base de datos: {DATABASE_URL}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False # Use transactions
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Initialize tables from the classmate's schema
        schema_path = os.path.join(os.path.dirname(__file__), "..", "atenea_schema.sql")
        try:
            run_sql_file(cur, schema_path)
            print("Esquema base cargado correctamente.")
        except Exception as e:
            conn.rollback()
            # If it already exists, that's fine. We proceed.
            print(f"Nota: El esquema base ya podría estar cargado (Error: {e}). Continuando con las extensiones...")

        # 2. Apply Schema Extensions (safe checks / ALTER TABLE IF NOT EXISTS where possible)
        print("Aplicando extensiones de base de datos...")
        try:
            # Add column foto_url to usuario if it doesn't exist
            cur.execute("""
                ALTER TABLE usuario ADD COLUMN IF NOT EXISTS foto_url VARCHAR(255);
            """)
            
            # Add column estado to profesor if it doesn't exist
            cur.execute("""
                ALTER TABLE profesor ADD COLUMN IF NOT EXISTS estado VARCHAR(30) NOT NULL DEFAULT 'activo';
            """)
            
            # Add columns to curso if they don't exist
            cur.execute("""
                ALTER TABLE curso ADD COLUMN IF NOT EXISTS cupo_maximo INTEGER NOT NULL DEFAULT 30;
                ALTER TABLE curso ADD COLUMN IF NOT EXISTS estado VARCHAR(30) NOT NULL DEFAULT 'activo';
                ALTER TABLE curso ADD COLUMN IF NOT EXISTS sede_id VARCHAR(50);
            """)
            
            # Add column estado to calificacion if it doesn't exist
            cur.execute("""
                ALTER TABLE calificacion ADD COLUMN IF NOT EXISTS estado VARCHAR(30) NOT NULL DEFAULT 'publicada';
            """)

            # Add column estado to anuncio if it doesn't exist
            cur.execute("""
                ALTER TABLE anuncio ADD COLUMN IF NOT EXISTS estado VARCHAR(30) NOT NULL DEFAULT 'publicado';
            """)

            # Widen puntaje.origen: it stores a composed audit sentence
            # ("Otorgado por Prof. X en Y. Motivo: Z") that easily exceeds VARCHAR(100)
            cur.execute("""
                ALTER TABLE puntaje ALTER COLUMN origen TYPE TEXT;
            """)
            
            # Add columns to tipo_punto if they don't exist
            cur.execute("""
                ALTER TABLE tipo_punto ADD COLUMN IF NOT EXISTS icono VARCHAR(50);
                ALTER TABLE tipo_punto ADD COLUMN IF NOT EXISTS color VARCHAR(20);
                ALTER TABLE tipo_punto ADD COLUMN IF NOT EXISTS estado VARCHAR(30) NOT NULL DEFAULT 'activo';
            """)
            
            # Create recompensa table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recompensa (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL,
                    costo_puntos INTEGER NOT NULL CHECK (costo_puntos > 0),
                    tipo_punto_id INTEGER NOT NULL REFERENCES tipo_punto(id),
                    descripcion TEXT,
                    estado VARCHAR(30) NOT NULL DEFAULT 'activo',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            
            # Create canje table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS canje (
                    id SERIAL PRIMARY KEY,
                    estudiante_id INTEGER NOT NULL REFERENCES estudiante(id),
                    recompensa_id INTEGER NOT NULL REFERENCES recompensa(id),
                    puntos_usados INTEGER NOT NULL,
                    estado VARCHAR(30) NOT NULL DEFAULT 'pendiente',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            
            conn.commit()
            print("Extensiones aplicadas correctamente.")
        except Exception as e:
            conn.rollback()
            print(f"Error aplicando las extensiones: {e}")
            raise e

        # 3. Insert Seed Data if not already seeded
        cur.execute("SELECT COUNT(*) FROM usuario")
        count = cur.fetchone()["count"]
        if count > 0:
            print("La base de datos ya contiene registros. Omitiendo la inserción de semillas.")
            cur.close()
            conn.close()
            return
            
        print("Insertando registros de prueba (semillas)...")
        
        # Insert Rector
        cur.execute(
            "INSERT INTO usuario (email, nombre, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
            ("rector@atenea.io", "Don Alirio (Rector)", get_password_hash("rector123"), RolUsuario.rector.value)
        )
        
        # Insert Profesores
        cur.execute(
            "INSERT INTO usuario (email, nombre, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
            ("profesor1@atenea.io", "Elizabeth Blackburn (Profe Ciencias)", get_password_hash("profe123"), RolUsuario.profesor.value)
        )
        prof1_user_id = cur.fetchone()["id"]
        
        cur.execute(
            "INSERT INTO usuario (email, nombre, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
            ("profesor2@atenea.io", "Julio Profe (Profe Matemáticas)", get_password_hash("profe123"), RolUsuario.profesor.value)
        )
        prof2_user_id = cur.fetchone()["id"]
        
        cur.execute(
            "INSERT INTO profesor (usuario_id, especialidad, estado) VALUES (%s, %s, 'activo') RETURNING id",
            (prof1_user_id, "Ciencias Biológicas")
        )
        prof1_id = cur.fetchone()["id"]
        
        cur.execute(
            "INSERT INTO profesor (usuario_id, especialidad, estado) VALUES (%s, %s, 'activo') RETURNING id",
            (prof2_user_id, "Cálculo y Álgebra")
        )
        prof2_id = cur.fetchone()["id"]
        
        # Insert Estudiantes
        cur.execute(
            "INSERT INTO usuario (email, nombre, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
            ("estudiante1@atenea.io", "Adriano (Estudiante 1)", get_password_hash("estu123"), RolUsuario.estudiante.value)
        )
        est1_user_id = cur.fetchone()["id"]
        
        cur.execute(
            "INSERT INTO usuario (email, nombre, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
            ("estudiante2@atenea.io", "Maria (Estudiante 2)", get_password_hash("estu123"), RolUsuario.estudiante.value)
        )
        est2_user_id = cur.fetchone()["id"]
        
        cur.execute(
            "INSERT INTO usuario (email, nombre, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
            ("estudiante3@atenea.io", "Juan (Estudiante 3)", get_password_hash("estu123"), RolUsuario.estudiante.value)
        )
        est3_user_id = cur.fetchone()["id"]
        
        cur.execute(
            "INSERT INTO estudiante (usuario_id, fecha_nacimiento, estado, total_puntos) VALUES (%s, %s, 'activo', 150) RETURNING id",
            (est1_user_id, date(2005, 5, 12))
        )
        est1_id = cur.fetchone()["id"]
        
        cur.execute(
            "INSERT INTO estudiante (usuario_id, fecha_nacimiento, estado, total_puntos) VALUES (%s, %s, 'activo', 80) RETURNING id",
            (est2_user_id, date(2006, 8, 24))
        )
        est2_id = cur.fetchone()["id"]
        
        cur.execute(
            "INSERT INTO estudiante (usuario_id, fecha_nacimiento, estado, total_puntos) VALUES (%s, %s, 'activo', 20) RETURNING id",
            (est3_user_id, date(2005, 11, 2))
        )
        est3_id = cur.fetchone()["id"]
        
        # Insert Materias
        cur.execute("INSERT INTO materia (nombre) VALUES (%s) RETURNING id", ("Matemáticas Avanzadas",))
        mat1_id = cur.fetchone()["id"]
        cur.execute("INSERT INTO materia (nombre) VALUES (%s) RETURNING id", ("Biología Molecular",))
        mat2_id = cur.fetchone()["id"]
        cur.execute("INSERT INTO materia (nombre) VALUES (%s) RETURNING id", ("Español y Literatura",))
        mat3_id = cur.fetchone()["id"]
        
        # Insert Cursos
        cur.execute(
            """
            INSERT INTO curso (materia_id, profesor_id, periodo, nombre_seccion, cupo_maximo, estado, sede_id)
            VALUES (%s, %s, '2026-1', 'Décimo A', 30, 'activo', 'Sede Norte') RETURNING id
            """,
            (mat1_id, prof2_id)
        )
        curso1_id = cur.fetchone()["id"]
        
        cur.execute(
            """
            INSERT INTO curso (materia_id, profesor_id, periodo, nombre_seccion, cupo_maximo, estado, sede_id)
            VALUES (%s, %s, '2026-1', 'Décimo A', 30, 'activo', 'Sede Norte') RETURNING id
            """,
            (mat2_id, prof1_id)
        )
        curso2_id = cur.fetchone()["id"]
        
        # Insert Horarios
        cur.execute("INSERT INTO horario (curso_id, dia_semana, hora_inicio, hora_fin, aula) VALUES (%s, 1, '08:00:00', '09:30:00', 'Salón 101')", (curso1_id,))
        cur.execute("INSERT INTO horario (curso_id, dia_semana, hora_inicio, hora_fin, aula) VALUES (%s, 3, '08:00:00', '09:30:00', 'Salón 101')", (curso1_id,))
        cur.execute("INSERT INTO horario (curso_id, dia_semana, hora_inicio, hora_fin, aula) VALUES (%s, 2, '10:00:00', '11:30:00', 'Laboratorio B')", (curso2_id,))
        
        # Insert Enrollments (Inscripciones)
        cur.execute("INSERT INTO inscripcion (estudiante_id, curso_id, fecha_inscripcion) VALUES (%s, %s, CURRENT_DATE)", (est1_id, curso1_id))
        cur.execute("INSERT INTO inscripcion (estudiante_id, curso_id, fecha_inscripcion) VALUES (%s, %s, CURRENT_DATE)", (est1_id, curso2_id))
        cur.execute("INSERT INTO inscripcion (estudiante_id, curso_id, fecha_inscripcion) VALUES (%s, %s, CURRENT_DATE)", (est2_id, curso1_id))
        
        # Insert Tipos de Punto
        cur.execute(
            """
            INSERT INTO tipo_punto (nombre, descripcion, icono, color, estado)
            VALUES (%s, %s, %s, %s, 'activo') RETURNING id
            """,
            ("Participación Destacada", "Puntos otorgados por responder preguntas difíciles en clase.", "emoji_events", "#f1c40f")
        )
        tp1_id = cur.fetchone()["id"]
        
        cur.execute(
            """
            INSERT INTO tipo_punto (nombre, descripcion, icono, color, estado)
            VALUES (%s, %s, %s, %s, 'activo') RETURNING id
            """,
            ("Asistencia Perfecta", "Asistir puntualmente a todas las clases del mes.", "check_circle", "#2ecc71")
        )
        tp2_id = cur.fetchone()["id"]
        
        cur.execute(
            """
            INSERT INTO tipo_punto (nombre, descripcion, icono, color, estado)
            VALUES (%s, %s, %s, %s, 'activo') RETURNING id
            """,
            ("Ayuda a Compañeros", "Apoyar a compañeros con explicaciones académicas.", "groups", "#3498db")
        )
        tp3_id = cur.fetchone()["id"]
        
        # Insert Recompensas
        cur.execute(
            """
            INSERT INTO recompensa (nombre, costo_puntos, tipo_punto_id, descripcion, estado)
            VALUES (%s, %s, %s, %s, 'activo')
            """,
            ("+0.5 en Examen Final", 50, tp1_id, "Suma medio punto a tu nota final de cualquier examen.")
        )
        cur.execute(
            """
            INSERT INTO recompensa (nombre, costo_puntos, tipo_punto_id, descripcion, estado)
            VALUES (%s, %s, %s, %s, 'activo')
            """,
            ("Exoneración de Tarea Corta", 80, tp2_id, "Quedas libre de entregar una tarea corta de tu elección.")
        )
        cur.execute(
            """
            INSERT INTO recompensa (nombre, costo_puntos, tipo_punto_id, descripcion, estado)
            VALUES (%s, %s, %s, %s, 'activo')
            """,
            ("Libro Escolar de Obsequio", 100, tp3_id, "Elige un libro literario de la biblioteca como regalo.")
        )
        
        # Insert initial points transactions to match current balances
        cur.execute("INSERT INTO puntaje (estudiante_id, tipo_punto_id, valor, origen, fecha) VALUES (%s, %s, 150, 'Semilla inicial', NOW())", (est1_id, tp1_id))
        cur.execute("INSERT INTO puntaje (estudiante_id, tipo_punto_id, valor, origen, fecha) VALUES (%s, %s, 80, 'Semilla inicial', NOW())", (est2_id, tp2_id))
        cur.execute("INSERT INTO puntaje (estudiante_id, tipo_punto_id, valor, origen, fecha) VALUES (%s, %s, 20, 'Semilla inicial', NOW())", (est3_id, tp3_id))
        
        conn.commit()
        print("Seed completado exitosamente.")
        
    except Exception as e:
        print(f"Error al poblar la base de datos: {e}")
        try:
            conn.rollback()
        except:
            pass
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

if __name__ == "__main__":
    seed_data()
