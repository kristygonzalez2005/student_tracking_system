from flask import Flask, render_template, request, redirect, url_for, session, send_file
from config import get_connection
from scanner import escanear_qr
from services.registration_service import registrar_ingreso
from app import exportar_historial_pdf
import os
import qrcode

app = Flask(__name__)
app.secret_key = "clave_secreta_proyecto"


# -------------------------
# INDEX (PRIMERA PANTALLA)
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")

# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.*, r.nombre AS rol_nombre
            FROM usuario_sistema u
            JOIN rol r ON u.id_rol = r.id_rol
            WHERE u.username = ? AND u.password = ? AND u.estado = 'activo'
        """, (username, password))

        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session["usuario_id"] = usuario["id_usuario"]
            session["nombre"] = usuario["nombre"]
            session["rol"] = usuario["rol_nombre"]

            if usuario["rol_nombre"] == "Portero":
                return redirect(url_for("panel_portero"))
            else:
                return redirect(url_for("panel_coordinador"))

        return render_template("login.html", error="Usuario o contraseña incorrectos")

    return render_template("login.html")

# -------------------------
# PORTERO
# -----------------------
@app.route("/portero")
def panel_portero():
    if "rol" not in session or session["rol"] != "Portero":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    # 🔥 CONTAR ENTRADAS HOY
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM evento_asistencia
        WHERE tipo = 'entrada'
        AND DATE(timestamp) = DATE('now')
    """)
    entradas_hoy = cursor.fetchone()["total"]

    # 🔥 CONTAR SALIDAS HOY
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM evento_asistencia
        WHERE tipo = 'salida'
        AND DATE(timestamp) = DATE('now')
    """)
    salidas_hoy = cursor.fetchone()["total"]

    conn.close()

    return render_template(
        "portero.html",
        nombre=session["nombre"],
        resultado=None,
        entradas_hoy=entradas_hoy,
        salidas_hoy=salidas_hoy
    )
    # -------------------------
# ESCANEAR QR
# -------------------------
@app.route("/portero/escanear")
def escanear_qr_web():
    if "rol" not in session or session["rol"] != "Portero":
        return redirect(url_for("login"))

    usuario = {"nombre": session["nombre"]}

    qr = escanear_qr()

    if qr:
        resultado = registrar_ingreso(qr, usuario)
    else:
        resultado = "❌ No se detectó ningún QR"

    # 🔥 ACTUALIZAR CONTADORES
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM evento_asistencia
        WHERE tipo = 'entrada'
        AND DATE(timestamp) = DATE('now')
    """)
    entradas_hoy = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM evento_asistencia
        WHERE tipo = 'salida'
        AND DATE(timestamp) = DATE('now')
    """)
    salidas_hoy = cursor.fetchone()["total"]

    conn.close()

    return render_template(
        "portero.html",
        nombre=session["nombre"],
        resultado=resultado,
        entradas_hoy=entradas_hoy,
        salidas_hoy=salidas_hoy
    )
# -------------------------
# PANEL COORDINADOR / ADMIN / RECTORA
# -------------------------
@app.route("/coordinador")
def panel_coordinador():
    if "rol" not in session or session["rol"] not in ["Coordinador", "Administrador", "Rectora"]:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    # Total estudiantes
    cursor.execute("SELECT COUNT(*) AS total FROM estudiante")
    total_estudiantes = cursor.fetchone()["total"]

    # Total entradas
    cursor.execute("SELECT COUNT(*) AS total FROM evento_asistencia WHERE tipo = 'entrada'")
    total_entradas = cursor.fetchone()["total"]

    # Total salidas
    cursor.execute("SELECT COUNT(*) AS total FROM evento_asistencia WHERE tipo = 'salida'")
    total_salidas = cursor.fetchone()["total"]

    # Total eventos
    total_eventos = total_entradas + total_salidas

    # Porcentajes
    if total_eventos > 0:
        porcentaje_entradas = round((total_entradas / total_eventos) * 100, 1)
        porcentaje_salidas = round((total_salidas / total_eventos) * 100, 1)
    else:
        porcentaje_entradas = 0
        porcentaje_salidas = 0

    conn.close()

    return render_template(
        "coordinador.html",
        nombre=session["nombre"],
        rol=session["rol"],
        total_estudiantes=total_estudiantes,
        total_entradas=total_entradas,
        total_salidas=total_salidas,
        total_eventos=total_eventos,
        porcentaje_entradas=porcentaje_entradas,
        porcentaje_salidas=porcentaje_salidas
    )


# -------------------------
# ESTUDIANTES
# -------------------------
@app.route("/coordinador/estudiantes")
def ver_estudiantes_web():
    if "rol" not in session or session["rol"] not in ["Coordinador", "Administrador", "Rectora"]:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.id_estudiante, e.documento, e.nombre, e.grado, e.estado,
               a.nombre AS acudiente_nombre
        FROM estudiante e
        LEFT JOIN acudiente a ON e.id_estudiante = a.id_estudiante
        ORDER BY e.nombre ASC
    """)
    estudiantes = cursor.fetchall()

    conn.close()

    return render_template(
        "estudiantes.html",
        estudiantes=estudiantes,
        nombre=session["nombre"]
    )


