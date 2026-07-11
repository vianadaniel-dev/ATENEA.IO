import enum

class RolUsuario(str, enum.Enum):
    rector = "rector"
    profesor = "profesor"
    estudiante = "estudiante"
