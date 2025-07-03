import os
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
import whisper

app = Flask(__name__)

model = whisper.load_model("medium")
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
        # Écris le fichier dans temp_path et ferme-le !
        audio.save(temp_path)
        # Vérifie l'existence réelle
        print("Chemin du fichier envoyé à Whisper :", temp_path)
        print("Fichier existe ?", os.path.exists(temp_path))
        print("Contenu du dossier temporaire :", os.listdir(os.path.dirname(temp_path)))

        # TEST ffmpeg depuis python
        import subprocess
        print("PATH système vu par Python :", os.environ.get("PATH"))
        print("Test appel direct ffmpeg depuis Python...")
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            print("FFmpeg trouvé :", result.stdout.splitlines()[0] if result.stdout else result.stderr)
        except Exception as e:
            print("Erreur appel ffmpeg :", e)

        if not os.path.exists(temp_path):
            return jsonify({"error": "Le fichier n'a pas été correctement enregistré sur le serveur."}), 500

        # Transcription avec Whisper
        print("Transcription du fichier :", temp_path)
        result = model.transcribe(temp_path)
        text = result["text"].strip()
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
    app.run(host="0.0.0.0", port=10000, debug=True)