@app.route("/coordinador/registrar", methods=["GET", "POST"])
def registrar_estudiante_web():
    if "rol" not in session or session["rol"] not in ["Coordinador", "Administrador", "Rectora"]:
        return redirect(url_for("login"))

    mensaje = None

    if request.method == "POST":
        documento = request.form["documento"].strip()
        nombre = request.form["nombre"].strip()
        grado = request.form["grado"].strip()
        nombre_acudiente = request.form["nombre_acudiente"].strip()
        telefono = request.form["telefono"].strip()
        parentesco = request.form["parentesco"].strip()
        email = request.form["email"].strip()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM estudiante WHERE documento = ?", (documento,))
        existe = cursor.fetchone()

        if existe:
            mensaje = "⚠️ Ya existe un estudiante con ese documento"
        else:
            qr_hash = f"STU_{documento}"

            carpeta_qr = "qr_codes"
            os.makedirs(carpeta_qr, exist_ok=True)

            ruta_qr = os.path.join(carpeta_qr, f"{documento}.png")
            img = qrcode.make(qr_hash)
            img.save(ruta_qr)

            cursor.execute("""
                INSERT INTO estudiante (documento, nombre, grado, estado, qr_hash)
                VALUES (?, ?, ?, 'activo', ?)
            """, (documento, nombre, grado, qr_hash))

            id_estudiante = cursor.lastrowid

            cursor.execute("""
                INSERT INTO acudiente (nombre, telefono, parentesco, email, estado, id_estudiante)
                VALUES (?, ?, ?, ?, 'activo', ?)
            """, (nombre_acudiente, telefono, parentesco, email, id_estudiante))

            conn.commit()
            mensaje = "✅ Estudiante registrado correctamente y QR generado"

        conn.close()

    return render_template(
        "registrar_estudiante.html",
        mensaje=mensaje,
        nombre=session["nombre"]
    )


@app.route("/coordinador/ver_qr/<documento>")
def ver_qr_estudiante(documento):
    if "rol" not in session or session["rol"] not in ["Coordinador", "Administrador", "Rectora"]:
        return redirect(url_for("login"))

    ruta_qr = os.path.join("qr_codes", f"{documento}.png")

    if not os.path.exists(ruta_qr):
        return "QR no encontrado", 404

    return send_file(ruta_qr, mimetype="image/png")


