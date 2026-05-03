import sqlite3

DATABASE = "school_tracking.db"

def get_connection():
    conn = sqlite3.connect(
        DATABASE,
        timeout=10,                # 🔥 evita bloqueo inmediato
        check_same_thread=False    # 🔥 permite múltiples accesos
    )

    conn.row_factory = sqlite3.Row

    # 🔥 MODO WAL (clave para evitar bloqueos)
    conn.execute("PRAGMA journal_mode=WAL;")

    return conn