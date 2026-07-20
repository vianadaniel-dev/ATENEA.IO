import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from api import DATABASE_URL

# Initialize a Threaded Connection Pool to share connections safely across threads
try:
    # Convert DATABASE_URL connection string into params if needed, or psycopg2 handles it directly
    pool = ThreadedConnectionPool(minconn=1, maxconn=20, dsn=DATABASE_URL)
    print("Database connection pool initialized successfully.")
except Exception as e:
    print(f"Error initializing database connection pool: {e}")
    pool = None

# FastAPI dependency to obtain a connection and release it back to the pool when done
def get_db():
    if pool is None:
        raise Exception("Database pool is not initialized")
    conn = pool.getconn()
    try:
        # Set autocommit to True so we don't have to manually call commit() on SELECTs
        conn.autocommit = True
        yield conn
    finally:
        pool.putconn(conn)

# Helper to obtain a dictionary cursor for clean key-value row retrieval
def get_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)
