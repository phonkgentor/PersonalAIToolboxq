import os
import uuid
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash

# Import your modules (implement these in 'modules/')
from modules.scene_detector import detect_scenes
from modules.music_selector import download_phonk_music, analyze_tempo
from modules.effects import add_advanced_effects

UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flash messages

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle file upload and music URL
        if 'anime_file' not in request.files or request.files['anime_file'].filename == '':
            flash('No file selected')
            return redirect(request.url)

        anime_file = request.files['anime_file']
        music_url = request.form.get('music_url')
        style = request.form.get('style', 'default')

        # Save uploaded video
        video_id = str(uuid.uuid4())
        in_filename = f"{video_id}_{anime_file.filename}"
        video_path = os.path.join(UPLOAD_FOLDER, in_filename)
        anime_file.save(video_path)

        # Download phonk music (if URL provided)
        music_path = os.path.join(UPLOAD_FOLDER, f"{video_id}_music.mp3")
        try:
            download_phonk_music(music_url, music_path)
        except Exception as e:
            flash(f"Music download failed: {e}")
            return redirect(request.url)

        # Detect highlights/scenes
        scenes = detect_scenes(video_path)

        # Analyze music tempo (optional: use for beat sync)
        tempo = analyze_tempo(music_path)

        # Apply advanced effects and build final AMV
        out_filename = f"{video_id}_AMV.mp4"
        out_path = os.path.join(RESULTS_FOLDER, out_filename)
        try:
            add_advanced_effects(
                input_video=video_path,
                output_video=out_path,
                overlay_text="Epic AMV Edit",
                scenes=scenes,
                music_path=music_path,
                tempo=tempo,
                style=style
            )
        except Exception as e:
            flash(f"Video processing failed: {e}")
            return redirect(request.url)

        return redirect(url_for('download', filename=out_filename))

    return render_template('index.html')

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(RESULTS_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
