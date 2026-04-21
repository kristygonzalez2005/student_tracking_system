from config import get_connection
from utils.qr_generator import generar_qr
from services.email_service import enviar_correo
from datetime import datetime


def registrar_ingreso(qr_code, usuario):
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

    ahora = datetime.now()
    fecha = ahora.strftime("%d/%m/%Y")
    hora = ahora.strftime("%I:%M %p")

    punto_acceso = "Portería Principal"
    nombre_portero = usuario["nombre"]

    cursor.execute("""
        INSERT INTO evento_asistencia (id_estudiante, id_punto, tipo, estado)
        VALUES (?, 1, ?, 'registrado')
    """, (estudiante["id_estudiante"], tipo_evento))

    cursor.execute("""
        SELECT * FROM acudiente
        WHERE id_estudiante = ?
    """, (estudiante["id_estudiante"],))
    acudiente = cursor.fetchone()

    mensaje_notificacion = ""

    if acudiente:
        asunto = "Notificación de asistencia estudiantil"
        cuerpo = (
            f"Hola {acudiente['nombre']},\n\n"
            f"Le informamos que el estudiante {estudiante['nombre']} "
            f"del grado {estudiante['grado']} "
            f"ha registrado {tipo_evento} en la institución.\n\n"
            f"📅 Fecha: {fecha}\n"
            f"⏰ Hora del registro: {hora}\n"
            f"📍 Punto de acceso: {punto_acceso}\n"
            f"👤 Registrado por: {nombre_portero}\n\n"
            f"No responda este correo, este es un mensaje generado automáticamente."
        )

        exito_correo, respuesta_correo = enviar_correo(
            acudiente["email"],
            asunto,
            cuerpo
        )

        estado_notificacion = "enviado" if exito_correo else "fallido"

        cursor.execute("""
            INSERT INTO notificacion (id_estudiante, id_acudiente, tipo, mensaje, estado, enviado_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (
            estudiante["id_estudiante"],
            acudiente["id_acudiente"],
            tipo_evento,
            mensaje,
            estado_notificacion
        ))

        if exito_correo:
            mensaje_notificacion = (
                f"📧 Correo enviado a {acudiente['nombre']} "
                f"({acudiente['email']})"
            )
        else:
            mensaje_notificacion = (
                f"⚠️ No se pudo enviar el correo a {acudiente['email']}. "
                f"Detalle: {respuesta_correo}"
            )
    else:
        mensaje_notificacion = "⚠️ No hay acudiente asociado a este estudiante"

    conn.commit()
    conn.close()

    return f"✅ {mensaje}\n{mensaje_notificacion}"


def registrar_estudiante():
    conn = get_connection()
    cursor = conn.cursor()

    documento = input("Documento del estudiante: ")
    nombre = input("Nombre del estudiante: ")
    grado = input("Grado: ")

    qr_hash = f"STU_{documento}"

    cursor.execute("SELECT * FROM estudiante WHERE documento = ?", (documento,))
    existe = cursor.fetchone()

    if existe:
        conn.close()
        print("⚠️ Ya existe un estudiante con ese documento")
        return

    cursor.execute("""
        INSERT INTO estudiante (documento, nombre, grado, estado, qr_hash)
        VALUES (?, ?, ?, 'activo', ?)
    """, (documento, nombre, grado, qr_hash))

    id_estudiante = cursor.lastrowid

    nombre_acudiente = input("Nombre del acudiente: ")
    telefono = input("Teléfono del acudiente: ")
    parentesco = input("Parentesco: ")
    email = input("Email del acudiente: ")

    cursor.execute("""
        INSERT INTO acudiente (nombre, telefono, parentesco, email, estado, id_estudiante)
        VALUES (?, ?, ?, ?, 'activo', ?)
    """, (nombre_acudiente, telefono, parentesco, email, id_estudiante))

    conn.commit()
    conn.close()

    ruta = f"qr_codes/{documento}.png"
    generar_qr(qr_hash, ruta)

    print("✅ Estudiante registrado correctamente")
    print("✅ Acudiente registrado correctamente")
    print(f"✅ QR generado en {ruta}")
    print(f"📌 Código QR asignado: {qr_hash}")


def actualizar_estudiante():
    conn = get_connection()
    cursor = conn.cursor()

    documento_buscar = input("Ingrese el documento del estudiante a actualizar: ")

    cursor.execute("""
        SELECT * FROM estudiante
        WHERE documento = ?
    """, (documento_buscar,))
    estudiante = cursor.fetchone()

    if not estudiante:
        conn.close()
        print("❌ Estudiante no encontrado")
        return

    print(f"Estudiante encontrado: {estudiante['nombre']} - Grado {estudiante['grado']}")

    nuevo_nombre = input("Nuevo nombre del estudiante: ")
    nuevo_grado = input("Nuevo grado: ")

    cursor.execute("""
        UPDATE estudiante
        SET nombre = ?, grado = ?
        WHERE id_estudiante = ?
    """, (nuevo_nombre, nuevo_grado, estudiante["id_estudiante"]))

    cursor.execute("""
        SELECT * FROM acudiente
        WHERE id_estudiante = ?
    """, (estudiante["id_estudiante"],))
    acudiente = cursor.fetchone()

    if acudiente:
        nuevo_nombre_acudiente = input("Nuevo nombre del acudiente: ")
        nuevo_telefono = input("Nuevo teléfono: ")
        nuevo_parentesco = input("Nuevo parentesco: ")
        nuevo_email = input("Nuevo email: ")

        cursor.execute("""
            UPDATE acudiente
            SET nombre = ?, telefono = ?, parentesco = ?, email = ?
            WHERE id_acudiente = ?
        """, (
            nuevo_nombre_acudiente,
            nuevo_telefono,
            nuevo_parentesco,
            nuevo_email,
            acudiente["id_acudiente"]
        ))

    conn.commit()
    conn.close()

    print("✅ Estudiante y acudiente actualizados correctamente")


def eliminar_estudiante():
    conn = get_connection()
    cursor = conn.cursor()

    documento_buscar = input("Ingrese el documento del estudiante a eliminar: ")

    cursor.execute("""
        SELECT * FROM estudiante
        WHERE documento = ?
    """, (documento_buscar,))
    estudiante = cursor.fetchone()

    if not estudiante:
        conn.close()
        print("❌ Estudiante no encontrado")
        return

    confirmar = input(f"¿Está seguro de eliminar a {estudiante['nombre']}? (s/n): ")

    if confirmar.lower() != "s":
        conn.close()
        print("⚠️ Operación cancelada")
        return

    id_estudiante = estudiante["id_estudiante"]

    cursor.execute("""
        DELETE FROM notificacion
        WHERE id_estudiante = ?
    """, (id_estudiante,))

    cursor.execute("""
        DELETE FROM evento_asistencia
        WHERE id_estudiante = ?
    """, (id_estudiante,))

    cursor.execute("""
        DELETE FROM acudiente
        WHERE id_estudiante = ?
    """, (id_estudiante,))

    cursor.execute("""
        DELETE FROM estudiante
        WHERE id_estudiante = ?
    """, (id_estudiante,))

    conn.commit()
    conn.close()

    print("✅ Estudiante, acudiente y registros asociados eliminados correctamente")