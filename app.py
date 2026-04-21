from services.auth_service import iniciar_sesion
from services.registration_service import (
    registrar_estudiante,
    registrar_ingreso,
    actualizar_estudiante,
    eliminar_estudiante
)
from scanner import escanear_qr
from config import get_connection
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors


def ver_estudiantes():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM estudiante")
    estudiantes = cursor.fetchall()

    print("\n===== LISTA DE ESTUDIANTES =====")
    for e in estudiantes:
        print(dict(e))

    conn.close()


def ver_historial():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.nombre, e.grado, ev.tipo, ev.timestamp
        FROM evento_asistencia ev
        JOIN estudiante e ON ev.id_estudiante = e.id_estudiante
        ORDER BY ev.timestamp DESC
    """)

    historial = cursor.fetchall()

    print("\n===== HISTORIAL DE ASISTENCIAS =====")
    if historial:
        for registro in historial:
            print(
                f"Estudiante: {registro['nombre']} | "
                f"Grado: {registro['grado']} | "
                f"Evento: {registro['tipo']} | "
                f"Fecha: {registro['timestamp']}"
            )
    else:
        print("No hay registros.")

    conn.close()


def ver_notificaciones():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT n.id_notificacion, e.nombre AS estudiante, a.nombre AS acudiente,
               n.tipo, n.mensaje, n.estado, n.enviado_at
        FROM notificacion n
        JOIN estudiante e ON n.id_estudiante = e.id_estudiante
        JOIN acudiente a ON n.id_acudiente = a.id_acudiente
        ORDER BY n.enviado_at DESC
    """)

    notificaciones = cursor.fetchall()

    print("\n===== NOTIFICACIONES =====")
    if notificaciones:
        for n in notificaciones:
            print(dict(n))
    else:
        print("No hay notificaciones registradas.")

    conn.close()