@app.route("/coordinador/editar_estudiante/<int:id_estudiante>", methods=["GET", "POST"])
def editar_estudiante(id_estudiante):
    if "rol" not in session or session["rol"] not in ["Coordinador", "Administrador", "Rectora"]:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        nuevo_documento = request.form["documento"].strip()
        nombre = request.form["nombre"].strip()
        grado = request.form["grado"].strip()
        estado = request.form["estado"].strip()

        nombre_acudiente = request.form["nombre_acudiente"].strip()
        telefono = request.form["telefono"].strip()
        parentesco = request.form["parentesco"].strip()
        email = request.form["email"].strip()

        cursor.execute("""
            SELECT documento
            FROM estudiante
            WHERE id_estudiante = ?
        """, (id_estudiante,))
        estudiante_actual = cursor.fetchone()

        if not estudiante_actual:
            conn.close()
            return redirect(url_for("ver_estudiantes_web"))

        documento_anterior = estudiante_actual["documento"]
        qr_hash = f"STU_{nuevo_documento}"

        cursor.execute("""
            UPDATE estudiante
            SET documento = ?, nombre = ?, grado = ?, estado = ?, qr_hash = ?
            WHERE id_estudiante = ?
        """, (nuevo_documento, nombre, grado, estado, qr_hash, id_estudiante))

        cursor.execute("""
            UPDATE acudiente
            SET nombre = ?, telefono = ?, parentesco = ?, email = ?
            WHERE id_estudiante = ?
        """, (nombre_acudiente, telefono, parentesco, email, id_estudiante))

        carpeta_qr = "qr_codes"
        os.makedirs(carpeta_qr, exist_ok=True)

        ruta_qr_anterior = os.path.join(carpeta_qr, f"{documento_anterior}.png")
        ruta_qr_nueva = os.path.join(carpeta_qr, f"{nuevo_documento}.png")

        if documento_anterior != nuevo_documento and os.path.exists(ruta_qr_anterior):
            os.remove(ruta_qr_anterior)

        img = qrcode.make(qr_hash)
        img.save(ruta_qr_nueva)

        conn.commit()
        conn.close()

        return redirect(url_for("ver_estudiantes_web"))

    cursor.execute("""
        SELECT e.id_estudiante, e.documento, e.nombre, e.grado, e.estado, e.qr_hash,
               a.nombre AS nombre_acudiente, a.telefono, a.parentesco, a.email
        FROM estudiante e
        LEFT JOIN acudiente a ON e.id_estudiante = a.id_estudiante
        WHERE e.id_estudiante = ?
    """, (id_estudiante,))
    estudiante = cursor.fetchone()

    conn.close()

    if not estudiante:
        return redirect(url_for("ver_estudiantes_web"))

    return render_template(
        "editar_estudiante.html",
        estudiante=estudiante,
        nombre=session["nombre"]
    )


@app.route("/coordinador/eliminar_estudiante/<int:id_estudiante>", methods=["POST"])
def eliminar_estudiante_web(id_estudiante):
    if "rol" not in session or session["rol"] not in ["Coordinador", "Administrador", "Rectora"]:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT documento
            FROM estudiante
            WHERE id_estudiante = ?
        """, (id_estudiante,))
        estudiante = cursor.fetchone()

        if not estudiante:
            conn.close()
            return redirect(url_for("ver_estudiantes_web"))

        documento = estudiante["documento"]

        cursor.execute("DELETE FROM notificacion WHERE id_estudiante = ?", (id_estudiante,))
        cursor.execute("DELETE FROM evento_asistencia WHERE id_estudiante = ?", (id_estudiante,))
        cursor.execute("DELETE FROM acudiente WHERE id_estudiante = ?", (id_estudiante,))
        cursor.execute("DELETE FROM estudiante WHERE id_estudiante = ?", (id_estudiante,))

        conn.commit()
        conn.close()

        ruta_qr = os.path.join("qr_codes", f"{documento}.png")
        if os.path.exists(ruta_qr):
            os.remove(ruta_qr)

    except Exception as e:
        conn.rollback()
        conn.close()
        return f"Error al eliminar estudiante: {str(e)}"

    return redirect(url_for("ver_estudiantes_web"))


# -------------------------
# USUARIOS
# -------------------------
@app.route("/coordinador/usuarios")
def ver_usuarios():
    if "rol" not in session or session["rol"] != "Administrador":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.id_usuario, u.username, u.nombre, r.nombre AS rol, u.estado
        FROM usuario_sistema u
        JOIN rol r ON u.id_rol = r.id_rol
        ORDER BY u.nombre ASC
    """)
    usuarios = cursor.fetchall()

    conn.close()

    return render_template(
        "usuarios.html",
        usuarios=usuarios,
        nombre=session["nombre"]
    )


