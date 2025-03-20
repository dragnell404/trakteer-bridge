from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# URL server lokal yang menjalankan app.py
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "https://9b26-103-47-133-127.ngrok-free.app")

@app.route('/trakteer-webhook', methods=['POST'])
def receive_webhook():
    """Menerima webhook dari Trakteer dan meneruskan ke server lokal."""
    try:
        data = request.json

        # 🔹 Pastikan data valid sebelum diteruskan
        if not data or "supporter_message" not in data or "amount" not in data:
            return jsonify({"status": "error", "message": "Data tidak valid"}), 400

        # 🔹 Kirim data ke server lokal yang menjalankan `app.py`
        response = requests.post(f"{LOCAL_SERVER_URL}/trakteer-webhook", json=data)

        return jsonify(response.json()), response.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": f"Server Error: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