def exportar_historial_pdf():
    conn = get_connection()
    cursor = conn.cursor()

    # Historial detallado
    cursor.execute("""
        SELECT e.nombre, e.grado, ev.tipo, ev.timestamp
        FROM evento_asistencia ev
        JOIN estudiante e ON ev.id_estudiante = e.id_estudiante
        ORDER BY ev.timestamp DESC
    """)
    historial = cursor.fetchall()

    # Resumen por estudiante
    cursor.execute("""
        SELECT 
            e.nombre,
            e.grado,
            SUM(CASE WHEN ev.tipo = 'entrada' THEN 1 ELSE 0 END) AS total_entradas,
            SUM(CASE WHEN ev.tipo = 'salida' THEN 1 ELSE 0 END) AS total_salidas
        FROM estudiante e
        LEFT JOIN evento_asistencia ev ON e.id_estudiante = ev.id_estudiante
        GROUP BY e.id_estudiante, e.nombre, e.grado
        ORDER BY e.nombre
    """)
    resumen = cursor.fetchall()

    # Totales generales
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN tipo = 'entrada' THEN 1 ELSE 0 END) AS entradas,
            SUM(CASE WHEN tipo = 'salida' THEN 1 ELSE 0 END) AS salidas
        FROM evento_asistencia
    """)
    totales = cursor.fetchone()

    conn.close()

    nombre_pdf = "historial_asistencias.pdf"
    c = canvas.Canvas(nombre_pdf, pagesize=letter)
    width, height = letter

    margen_x = 40
    y = height - 50

    # Título
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, y, "Historial de Asistencias")

    # Subtítulo
    y -= 25
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.grey)
    c.drawString(margen_x, y, "Reporte generado automáticamente por el sistema")
    c.setFillColor(colors.black)

    # Línea decorativa
    y -= 15
    c.setStrokeColor(colors.darkblue)
    c.setLineWidth(1)
    c.line(margen_x, y, width - margen_x, y)

    # -----------------------------
    # RESUMEN
    # -----------------------------
    y -= 30
    c.setFont("Helvetica-Bold", 13)
    c.drawString(margen_x, y, "Resumen por estudiante")

    y -= 20
    c.setFillColor(colors.lightblue)
    c.rect(margen_x, y - 5, width - 2 * margen_x, 22, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)

    c.drawString(50, y, "Estudiante")
    c.drawString(200, y, "Grado")
    c.drawString(280, y, "Entradas")
    c.drawString(380, y, "Salidas")

    y -= 25
    c.setFont("Helvetica", 10)

    if resumen:
        for i, r in enumerate(resumen):
            if i % 2 == 0:
                c.setFillColorRGB(0.95, 0.95, 0.95)
                c.rect(margen_x, y - 5, width - 2 * margen_x, 18, fill=1, stroke=0)
                c.setFillColor(colors.black)

            c.drawString(50, y, str(r["nombre"]))
            c.drawString(200, y, str(r["grado"]))
            c.drawString(280, y, str(r["total_entradas"] or 0))
            c.drawString(380, y, str(r["total_salidas"] or 0))

            y -= 20

            if y < 100:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica-Bold", 13)
                c.drawString(margen_x, y, "Resumen por estudiante")
                y -= 20

                c.setFillColor(colors.lightblue)
                c.rect(margen_x, y - 5, width - 2 * margen_x, 22, fill=1, stroke=0)
                c.setFillColor(colors.black)
                c.setFont("Helvetica-Bold", 10)

                c.drawString(50, y, "Estudiante")
                c.drawString(200, y, "Grado")
                c.drawString(280, y, "Entradas")
                c.drawString(380, y, "Salidas")

                y -= 25
                c.setFont("Helvetica", 10)
    else:
        c.drawString(margen_x, y, "No hay datos para el resumen.")
        y -= 20

    # Totales generales
    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margen_x, y, f"Total general de entradas: {totales['entradas'] or 0}")
    y -= 18
    c.drawString(margen_x, y, f"Total general de salidas: {totales['salidas'] or 0}")

    # -----------------------------
    # DETALLE DEL HISTORIAL
    # -----------------------------
    y -= 30
    if y < 120:
        c.showPage()
        y = height - 50

    c.setFont("Helvetica-Bold", 13)
    c.drawString(margen_x, y, "Detalle del historial")

    y -= 20
    c.setFillColor(colors.lightblue)
    c.rect(margen_x, y - 5, width - 2 * margen_x, 22, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)

    c.drawString(45, y, "Estudiante")
    c.drawString(160, y, "Grado")
    c.drawString(220, y, "Evento")
    c.drawString(300, y, "Fecha y hora")

    y -= 25
    c.setFont("Helvetica", 9)

    if historial:
        for i, registro in enumerate(historial):
            if i % 2 == 0:
                c.setFillColorRGB(0.95, 0.95, 0.95)
                c.rect(margen_x, y - 5, width - 2 * margen_x, 18, fill=1, stroke=0)
                c.setFillColor(colors.black)

            c.drawString(45, y, str(registro["nombre"]))
            c.drawString(160, y, str(registro["grado"]))
            c.drawString(220, y, str(registro["tipo"]))
            c.drawString(300, y, str(registro["timestamp"]))

            y -= 20

            if y < 60:
                c.showPage()
                y = height - 50

                c.setFont("Helvetica-Bold", 13)
                c.drawString(margen_x, y, "Detalle del historial")
                y -= 20

                c.setFillColor(colors.lightblue)
                c.rect(margen_x, y - 5, width - 2 * margen_x, 22, fill=1, stroke=0)
                c.setFillColor(colors.black)
                c.setFont("Helvetica-Bold", 9)

                c.drawString(45, y, "Estudiante")
                c.drawString(160, y, "Grado")
                c.drawString(220, y, "Evento")
                c.drawString(300, y, "Fecha y hora")

                y -= 25
                c.setFont("Helvetica", 9)
    else:
        c.drawString(margen_x, y, "No hay registros de asistencia.")

    c.save()
    print(f"✅ PDF generado correctamente: {nombre_pdf}")


def menu_portero(usuario):
    while True:
        print("\n===== MENÚ PORTERO =====")
        print("1. Escanear QR")
        print("2. Salir")

        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            print("📷 Abriendo cámara...")
            qr = escanear_qr()

            if qr:
                resultado = registrar_ingreso(qr, usuario)
                print(resultado)
            else:
                print("❌ No se detectó ningún QR")

        elif opcion == "2":
            break

        else:
            print("❌ Opción inválida")


def menu_coordinador():
    while True:
        print("\n===== MENÚ COORDINADOR =====")
        print("1. Ver estudiantes")
        print("2. Ver historial de asistencias")
        print("3. Ver notificaciones")
        print("4. Registrar estudiante")
        print("5. Actualizar estudiante")
        print("6. Eliminar estudiante")
        print("7. Exportar historial a PDF")
        print("8. Salir")

        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            ver_estudiantes()

        elif opcion == "2":
            ver_historial()

        elif opcion == "3":
            ver_notificaciones()

        elif opcion == "4":
            registrar_estudiante()

        elif opcion == "5":
            actualizar_estudiante()

        elif opcion == "6":
            eliminar_estudiante()

        elif opcion == "7":
            exportar_historial_pdf()

        elif opcion == "8":
            break

        else:
            print("❌ Opción inválida")


if __name__ == "__main__":
    usuario = iniciar_sesion()

    if usuario:
        if usuario["rol_nombre"] == "Portero":
            menu_portero(usuario)
        elif usuario["rol_nombre"] in ["Coordinador", "Administrador"]:
            menu_coordinador()
        else:
            print("⚠️ Rol no reconocido")