@app.route("/coordinador/registrar_usuario", methods=["GET", "POST"])
def registrar_usuario_web():
    if "rol" not in session or session["rol"] != "Administrador":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id_rol, nombre FROM rol ORDER BY nombre ASC")
    roles = cursor.fetchall()

    mensaje = None

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        nombre = request.form["nombre"].strip()
        id_rol = request.form["id_rol"]

        cursor.execute("SELECT * FROM usuario_sistema WHERE username = ?", (username,))
        existe = cursor.fetchone()

        if existe:
            mensaje = "⚠️ Ya existe un usuario con ese nombre"
        else:
            cursor.execute("""
                INSERT INTO usuario_sistema (username, password, nombre, id_rol, estado)
                VALUES (?, ?, ?, ?, 'activo')
            """, (username, password, nombre, id_rol))

            conn.commit()
            mensaje = "✅ Usuario creado correctamente"

    conn.close()

    return render_template(
        "registrar_usuario.html",
        roles=roles,
        mensaje=mensaje,
        nombre=session["nombre"]
    )


@app.route("/coordinador/desactivar_usuario/<int:id_usuario>", methods=["POST"])
def desactivar_usuario(id_usuario):
    if "rol" not in session or session["rol"] != "Administrador":
        return redirect(url_for("login"))

    if session.get("usuario_id") == id_usuario:
        return redirect(url_for("ver_usuarios"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuario_sistema
        SET estado = 'inactivo'
        WHERE id_usuario = ?
    """, (id_usuario,))

    conn.commit()
    conn.close()

    return redirect(url_for("ver_usuarios"))


# -------------------------
# HISTORIAL
# -------------------------
@app.route("/coordinador/historial")
def ver_historial_web():
    if "rol" not in session or session["rol"] not in ["Coordinador", "Administrador", "Rectora"]:
        return redirect(url_for("login"))

    filtro_estudiante = request.args.get("estudiante", "")
    filtro_fecha = request.args.get("fecha", "")

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT e.nombre, e.grado, ev.tipo, ev.timestamp
        FROM evento_asistencia ev
        JOIN estudiante e ON ev.id_estudiante = e.id_estudiante
        WHERE 1=1
    """

    params = []

    if filtro_estudiante:
        query += " AND e.nombre LIKE ?"
        params.append(f"%{filtro_estudiante}%")

    if filtro_fecha:
        query += " AND DATE(ev.timestamp) = ?"
        params.append(filtro_fecha)

    query += " ORDER BY ev.timestamp DESC"

    cursor.execute(query, params)
    historial = cursor.fetchall()

    # 🔥 CONTADORES HOY
    cursor.execute("""
        SELECT COUNT(*) FROM evento_asistencia
        WHERE tipo = 'entrada' AND DATE(timestamp) = DATE('now')
    """)
    entradas_hoy = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM evento_asistencia
        WHERE tipo = 'salida' AND DATE(timestamp) = DATE('now')
    """)
    salidas_hoy = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "historial.html",
        historial=historial,
        entradas_hoy=entradas_hoy,
        salidas_hoy=salidas_hoy
    )
# -------------------------
# NOTIFICACIONES
# -------------------------
@app.route("/coordinador/notificaciones")
def ver_notificaciones_web():
    if "rol" not in session or session["rol"] not in ["Coordinador", "Administrador", "Rectora"]:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.nombre AS estudiante, a.nombre AS acudiente,
               n.tipo, n.mensaje, n.estado, n.enviado_at
        FROM notificacion n
        JOIN estudiante e ON n.id_estudiante = e.id_estudiante
        JOIN acudiente a ON n.id_acudiente = a.id_acudiente
        ORDER BY n.enviado_at DESC
    """)
    notificaciones = cursor.fetchall()

    conn.close()

    return render_template(
        "notificaciones.html",
        notificaciones=notificaciones,
        nombre=session["nombre"]
    )


# -------------------------
# EXPORTAR PDF
# -------------------------
@app.route("/coordinador/exportar-pdf")
def exportar_pdf_web():
    if "rol" not in session or session["rol"] not in ["Coordinador", "Administrador", "Rectora"]:
        return redirect(url_for("login"))

    exportar_historial_pdf()
    ruta_pdf = os.path.join(os.getcwd(), "historial_asistencias.pdf")
    return send_file(ruta_pdf, as_attachment=True)


# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)