
CREATE TYPE rol_usuario AS ENUM ('rector', 'profesor', 'estudiante');
CREATE TABLE usuario (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nombre        VARCHAR(150) NOT NULL,
    rol           rol_usuario NOT NULL,
    foto_url      VARCHAR(255),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE estudiante (
    id               SERIAL PRIMARY KEY,
    usuario_id       INTEGER NOT NULL UNIQUE REFERENCES usuario(id),
    fecha_nacimiento DATE,
    estado           VARCHAR(30) NOT NULL DEFAULT 'activo',
    total_puntos     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE profesor (
    id           SERIAL PRIMARY KEY,
    usuario_id   INTEGER NOT NULL UNIQUE REFERENCES usuario(id),
    especialidad VARCHAR(150),
    estado       VARCHAR(30) NOT NULL DEFAULT 'activo'
);

CREATE TABLE materia (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL
);

-- "curso" es donde se matricula el estudiante (ej: "9-A").
CREATE TABLE curso (
    id             SERIAL PRIMARY KEY,
    nombre         VARCHAR(50) NOT NULL,
    periodo        VARCHAR(20) NOT NULL,   -- ej: '2026-1'
    cupo_maximo    INTEGER NOT NULL DEFAULT 30,
    estado         VARCHAR(30) NOT NULL DEFAULT 'activo',
    sede_id        VARCHAR(50),
    UNIQUE (nombre, periodo)
);

-- "curso_materia" es una materia ofrecida dentro de un curso (ej: "Matemáticas en 9-A").
CREATE TABLE curso_materia (
    id             SERIAL PRIMARY KEY,
    curso_id       INTEGER NOT NULL REFERENCES curso(id),
    materia_id     INTEGER NOT NULL REFERENCES materia(id),
    profesor_id    INTEGER REFERENCES profesor(id),
    estado         VARCHAR(30) NOT NULL DEFAULT 'activo',
    UNIQUE (curso_id, materia_id)
);

CREATE TABLE inscripcion (
    id                SERIAL PRIMARY KEY,
    estudiante_id     INTEGER NOT NULL REFERENCES estudiante(id),
    curso_id          INTEGER NOT NULL REFERENCES curso(id),
    fecha_inscripcion DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (estudiante_id, curso_id)
);

CREATE TABLE calificacion (
    id               SERIAL PRIMARY KEY,
    inscripcion_id   INTEGER NOT NULL REFERENCES inscripcion(id) ON DELETE CASCADE,
    curso_materia_id INTEGER NOT NULL REFERENCES curso_materia(id),
    tipo_evaluacion  VARCHAR(50) NOT NULL,
    valor            NUMERIC(4,2) NOT NULL CHECK (valor >= 0 AND valor <= 5),
    estado           VARCHAR(30) NOT NULL DEFAULT 'publicada', -- 'borrador' | 'publicada'
    fecha            DATE NOT NULL DEFAULT CURRENT_DATE
);
CREATE TABLE boletin (
    id               SERIAL PRIMARY KEY,
    estudiante_id    INTEGER NOT NULL REFERENCES estudiante(id),
    curso_materia_id INTEGER NOT NULL REFERENCES curso_materia(id),
    periodo          VARCHAR(20) NOT NULL,
    promedio_final   NUMERIC(4,2) NOT NULL,
    fecha_generacion DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (estudiante_id, curso_materia_id, periodo)
);

CREATE TABLE horario (
    id               SERIAL PRIMARY KEY,
    curso_materia_id INTEGER NOT NULL REFERENCES curso_materia(id),
    dia_semana       SMALLINT NOT NULL CHECK (dia_semana BETWEEN 1 AND 7),
    hora_inicio      TIME NOT NULL,
    hora_fin         TIME NOT NULL,
    aula             VARCHAR(30)
);

CREATE TABLE tarea (
    id               SERIAL PRIMARY KEY,
    curso_materia_id INTEGER NOT NULL REFERENCES curso_materia(id),
    titulo           VARCHAR(150) NOT NULL,
    descripcion      TEXT,
    fecha_entrega    DATE,
    estado           VARCHAR(20) NOT NULL DEFAULT 'abierta', -- 'abierta' | 'cerrada'
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE asistencia (
    id               SERIAL PRIMARY KEY,
    inscripcion_id   INTEGER NOT NULL REFERENCES inscripcion(id) ON DELETE CASCADE,
    curso_materia_id INTEGER NOT NULL REFERENCES curso_materia(id),
    fecha            DATE NOT NULL,
    estado           VARCHAR(20) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (inscripcion_id, curso_materia_id, fecha)
);

CREATE TABLE anuncio (
    id                SERIAL PRIMARY KEY,
    autor_id          INTEGER NOT NULL REFERENCES usuario(id),
    titulo            VARCHAR(200) NOT NULL,
    contenido         TEXT NOT NULL,
    rol_destinatario  rol_usuario,                       -- NULL = para todos los roles
    curso_materia_id  INTEGER REFERENCES curso_materia(id), -- NULL = institucional general
    estado            VARCHAR(30) NOT NULL DEFAULT 'publicado', -- 'borrador' | 'publicado'
    fecha_publicacion TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tipo_punto (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(50) UNIQUE NOT NULL,  -- 'asistencia', 'participacion', 'insignia_lectura'...
    descripcion TEXT,
    icono       VARCHAR(50),
    color       VARCHAR(20),
    estado      VARCHAR(30) NOT NULL DEFAULT 'activo'
);

CREATE TABLE puntaje (
    id            SERIAL PRIMARY KEY,
    estudiante_id INTEGER NOT NULL REFERENCES estudiante(id),
    tipo_punto_id INTEGER NOT NULL REFERENCES tipo_punto(id),
    valor         INTEGER NOT NULL,
    origen        TEXT,
    fecha         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE recompensa (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(150) NOT NULL,
    costo_puntos  INTEGER NOT NULL CHECK (costo_puntos > 0),
    tipo_punto_id INTEGER NOT NULL REFERENCES tipo_punto(id),
    descripcion   TEXT,
    estado        VARCHAR(30) NOT NULL DEFAULT 'activo',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE canje (
    id             SERIAL PRIMARY KEY,
    estudiante_id  INTEGER NOT NULL REFERENCES estudiante(id),
    recompensa_id  INTEGER NOT NULL REFERENCES recompensa(id),
    puntos_usados  INTEGER NOT NULL,
    estado         VARCHAR(30) NOT NULL DEFAULT 'pendiente', -- 'pendiente' | 'aprobado' | 'rechazado'
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Indices pensados para paginacion server-side
-- sirve para encontrar información rápidamente
-- sin tener que leer todo el documento desde el principio.
CREATE INDEX idx_curso_materia_curso    ON curso_materia(curso_id);
CREATE INDEX idx_inscripcion_curso        ON inscripcion(curso_id);
CREATE INDEX idx_calificacion_inscripcion ON calificacion(inscripcion_id);
CREATE INDEX idx_calificacion_curso_materia ON calificacion(curso_materia_id);
CREATE INDEX idx_boletin_estudiante_periodo ON boletin(estudiante_id, periodo);
CREATE INDEX idx_puntaje_estudiante       ON puntaje(estudiante_id);
CREATE INDEX idx_anuncio_fecha           ON anuncio(fecha_publicacion DESC);
CREATE INDEX idx_horario_curso_materia   ON horario(curso_materia_id);
CREATE INDEX idx_tarea_curso_materia     ON tarea(curso_materia_id);
CREATE INDEX idx_asistencia_inscripcion  ON asistencia(inscripcion_id);
CREATE INDEX idx_asistencia_curso_materia ON asistencia(curso_materia_id);
CREATE INDEX idx_canje_estudiante        ON canje(estudiante_id);
CREATE INDEX idx_canje_estado            ON canje(estado);
-- esta es una vista del CRM
-- ¿QUE ES UN CRM?
-- es un software para organizar todas las interacciones
-- entre una empresa y sus clientes en un solo lugar
CREATE VIEW leaderboard AS
SELECT e.id AS estudiante_id, u.nombre, SUM(p.valor) AS puntos_totales
FROM estudiante e
JOIN usuario u ON u.id = e.usuario_id
JOIN puntaje p ON p.estudiante_id = e.id
GROUP BY e.id, u.nombre
ORDER BY puntos_totales DESC;
