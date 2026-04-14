from config import get_connection
from utils.qr_generator import generar_qr  


def registrar_ingreso(qr_code):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM estudiante WHERE qr_hash = ?", (qr_code,))
    estudiante = cursor.fetchone()

    if not estudiante:
        conn.close()
        return "❌ Estudiante no encontrado"

    cursor.execute("""
        SELECT * FROM evento_asistencia
        WHERE id_estudiante = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (estudiante["id_estudiante"],))

    ultimo_evento = cursor.fetchone()

    if not ultimo_evento or ultimo_evento["tipo"] == "salida":
        tipo_evento = "entrada"
        mensaje = f"{estudiante['nombre']} ingresó al colegio"
    else:
        tipo_evento = "salida"
        mensaje = f"{estudiante['nombre']} salió del colegio"

    cursor.execute("""
        INSERT INTO evento_asistencia (id_estudiante, id_punto, tipo, estado)
        VALUES (?, 1, ?, 'registrado')
    """, (estudiante["id_estudiante"], tipo_evento))

    cursor.execute("SELECT * FROM acudiente WHERE id_acudiente = 1")
    acudiente = cursor.fetchone()

    if acudiente:
        cursor.execute("""
            INSERT INTO notificacion (id_estudiante, id_acudiente, tipo, mensaje, estado, enviado_at)
            VALUES (?, ?, ?, ?, 'enviado', datetime('now'))
        """, (estudiante["id_estudiante"], acudiente["id_acudiente"], tipo_evento, mensaje))

    conn.commit()
    conn.close()

    return f"✅ {mensaje}"


def registrar_estudiante():
    conn = get_connection()
    cursor = conn.cursor()

    documento = input("Documento: ")
    nombre = input("Nombre: ")
    grado = input("Grado: ")

    qr_hash = f"STU_{documento}"

    cursor.execute("""
        INSERT INTO estudiante (documento, nombre, grado, estado, qr_hash)
        VALUES (?, ?, ?, 'activo', ?)
    """, (documento, nombre, grado, qr_hash))

    conn.commit()
    conn.close()

    ruta = f"qr_codes/{nombre}.png"
    generar_qr(qr_hash, ruta)

    print(f"✅ Estudiante registrado y QR generado en {ruta}")
    