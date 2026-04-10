import requests
import hashlib
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime

# CONFIG
URL = "https://www.correoargentino.com.ar/sites/all/modules/custom/ca_forms/api/wsFacade.php"
TRACKING_ID = "000136841967E8PE23IC101"
WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQANG9zM7c/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=reQlEzH4hYqhxLKOyzbeNx1rcmvP6EBIFaavGz82d-U"
STATE_FILE = "estado.json"

HEADERS = {
    "accept": "text/html, */*; q=0.01",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-requested-with": "XMLHttpRequest",
    "referrer": "https://www.correoargentino.com.ar/"
}

def fetch_data():
    data = f"action=ecommerce&id={TRACKING_ID}"
    response = requests.post(URL, headers=HEADERS, data=data, timeout=30)
    response.raise_for_status()
    return response.text

def parse_movimientos(html):
    soup = BeautifulSoup(html, "html.parser")
    filas = soup.select("table tbody tr")

    movimientos = []

    for fila in filas:
        celdas = fila.find_all("td")
        if len(celdas) >= 3:
            movimientos.append({
                "fecha": celdas[0].get_text(strip=True),
                "planta": celdas[1].get_text(strip=True),
                "historia": celdas[2].get_text(strip=True),
                "estado": celdas[3].get_text(strip=True) if len(celdas) > 3 else ""
            })

    return movimientos

def hash_movimientos(movs):
    texto = json.dumps(movs, sort_keys=True)
    return hashlib.sha256(texto.encode()).hexdigest()

def cargar_estado():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def guardar_estado(hash_actual, movimientos):
    with open(STATE_FILE, "w") as f:
        json.dump({
            "hash": hash_actual,
            "movimientos": movimientos,
            "fecha": datetime.utcnow().isoformat()
        }, f, indent=2)

def enviar_notificacion(nuevo_mov):
    mensaje = {
        "text": (
            f"📦 Actualización de envío\n\n"
            f"🕒 {nuevo_mov['fecha']}\n"
            f"📍 {nuevo_mov['planta']}\n"
            f"📌 {nuevo_mov['historia']}\n"
            f"📄 {nuevo_mov['estado']}"
        )
    }
    requests.post(WEBHOOK_URL, json=mensaje)

def main():
    try:
        html = fetch_data()
        movimientos = parse_movimientos(html)

        if not movimientos:
            print("No se encontraron movimientos.")
            return

        estado = cargar_estado()
        hash_actual = hash_movimientos(movimientos)

        if estado is None:
            print("Primera ejecución, guardando estado...")
            guardar_estado(hash_actual, movimientos)
            return

        if estado["hash"] != hash_actual:
            print("Cambio detectado!")

            # detectar nuevo movimiento (el más reciente)
            anterior = estado.get("movimientos", [])
            nuevos = [m for m in movimientos if m not in anterior]

            if nuevos:
                # normalmente el primero es el más nuevo
                enviar_notificacion(nuevos[0])
            else:
                # fallback
                enviar_notificacion(movimientos[0])

            guardar_estado(hash_actual, movimientos)
        else:
            print("Sin cambios.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
