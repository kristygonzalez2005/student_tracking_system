import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.registration_service import registrar_estudiante, registrar_ingreso


def menu():
    while True:
        print("\n===== SISTEMA DE ASISTENCIA =====")
        print("1. Registrar estudiante")
        print("2. Escanear QR")
        print("3. Ver estudiantes")
        print("4. Salir")

        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            registrar_estudiante()

        elif opcion == "2":
            qr = input("Escanea QR: ")
            resultado = registrar_ingreso(qr)
            print(resultado)

        elif opcion == "3":
            from config import get_connection
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM estudiante")
            estudiantes = cursor.fetchall()

            for e in estudiantes:
                print(dict(e))

            conn.close()

        elif opcion == "4":
            print("👋 Saliendo...")
            break

        else:
            print("❌ Opción inválida")


if __name__ == "__main__":
    menu()