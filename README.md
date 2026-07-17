#  Atenea.io

> **Educational Management Platform** developed as an Integrative Project at **Riwi**.

![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?logo=javascript&logoColor=black)
![SCSS](https://img.shields.io/badge/SCSS-Styles-CC6699?logo=sass&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-Frontend-646CFF?logo=vite)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)
![Supabase](https://img.shields.io/badge/Supabase-Hosting-3ECF8E?logo=supabase)
![GitHub](https://img.shields.io/badge/GitHub-Repo-181717?logo=github)
![License](https://img.shields.io/badge/License-Academic-blue)
---

# Overview

Atenea.io is a modern Educational Management System (EMS) built to simplify the administration of academic institutions.

The platform provides different workspaces for **Principals**, **Teachers**, and **Students**, allowing them to manage academic information securely according to their roles.

The application follows a **Layered Architecture** with a **Vanilla JavaScript SPA**, communicating with a **FastAPI REST API** backed by **PostgreSQL**.

---

# Features

## Student Module

- View Report Cards
- Check Enrolled Courses
- View Class Schedule
- Read Institutional Announcements
- View Gamification Ranking
- Redeem Rewards
- Edit Personal Profile

---

##  Teacher Module

- Grade Management (CRUD)
- View Assigned Courses
- Assign Reward Points
- View Schedule
- Read Announcements

---

## Principal Module

- Student Management
- Teacher Management
- Course Administration
- Schedule Management
- Publish Announcements
- Configure Reward Types
- Dashboard & Statistics

---

#  Gamification System

The platform includes a flexible reward system where:

- Multiple point categories are available.
- Points are assigned by subject.
- Every point assignment is recorded.
- Rankings are generated automatically.
- Students can redeem rewards.
- Reward history is stored.

---

# Tech Stack

## Frontend

- HTML5
- SCSS (7-1 Architecture)
- JavaScript (ES6+)
- Vite

---

## Backend

- FastAPI
- Python
- Psycopg3

---

## Database

- PostgreSQL 16

---

## Development Tools

- Git
- GitHub
- Visual Studio Code
- Supa base
- pgAdmin 4

---

# Project Structure

```text
ATENEA.IO/
│
├── src/                 # Código principal (frontend)
│   ├── assets/         # Imágenes y logos
│   ├── constants/      
│   ├── helpers/        
│   ├── models/         
│   ├── pages/           # Páginas por rol
│   │   ├── estudiante/
│   │   ├── profesor/
│   │   └── rector/
│   ├── partials/       # Componentes parciales/reusables
│   ├── services/       # Lógica de servicios/APIs
│   └── styles/         # Estructura de estilos
│       ├── abstracts/
│       ├── components/
│       ├── layouts/
│       └── pages/
│
├── public/             # Archivos estáticos
├── estudiante/         # (si aplica) carpeta extra por rol
├── profesor/           # (si aplica) carpeta extra por rol
├── rector/             # (si aplica) carpeta extra por rol
├── node_modules/       # Dependencias (generado automáticamente)
└── (configs)           # por ejemplo: vite config / etc.
```

---

# 🗄 Database Design

The application uses **PostgreSQL** as its relational database management system.

### Core Entities

- Users
- Students
- Teachers
- Courses
- Subjects
- Enrollments
- Schedules
- Grades
- Report Cards
- Reward Types
- Scores
- Announcements

---

# 🏛 Application Architecture

The frontend follows a lightweight MVC-inspired architecture.

| Layer | Responsibility |
|---------|---------------|
| **Views** | Render the user interface |
| **Controllers** | Handle business logic |
| **Services** | Communicate with the REST API |
| **Models** | Represent domain entities |
| **Layouts** | Shared page layouts |
| **Router** | SPA Navigation |
| **Helpers** | Utility functions |
| **Constants** | Global configuration |

---

#  System Architecture

```text
                           ┌──────────────────────────┐
                           │          Users           │
                           │ Principal • Teacher • Student │
                           └─────────────┬────────────┘
                                         │
                                         ▼
                    ┌────────────────────────────────────┐
                    │         Frontend (MPA)             │
                    │      HTML + SCSS + JavaScript      │
                    └─────────────┬──────────────────────┘
                                  │
                                  ▼
                       Router + Route Guards (RBAC)
                                  │
      ┌───────────────┬────────────┼───────────────┬───────────────┐
      ▼               ▼            ▼               ▼
   Views         Controllers    Services       Layouts
                                     │
                                     ▼
                           REST API (FastAPI)
                                     │
                                     │
                                     ▼
                              PostgreSQL 16
```

---

# 🔄 Application Flow

```text
Start
 │
 ▼
User Login
 │
 ▼
Validate Credentials
 │
 ├──────────────┐
 │              │
 ▼              ▼
Success      Failure
 │              │
 ▼              ▼
Load Dashboard  Display Error
 │
 ▼
Select Module
 │
 ▼
Controller
 │
 ▼
Service Layer
 │
 ▼
REST API
 │
 ▼
PostgreSQL
 │
 ▼
Return Response
 │
 ▼
Update UI
```

---

#  API Communication

The frontend communicates **exclusively** with the REST API through the **Services Layer**.

### API Modules

| Endpoint | Description |
|----------|-------------|
| `/api/auth` | Authentication |
| `/api/principal` | Principal Module |
| `/api/teacher` | Teacher Module |
| `/api/student` | Student Module |

Each service is responsible for:

- Sending HTTP requests
- Handling responses
- Processing errors
- Token management

---

#  Authentication & Authorization

The platform implements **Authentication** together with **Role-Based Access Control (RBAC).**

Features include:

- Secure Login
- Protected Routes
- Session Persistence
- User Authorization
- Role Guards

---

#  User Roles

| Role | Responsibilities |
|------|------------------|
| Principal | Complete platform administration |
| Teacher | Academic management |
| Student | Academic consultation |

---

# User Stories

The application is developed following Agile methodologies through User Stories.

Modules include:

- Authentication
- Student Management
- Teacher Management
- Course Management
- Subject Management
- Grade CRUD
- Schedule Management
- Report Cards
- Announcements
- Gamification
- User Profile
- Dashboard
- Notifications

---

#  Scalability

The project has been designed following software engineering best practices.

### Current Architecture

- Layered Architecture
- MVC-inspired Structure
- Modular Components
- Independent Services
- Reusable Layouts
- Route Guards
- Role Permissions
- RESTful API Integration
- PostgreSQL Relational Database

Future improvements may include:

- Docker Deployment
- CI/CD Pipelines
- Unit Testing
- Integration Testing
- WebSockets
- Notifications
- Dark Mode
- Progressive Web App (PWA)

---

#  Installation

## 1. Clone the repository

```bash
git clone https://github.com/your-username/atenea.git
```

---

## 2. Navigate to the project

```bash
cd atenea
```

---

## 3. Install Frontend Dependencies

```bash
npm install
```

---

## 4. Start the Frontend

```bash
npm run dev
```

---

## 5. Configure the Backend

```bash
cd backend
pip install -r requirements.txt
```

---

## 6. Run FastAPI

```bash
python run.py
```

---

## 7. Database

Configure PostgreSQL and execute:

```sql
atenea_schema.sql
```

---

# Screenshots

## Entity Relationship Diagram

![ERD](./docs/ERD.jpg)

---

## Login

![Login](./docs/login.png)

---

## Dashboard

![Dashboard](./docs/dashboard.png)

---

## Report Card

![Report Card](./docs/report-card.png)

---

# 🚀 Future Improvements

- Email Notifications
- Calendar Synchronization
- Attendance Tracking
- Parent Portal
- Mobile Responsive Improvements
- Analytics Dashboard
- AI-powered Academic Recommendations

---

#  Team

| Name | Role |
|------|------|
| **Auri Valdes** | Scrum Master |
| **Jesus Lucena** | Frontend Developer |
| **Adriano Gonzales** | Backend Developer |
| **Kevin** | Database Developer |
| **Daniel Viaña** | Technical Documentation |

---

#  License

This project was developed for academic purposes as part of the **Riwi Integrative Project**.

© 2026 Atenea.io — All Rights Reserved.
