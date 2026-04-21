import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_REMITENTE = os.getenv("EMAIL_REMITENTE")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def enviar_correo(destino, asunto, mensaje):

    if not EMAIL_REMITENTE or not EMAIL_PASSWORD:
        return False, "Faltan variables de entorno EMAIL_REMITENTE o EMAIL_PASSWORD"

    try:
        correo = MIMEMultipart()
        correo["From"] = EMAIL_REMITENTE
        correo["To"] = destino
        correo["Subject"] = asunto

        correo.attach(MIMEText(mensaje, "plain", "utf-8"))

        servidor = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        servidor.starttls()
        servidor.login(EMAIL_REMITENTE, EMAIL_PASSWORD)
        servidor.sendmail(EMAIL_REMITENTE, destino, correo.as_string())
        servidor.quit()

        return True, f"Correo enviado a {destino}"

    except Exception as e:
        return False, f"Error al enviar correo: {e}"