import  qrcode

def generar_qr(codigo, nombre_archivo):
    qr = qrcode.make(codigo)
    qr.save(nombre_archivo)
    from utils.qr_generator import generar_qr


