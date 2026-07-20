from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, rector, profesor, estudiante

app = FastAPI(
    title="Atenea.io API",
    description="API Backend para la plataforma de gestión escolar Atenea.io built with Python, FastAPI and PostgreSQL.",
    version="1.0.0",
)

# Set up CORS middleware to allow connection from the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/auth_utils.py", tags=["Autenticación"])
app.include_router(rector.router, prefix="/rector", tags=["Módulo Rector"])
app.include_router(profesor.router, prefix="/profesor", tags=["Módulo Profesor"])
app.include_router(estudiante.router, prefix="/estudiante", tags=["Módulo Estudiante"])

@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a la API de Atenea.io",
        "docs": "/docs",
        "status": "online"
    }
