import os
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
import openai

# Charge la clé API OpenAI depuis la variable d'environnement
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
transcriptions = {}

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    audio = request.files.get("audio")
    if not audio:
        return jsonify({"error": "Aucun fichier envoyé."}), 400

    suffix = os.path.splitext(audio.filename)[-1]
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, next(tempfile._get_candidate_names()) + suffix)

    try:
        # Sauvegarder le fichier uploadé
        audio.save(temp_path)
        if not os.path.exists(temp_path):
            return jsonify({"error": "Le fichier n'a pas été correctement enregistré sur le serveur."}), 500

        # Transcription via API OpenAI
        with open(temp_path, "rb") as f:
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
                # language="fr",  # Optionnel : détecte automatique si non précisé
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
        # Supprime le fichier temporaire s'il existe encore
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as ex:
                print("Erreur suppression temporaire :", ex)

@app.route("/download/<key>")
def download_txt(key):
    text = transcriptions.get(key)
    if not text:
        return "Transcription introuvable", 404
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt") as f:
        f.write(text)
        temp_name = f.name
    return send_file(temp_name, as_attachment=True, download_name="transcription.txt")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
