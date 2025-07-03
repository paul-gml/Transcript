import os
import tempfile
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")
PASSWORD = os.getenv("APP_PASSWORD", "MONSECRET")  # Modifie ici ou passe en variable Render

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY", "super-secret-key")  # à changer en prod

transcriptions = {}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Mot de passe incorrect")
    # Si déjà authentifié, accès direct
    if session.get("authenticated"):
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/app", methods=["GET"])
def index():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if not session.get("authenticated"):
        return jsonify({"error": "Non authentifié"}), 403

    audio = request.files.get("audio")
    if not audio:
        return jsonify({"error": "Aucun fichier envoyé."}), 400

    suffix = os.path.splitext(audio.filename)[-1]
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, next(tempfile._get_candidate_names()) + suffix)

    try:
        audio.save(temp_path)
        if not os.path.exists(temp_path):
            return jsonify({"error": "Le fichier n'a pas été correctement enregistré sur le serveur."}), 500

        with open(temp_path, "rb") as f:
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
            )
        text = response.strip()
        key = os.path.basename(temp_path)
        transcriptions[key] = text
        return jsonify({"text": text, "key": key})
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Erreur de transcription: {e}"}), 500
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as ex:
                print("Erreur suppression temporaire :", ex)

@app.route("/download/<key>")
def download_txt(key):
    if not session.get("authenticated"):
        return "Non authentifié", 403
    text = transcriptions.get(key)
    if not text:
        return "Transcription introuvable", 404
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt") as f:
        f.write(text)
        temp_name = f.name
    return send_file(temp_name, as_attachment=True, download_name="transcription.txt")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
