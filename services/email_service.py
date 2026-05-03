import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Cargar variables .env
load_dotenv()

SMTP_SERVER = "smtp.gmail.com"

# 🔥 usamos 465 (más estable que 587)
SMTP_PORT = 465  

EMAIL_REMITENTE = os.getenv("EMAIL_REMITENTE")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def enviar_correo(destino, asunto, mensaje):

    # 🔍 Validación
    if not EMAIL_REMITENTE or not EMAIL_PASSWORD:
        return False, "❌ Faltan variables EMAIL_REMITENTE o EMAIL_PASSWORD"

    try:
        correo = MIMEMultipart()
        correo["From"] = EMAIL_REMITENTE
        correo["To"] = destino
        correo["Subject"] = asunto

        correo.attach(MIMEText(mensaje, "plain", "utf-8"))

        # 🔥 conexión segura SSL (evita bloqueos de red)
        servidor = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)

        servidor.login(EMAIL_REMITENTE, EMAIL_PASSWORD)
        servidor.sendmail(EMAIL_REMITENTE, destino, correo.as_string())
        servidor.quit()

        return True, f"📧 Correo enviado a {destino}"

    except smtplib.SMTPAuthenticationError:
        return False, "❌ Error de autenticación (revisa contraseña de aplicación)"

    except smtplib.SMTPConnectError:
        return False, "❌ No se pudo conectar al servidor SMTP"

    except Exception as e:
        return False, f"❌ Error general: {str(e)}"