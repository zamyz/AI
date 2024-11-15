from flask import Flask, request, jsonify, render_template
import sqlite3
import os
import requests

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# API Key Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_actual_groq_api_key_here")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Inisialisasi database SQLite
def inisialisasi_database():
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS riwayat_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pesan_pengguna TEXT,
            balasan_ai TEXT,
            waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

# Panggil inisialisasi database
inisialisasi_database()

@app.route("/")
def beranda():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def balas_chat():
    pesan_pengguna = request.json.get("message", "").strip()
    if not pesan_pengguna:
        return jsonify({"error": "Pesan tidak boleh kosong"}), 400

    # Permintaan ke API Groq
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "Anda adalah asisten pertanian yang membantu."},
            {"role": "user", "content": pesan_pengguna}
        ],
        "temperature": 0.5,
        "max_tokens": 512,
        "top_p": 1
    }

    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        groq_response = response.json()

        # Debugging: Cetak respons API Groq
        print("Respons API Groq:", groq_response)

        # Ekstraksi balasan dari API
        choices = groq_response.get("choices")
        if not choices or len(choices) == 0:
            return jsonify({"reply": "Maaf, tidak ada balasan dari AI."})

        # Ambil isi balasan dari field "content"
        balasan = choices[0].get("message", {}).get("content", "").strip()
        if not balasan:
            balasan = "Maaf, saya tidak bisa memberikan jawaban untuk pertanyaan Anda."

        return jsonify({"reply": balasan})

    except requests.exceptions.RequestException as e:
        print(f"Error saat mengakses API Groq: {e}")
        return jsonify({"error": f"Gagal terhubung ke API Groq: {e}"}), 500

    except Exception as e:
        print(f"Error tak terduga: {e}")
        return jsonify({"error": f"Kesalahan tak terduga: {e}"}), 500

@app.route("/riwayat", methods=["GET"])
def lihat_riwayat():
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pesan_pengguna, balasan_ai FROM riwayat_chat ORDER BY waktu DESC")
            riwayat = [{"pesan_pengguna": row[0], "balasan_ai": row[1]} for row in cursor.fetchall()]
        return jsonify({"riwayat": riwayat})
    except Exception as e:
        return jsonify({"error": f"Gagal memuat riwayat: {e}"}), 500

@app.route("/save_to_history", methods=["POST"])
def save_to_history():
    try:
        data = request.json.get("chats", [])
        if not data:
            return jsonify({"error": "Tidak ada data untuk disimpan."}), 400

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            for chat in data:
                # Gunakan nilai default kosong jika None
                pesan_pengguna = (chat.get("pesan_pengguna") or "").strip()
                balasan_ai = (chat.get("balasan_ai") or "").strip()
                if pesan_pengguna or balasan_ai:
                    cursor.execute(
                        "INSERT INTO riwayat_chat (pesan_pengguna, balasan_ai) VALUES (?, ?)",
                        (pesan_pengguna, balasan_ai)
                    )
            conn.commit()

        return jsonify({"message": "Obrolan berhasil disimpan ke riwayat."}), 200
    except Exception as e:
        print(f"Error saat menyimpan riwayat: {e}")
        return jsonify({"error": f"Gagal menyimpan obrolan: {e}"}), 500


@app.route("/hapus_riwayat", methods=["POST"])
def hapus_riwayat():
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM riwayat_chat")
            conn.commit()
        return jsonify({"message": "Riwayat chat berhasil dihapus."}), 200
    except Exception as e:
        return jsonify({"error": f"Gagal menghapus riwayat: {e}"}), 500
if __name__ == "__main__":
    app.run(debug=True)
