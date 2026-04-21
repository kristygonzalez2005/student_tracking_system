import cv2


def escanear_qr():
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        data, bbox, _ = detector.detectAndDecode(frame)

        if data:
            cap.release()
            cv2.destroyAllWindows()
            return data

        cv2.imshow("Escaneando QR...", frame)

        if cv2.waitKey(1) == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    return None