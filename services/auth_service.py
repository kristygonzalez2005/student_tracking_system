from config import get_connection
import getpass

def iniciar_sesion():
    conn = get_connection()
    cursor = conn.cursor()

    username = input("Usuario: ")
    password = getpass.getpass("Contraseña: ")

    cursor.execute("""
        SELECT u.*, r.nombre as rol_nombre
        FROM usuario_sistema u
        JOIN rol r ON u.id_rol = r.id_rol
        WHERE u.username = ? AND u.password = ? AND u.estado = 'activo'
    """, (username, password))

    usuario = cursor.fetchone()
    conn.close()

    if usuario:
        print(f"✅ Bienvenido {usuario['nombre']} - Rol: {usuario['rol_nombre']}")
        return usuario
    else:
        print("❌ Usuario o contraseña incorrectos")
        return None