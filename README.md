# 🎓 Atenea.io

> Plataforma de Gestión Educativa desarrollada como Proyecto Integrador en Riwi.

---

## 📖 Descripción

Atenea.io es un sistema de gestión educativa diseñado para facilitar la administración académica de una institución educativa mediante una aplicación desarrollada con JavaScript Vanilla y Vite.

La plataforma permite administrar estudiantes, profesores, cursos, notas, horarios, comunicados institucionales y un sistema de gamificación que incentiva el rendimiento académico.

El sistema está construido bajo una arquitectura modular y escalable siguiendo el modelo Multiple Page Application (MPA).

---

# 🚀 Características

## 👨‍🎓 Estudiantes

- Consultar boletín de notas
- Ver cursos matriculados
- Consultar horarios
- Consultar comunicados
- Visualizar ranking de puntos
- Canjear recompensas
- Editar perfil

## 👨‍🏫 Profesores

- Gestionar notas (CRUD)
- Consultar cursos asignados
- Asignar puntos de gamificación
- Ver horarios
- Consultar comunicados

## 👨‍💼 Rector

- Gestión de estudiantes
- Gestión de profesores
- Gestión de cursos
- Cambiar horarios
- Publicar comunicados
- Configurar tipos de puntos
- Dashboard con estadísticas

---

# 🏆 Sistema de Gamificación

El proyecto incorpora un sistema de recompensas flexible donde:

- Existen múltiples tipos de puntuación.
- Los puntos se asignan por materia.
- Cada asignación queda registrada.
- Se genera un ranking por curso.
- Los estudiantes pueden canjear recompensas.

---

## 🛠 Tecnologías

### Frontend
- HTML5
- CSS3
- JavaScript (ES6+)

### Dependencias
- Vite

### Backend
- Node.js
- Express.js *(si lo utilizarán como API)*

### Base de Datos
- PostgreSQL

### Herramientas
- Git
- GitHub
- Postman
- pgAdmin 4

### Persistencia
- LocalStorage
- SessionStorage
---

# 📂 Estructura del proyecto

```text
src/
│
├── assets/
├── components/
├── pages/
├── router/
├── services/
├── store/
├── styles/
├── utils/
└── main.js
```

---

# 🗄️ Base de Datos

El sistema utiliza PostgreSQL como gestor de base de datos relacional.

Las principales entidades del sistema incluyen:

- Usuarios
- Estudiantes
- Profesores
- Cursos
- materia
- Horarios
- Inscripciones
- Puntaje
- Tipo_puntos
- Comunicados
- Calificaciones
- Boletin


---


# ⚙️ Instalación

## 1 Clonar el repositorio

```bash
git clone URL_DEL_REPOSITORIO
```

## 2 Entrar al proyecto

```bash
cd atenea
```

## 3 Instalar dependencias

```bash
npm install
```

## 4 Ejecutar Vite

```bash
npm run dev
```

---
# 🏗️ Arquitectura del Sistema

```text
                        ┌───────────────────────────┐
                        │        Usuario            │
                        │ Rector | Profesor | Alumno│
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       Frontend          │
                         │ HTML + CSS + JS + Vite  │
                         └─────────────┬───────────┘
                                       │
                                       ▼
                         ┌─────────────────────────┐
                         │         Router          │
                         │ Navegación entre vistas │
                         └─────────────┬───────────┘
                                       │
               ┌───────────────────────┼────────────────────────┐
               ▼                       ▼                        ▼
      ┌────────────────┐      ┌────────────────┐      ┌────────────────┐
      │   Components   │      │     Pages      │      │     Store      │
      │ UI reutilizable│      │ Vistas MPA     │      │ Sesión Usuario │
      └────────┬───────┘      └────────┬───────┘      └────────┬───────┘
               │                       │                       │
               └───────────────┬───────┴───────────────────────┘
                               ▼
                     ┌─────────────────────┐
                     │      Services       │
                     │ Lógica de negocio   │
                     │ Fetch / API REST    │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │      Backend        │
                     │ Node.js + Express   │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │     PostgreSQL      │
                     │ Base de Datos       │
                     └─────────────────────┘
```

# 🔄 Flujo General del Sistema

```text
               Inicio
                  │
                  ▼
          Iniciar Sesión
                  │
                  ▼
      Validación de Credenciales
                  │
         ┌────────┴────────┐
         │                 │
   Credenciales      Credenciales
    Correctas         Incorrectas
         │                 │
         ▼                 ▼
  Dashboard según     Mostrar Error
        Rol                 │
         │                  │
         ▼                  │
 Seleccionar Módulo ◄────────┘
         │
         ▼
Consultar / Registrar Información
         │
         ▼
Validación de Datos
         │
         ▼
Enviar solicitud al Backend
         │
         ▼
Actualizar PostgreSQL
         │
         ▼
Obtener respuesta
         │
         ▼
Actualizar la interfaz
         │
         ▼
Fin del proceso
```


# 👥 Roles del sistema

| Rol | Funciones |
|------|-----------|
| Rector | Administración completa |
| Profesor | Gestión académica |
| Estudiante | Consulta académica |

---

# 📚 Historias de Usuario

El desarrollo del proyecto está basado en historias de usuario que incluyen:

- Autenticación
- Gestión de cursos
- Gestión de estudiantes
- Gestión de profesores
- CRUD de notas
- Comunicados
- Gamificación
- Dashboard
- Perfil
- Arquitectura MPA

---

# 🔐 Autenticación

El sistema implementa:

- Inicio de sesión
- Protección de rutas
- Persistencia de sesión
- Control de acceso por roles

---

# 📈 Escalabilidad

La aplicación fue diseñada teniendo en cuenta principios de escalabilidad vertical:

- Arquitectura modular
- Router desacoplado
- Servicios independientes
- Paginación
- Gestión centralizada del estado
- Separación por capas

---

# 📸 Capturas

Aquí se agregarán imágenes del proyecto.

## ERD

![ERD](./docs/ERD.jpg)

## Login

![Login](./docs/login.png)

## Dashboard

![Dashboard](./docs/dashboard.png)

## Boletín

![Boletín](./docs/boletin.png)

---

# 👨‍💻 Integrantes

| Nombre          | Rol          |
|-----------------|--------------|
| Auri Valdes     |Scrum Master  |
| Jesus Lucena    | Frontend     |
| Adriano Gonzales| Backend      |
| Kevin           | Base de Datos|
| Daniel Viaña    | Documentación|

---

# 📄 Licencia

Proyecto académico desarrollado para Riwi.