"""Script de testing para verificar la conexión con Supabase.

Ejecuta con:
    python test_connection.py
"""

import sys
from config import settings
from database import init_pool, close_pool, get_cursor, acquire_connection

def test_config():
    """Verifica que las variables de entorno están cargadas."""
    print("🔍 Verificando configuración...")
    try:
        print(f"   DATABASE_URL: {settings.DATABASE_URL[:50]}...")
        print(f"   DB_SSLMODE: {settings.DB_SSLMODE}")
        print(f"   DB_POOL_MIN: {settings.DB_POOL_MIN}")
        print(f"   DB_POOL_MAX: {settings.DB_POOL_MAX}")
        print(f"   SECRET_KEY: {'*' * len(settings.SECRET_KEY[:20])}")
        print("✓ Configuración cargada correctamente\n")
        return True
    except Exception as exc:
        print(f"✗ Error en configuración: {exc}\n")
        return False


def test_pool_creation():
    """Verifica que se puede crear el pool de conexiones."""
    print("🔍 Inicializando pool de conexiones...")
    try:
        init_pool()
        print("✓ Pool creado correctamente\n")
        return True
    except Exception as exc:
        print(f"✗ Error al crear el pool: {exc}\n")
        return False


def test_database_connection():
    """Verifica que se puede conectar a la base de datos."""
    print("🔍 Conectando a la base de datos...")
    try:
        conn = acquire_connection()
        with get_cursor(conn) as cur:
            cur.execute("SELECT 1 AS ok")
            result = cur.fetchone()
        print(f"✓ Conexión exitosa: {result}\n")
        return True
    except Exception as exc:
        print(f"✗ Error de conexión: {exc}\n")
        return False


def test_table_check():
    """Verifica que existen las tablas principales."""
    print("🔍 Verificando tablas de la base de datos...")
    tables_to_check = ["usuario", "estudiante", "profesor", "curso", "inscripcion"]
    try:
        conn = acquire_connection()
        with get_cursor(conn) as cur:
            for table in tables_to_check:
                cur.execute(f"SELECT 1 FROM {table} LIMIT 1")
                print(f"   ✓ Tabla '{table}' existe")
        print("✓ Todas las tablas necesarias existen\n")
        return True
    except Exception as exc:
        print(f"✗ Error al verificar tablas: {exc}")
        print("   (Nota: Las tablas deben ser creadas en Supabase primero)\n")
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n" + "=" * 60)
    print("   TEST DE CONEXIÓN - ATENEA.IO Backend")
    print("=" * 60 + "\n")

    results = []
    results.append(("Configuración", test_config()))
    results.append(("Pool de conexiones", test_pool_creation()))
    results.append(("Conexión a BD", test_database_connection()))
    results.append(("Tablas existentes", test_table_check()))

    # Resumen
    close_pool()
    print("=" * 60)
    print("RESUMEN DE RESULTADOS:")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASÓ" if result else "✗ FALLÓ"
        print(f"{name}: {status}")

    all_passed = all(result for _, result in results)
    print("=" * 60 + "\n")

    if all_passed:
        print("✓ ¡Todos los tests pasaron! La conexión está lista.\n")
        return 0
    else:
        print("✗ Algunos tests fallaron. Revisa la configuración.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
