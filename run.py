import socket
import uvicorn

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 60)
    print("🚕 Запуск приложения «Дневник смен водителя»")
    print("=" * 60)
    print(f"📍 На компьютере (ПК):      http://127.0.0.1:8000")
    print(f"📱 С телефона (Wi-Fi):       http://{local_ip}:8000")
    print(f"📑 Swagger API:             http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)

