from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import date, time, datetime
from app.models import RolUsuario  # no eres especifico con la root del proyecto deben haber
# mejores validacione, faltan mensajes de que se haya inicializado el programa correctamente, y 
# que se haya conectado a la base de datos, y que se haya creado el usuario. 

# Auth Schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre: str

class TokenData(BaseModel):
    email: Optional[str] = None

# User Schemas
class UsuarioBase(BaseModel):
    email: EmailStr
    nombre: str
    rol: RolUsuario
    foto_url: Optional[str] = None

class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre: str
    password: str = Field(..., min_length=6)
    rol: RolUsuario
    foto_url: Optional[str] = None

class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre: Optional[str] = None
    password: Optional[str] = None
    foto_url: Optional[str] = None
    confirm_password: Optional[str] = None # For profile editing (US-17)

class UsuarioResponse(UsuarioBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Estudiante & Profesor management (Rector - US-05, US-06)
class EstudianteCreateRector(BaseModel):
    nombre: str
    email: EmailStr
    password_temporal: str = Field(..., min_length=6)
    fecha_nacimiento: Optional[date] = None
    curso_id: Optional[int] = None  # matricula al estudiante en este curso

class EstudianteUpdateRector(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    estado: Optional[str] = None
    fecha_nacimiento: Optional[date] = None

class ProfesorCreateRector(BaseModel):
    nombre: str
    email: EmailStr
    password_temporal: str = Field(..., min_length=6)
    especialidad: Optional[str] = None

class ProfesorUpdateRector(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    especialidad: Optional[str] = None
    estado: Optional[str] = None

# Estudiante & Profesor Extensions
class EstudianteResponse(BaseModel):
    id: int
    fecha_nacimiento: Optional[date] = None
    estado: str
    total_puntos: int
    usuario: UsuarioResponse

    class Config:
        from_attributes = True

class ProfesorResponse(BaseModel):
    id: int
    especialidad: Optional[str] = None
    estado: str
    usuario: UsuarioResponse

    class Config:
        from_attributes = True

# Materia Schemas
class MateriaBase(BaseModel):
    nombre: str

class MateriaResponse(MateriaBase):
    id: int

    class Config:
        from_attributes = True

# Curso Schemas (donde se matricula un estudiante, ej: "9-A")
class CursoBase(BaseModel):
    nombre: str
    periodo: str
    cupo_maximo: int = Field(default=30, ge=1)
    estado: str = "activo"
    sede_id: Optional[str] = None

class CursoCreate(CursoBase):
    pass

class CursoUpdate(BaseModel):
    nombre: Optional[str] = None
    periodo: Optional[str] = None
    cupo_maximo: Optional[int] = None
    estado: Optional[str] = None
    sede_id: Optional[str] = None

class CursoResponse(CursoBase):
    id: int

    class Config:
        from_attributes = True

# Horario Schemas
class HorarioBase(BaseModel):
    dia_semana: int = Field(..., ge=1, le=7) # 1-7 (Lunes-Domingo)
    hora_inicio: time
    hora_fin: time
    aula: Optional[str] = None

class HorarioCreate(HorarioBase):
    pass

class HorarioResponse(HorarioBase):
    id: int
    curso_materia_id: int

    class Config:
        from_attributes = True

# CursoMateria Schemas (una materia ofrecida dentro de un curso, ej: "Matemáticas en 9-A")
class CursoMateriaBase(BaseModel):
    materia_id: int
    profesor_id: Optional[int] = None
    curso_id: int
    estado: str = "activo"

class CursoMateriaCreate(CursoMateriaBase):
    horarios: List[HorarioCreate] = []

class CursoMateriaUpdate(BaseModel):
    materia_id: Optional[int] = None
    profesor_id: Optional[int] = None
    curso_id: Optional[int] = None
    estado: Optional[str] = None
    horarios: Optional[List[HorarioCreate]] = None

class CursoMateriaResponse(BaseModel):
    id: int
    materia: MateriaResponse
    profesor: Optional[ProfesorResponse] = None
    curso: Optional[CursoResponse] = None
    estado: str
    horarios: List[HorarioResponse] = []

    class Config:
        from_attributes = True

# Calificacion Schemas
class CalificacionBase(BaseModel):
    tipo_evaluacion: str
    valor: float = Field(..., ge=0.0, le=5.0)
    estado: str = "publicada" # 'borrador' | 'publicada'

class CalificacionCreate(CalificacionBase):
    inscripcion_id: int
    curso_materia_id: int

class CalificacionUpdate(BaseModel):
    tipo_evaluacion: Optional[str] = None
    valor: Optional[float] = Field(None, ge=0.0, le=5.0)
    estado: Optional[str] = None

class CalificacionResponse(CalificacionBase):
    id: int
    inscripcion_id: int
    curso_materia_id: int
    fecha: date
    desempeno: Optional[str] = None

    class Config:
        from_attributes = True

# Inscripcion Schemas
class InscripcionCreate(BaseModel):
    estudiante_id: int
    curso_id: int

class InscripcionResponse(BaseModel):
    id: int
    estudiante_id: int
    curso_id: int
    fecha_inscripcion: date

    class Config:
        from_attributes = True

# Boletin Schemas
class BoletinResponse(BaseModel):
    id: int
    estudiante_id: int
    curso_materia_id: int
    periodo: str
    promedio_final: float
    fecha_generacion: date
    curso_materia: Optional[CursoMateriaResponse] = None

    class Config:
        from_attributes = True

# Anuncio Schemas
class AnuncioBase(BaseModel):
    titulo: str
    contenido: str
    rol_destinatario: Optional[RolUsuario] = None
    curso_materia_id: Optional[int] = None
    estado: str = "publicado"

class AnuncioCreate(AnuncioBase):
    pass

class AnuncioResponse(AnuncioBase):
    id: int
    autor_id: int
    fecha_publicacion: datetime
    autor: UsuarioResponse

    class Config:
        from_attributes = True

# TipoPunto Schemas
class TipoPuntoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    estado: str = "activo"

class TipoPuntoCreate(TipoPuntoBase):
    pass

class TipoPuntoResponse(TipoPuntoBase):
    id: int

    class Config:
        from_attributes = True

# Puntaje Schemas
class PuntajeCreate(BaseModel):
    estudiante_id: int
    tipo_punto_id: int
    valor: int = Field(..., gt=0)
    origen: Optional[str] = None
    curso_materia_id: int # To validate the teacher has them in class

class PuntajeResponse(BaseModel):
    id: int
    estudiante_id: int
    tipo_punto: TipoPuntoResponse
    valor: int
    origen: Optional[str] = None
    fecha: datetime

    class Config:
        from_attributes = True

# Recompensa Schemas
class RecompensaBase(BaseModel):
    nombre: str
    costo_puntos: int = Field(..., gt=0)
    tipo_punto_id: int
    descripcion: Optional[str] = None
    estado: str = "activo"

class RecompensaCreate(RecompensaBase):
    pass

class RecompensaResponse(RecompensaBase):
    id: int
    tipo_punto: TipoPuntoResponse
    created_at: datetime

    class Config:
        from_attributes = True

# Canje Schemas
class CanjeCreate(BaseModel):
    recompensa_id: int

class CanjeResponse(BaseModel):
    id: int
    estudiante_id: int
    recompensa: RecompensaResponse
    puntos_usados: int
    estado: str
    created_at: datetime

    class Config:
        from_attributes = True

class CanjeEstadoUpdate(BaseModel):
    estado: str  # 'aprobado' | 'rechazado' - resolución del rector (US-16)

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, v: str) -> str:
        if v not in ("aprobado", "rechazado"):
            raise ValueError("estado debe ser 'aprobado' o 'rechazado'")
        return v

# Dashboard Stats Schemas (US-07)
class DashboardStats(BaseModel):
    promedio_general_por_curso: List[dict]
    total_estudiantes_activos: int
    total_estudiantes_inactivos: int
    top_gamificacion: List[dict]

# Tarea Schemas
class TareaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    fecha_entrega: Optional[date] = None
    estado: str = "abierta"  # 'abierta' | 'cerrada'

class TareaCreate(TareaBase):
    curso_materia_id: int

class TareaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_entrega: Optional[date] = None
    estado: Optional[str] = None

class TareaResponse(TareaBase):
    id: int
    curso_materia_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Asistencia Schemas
class AsistenciaRegistroItem(BaseModel):
    estudiante_id: int
    estado: str  # 'presente' | 'ausente' | 'tarde' | 'justificado'

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, v: str) -> str:
        if v not in ("presente", "ausente", "tarde", "justificado"):
            raise ValueError("estado debe ser 'presente', 'ausente', 'tarde' o 'justificado'")
        return v

class AsistenciaBulkCreate(BaseModel):
    curso_materia_id: int
    fecha: date
    registros: List[AsistenciaRegistroItem]

class AsistenciaResponse(BaseModel):
    id: int
    inscripcion_id: int
    curso_materia_id: int
    estudiante_id: int
    fecha: date
    estado: str

    class Config:
        from_attributes = True
