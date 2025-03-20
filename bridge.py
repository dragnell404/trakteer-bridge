from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
import logging

app = Flask(__name__)

# Ambil token Webhook dari environment variable
WEBHOOK_TOKEN = os.getenv("TRAKTEER_WEBHOOK_TOKEN")
# Ambil URL server lokal (app.py di Railway atau Google Cloud)
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "http://localhost:5000")
# Ambil token bot Telegram untuk notifikasi
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))  # Pastikan bertipe integer

# Nominal pembayaran yang valid untuk VIP
VIP_PRICING = {2000: 1, 5000: 3, 10000: 7, 30000: 30}  # {harga: hari VIP}

logging.basicConfig(level=logging.INFO)

def send_telegram_notification(message):
    """Mengirim notifikasi ke Telegram."""
    try:
        logging.info("Mengirim notifikasi ke Telegram...")
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        response = requests.post(telegram_url, json=data)
        if response.status_code == 200:
            logging.info("✅ Notifikasi Telegram berhasil dikirim.")
        else:
            logging.error(f"❌ Gagal mengirim notifikasi Telegram: {response.text}")
    except Exception as e:
        logging.error(f"⚠️ ERROR: {e}")

@app.route('/trakteer-webhook', methods=['POST'])
def receive_webhook():
    """Menerima webhook dari Trakteer, memverifikasi token, dan meneruskan data ke API lokal."""
    try:
        data = request.json
        received_token = request.headers.get("X-Webhook-Token")  # Webhook Token dari Trakteer
        
        print(f"📩 Received token: {received_token}")  # 🔍 Debugging
        print(f"🎯 Expected token: {WEBHOOK_TOKEN}")  # 🔍 Debugging

        # 🔹 Cek apakah token cocok
        if received_token != WEBHOOK_TOKEN:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403

        supporter_message = data["supporter_message"]  # Token pengguna
        amount = data["amount"]  # Nominal pembayaran
        transaction_id = data["transaction_id"]  # ID unik transaksi

        # 🔹 Perbaiki format tanggal
        created_at = data.get("created_at", None)
        if created_at:
            try:
                created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S%z").strftime("%d %B %Y %H:%M:%S")
            except ValueError:
                created_at = "Waktu tidak diketahui"
        else:
            created_at = "Waktu tidak diketahui"

        # 🔹 Jika nominal tidak sesuai, kirim notifikasi ke Telegram
        if amount not in VIP_PRICING:
            error_message = (
                f"⚠️ *Pembayaran Tidak Valid!*\n\n"
                f"📅 *Tanggal:* {created_at}\n"
                f"💰 *Nominal:* {amount} IDR ❌\n"
                f"🎟️ *Token:* `{supporter_message}`\n"
                f"🆔 *Transaksi ID:* `{transaction_id}`\n"
                f"❌ *Gagal Upgrade VIP: Nominal Salah!*"
            )
            send_telegram_notification(error_message)

            return jsonify({
                "status": "error",
                "message": f"Nominal {amount} tidak valid untuk upgrade VIP."
            }), 400

        # 🔹 Kirim data ke server lokal (app.py)
        response = requests.post(f"{LOCAL_SERVER_URL}/trakteer-webhook", json=data)

        if response.status_code == 200:
            # 🔹 Notifikasi ke Telegram jika pembayaran sukses
            success_message = (
                f"✅ *Pembayaran Trakteer Berhasil!*\n\n"
                f"📅 *Tanggal:* {created_at}\n"
                f"💰 *Nominal:* {amount} IDR\n"
                f"🎟️ *Token:* `{supporter_message}`\n"
                f"🆔 *Transaksi ID:* `{transaction_id}`\n"
                f"🏆 *VIP diperpanjang {VIP_PRICING[amount]} hari!*"
            )
            send_telegram_notification(success_message)

        return jsonify(response.json()), response.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": f"Server Error: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

