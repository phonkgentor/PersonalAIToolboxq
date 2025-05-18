import os
import uuid
import shutil
from flask import Flask, render_template_string, request, send_from_directory, redirect, url_for, flash
import yt_dlp
import librosa
import moviepy.editor as mp

UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mkv', 'avi', 'mov'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")  # Set a real secret in prod!

# HTML template is inlined for simplicity, but you can move it to templates/index.html
INDEX_HTML = '''
<!doctype html>
<title>Anime AMV Editor</title>
<h1>Anime AMV Generator</h1>
<form method=post enctype=multipart/form-data>
  <label>Anime Video File:</label>
  <input type=file name=anime_file required>
  <br><br>
  <label>YouTube Phonk Track URL:</label>
  <input type=text name=music_url required placeholder="https://www.youtube.com/watch?v=...">
  <br><br>
  <label>Overlay Text (optional):</label>
  <input type=text name=overlay_text value="Epic AMV Edit">
  <br><br>
  <button type=submit>Generate AMV</button>
</form>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul>
    {% for message in messages %}
      <li>{{ message }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}
{% if download_url %}
  <h2>Your AMV is ready!</h2>
  <a href="{{ download_url }}">Download AMV</a>
{% endif %}
'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def download_youtube_audio(youtube_url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

def analyze_audio_tempo(audio_path):
    y, sr = librosa.load(audio_path)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return tempo

def dummy_scene_detect(video_path):
    # Dummy: return one segment, first 10 seconds or video duration if shorter
    clip = mp.VideoFileClip(video_path)
    end = min(10, clip.duration)
    clip.close()
    return [(0, end)]

def add_overlay_effect(input_video_path, output_video_path, text, scenes=None):
    clip = mp.VideoFileClip(input_video_path)
    # For simplicity, apply text overlay for the whole video
    txt_clip = mp.TextClip(text, fontsize=60, color='white', font='Arial-Bold', stroke_color='black', stroke_width=2)
    txt_clip = txt_clip.set_pos(('center', 'bottom')).set_duration(clip.duration)
    result = mp.CompositeVideoClip([clip, txt_clip])
    result.write_videofile(output_video_path, codec="libx264", audio_codec="aac")
    clip.close()
    txt_clip.close()
    result.close()

def combine_video_and_music(video_path, music_path, output_path):
    video_clip = mp.VideoFileClip(video_path)
    audio_clip = mp.AudioFileClip(music_path)
    min_duration = min(video_clip.duration, audio_clip.duration)
    audio_clip = audio_clip.subclip(0, min_duration)
    video_clip = video_clip.subclip(0, min_duration)
    video_clip = video_clip.set_audio(audio_clip)
    video_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    video_clip.close()
    audio_clip.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    download_url = None
    if request.method == 'POST':
        anime_file = request.files.get('anime_file')
        music_url = request.form.get('music_url')
        overlay_text = request.form.get('overlay_text', 'Epic AMV Edit')
        if not anime_file or not allowed_file(anime_file.filename):
            flash('Invalid or missing video file.')
            return render_template_string(INDEX_HTML, download_url=None)

        video_id = str(uuid.uuid4())
        video_filename = f"{video_id}_{anime_file.filename}"
        video_path = os.path.join(UPLOAD_FOLDER, video_filename)
        anime_file.save(video_path)

        # Download music
        music_filename = f"{video_id}_music.mp3"
        music_path = os.path.join(UPLOAD_FOLDER, music_filename)
        try:
            download_youtube_audio(music_url, music_path)
        except Exception as e:
            flash(f"Music download failed: {e}")
            if os.path.exists(video_path): os.remove(video_path)
            return render_template_string(INDEX_HTML, download_url=None)

        # Analyze music tempo (not used in dummy, but ready for advanced sync)
        try:
            tempo = analyze_audio_tempo(music_path)
        except Exception as e:
            flash(f"Audio analysis failed: {e}")
            if os.path.exists(video_path): os.remove(video_path)
            if os.path.exists(music_path): os.remove(music_path)
            return render_template_string(INDEX_HTML, download_url=None)

        # Dummy scene detection (can be replaced with OpenCV/AI)
        scenes = dummy_scene_detect(video_path)

        # Generate video with overlay
        overlayed_path = os.path.join(UPLOAD_FOLDER, f"{video_id}_overlay.mp4")
        try:
            add_overlay_effect(video_path, overlayed_path, overlay_text, scenes=scenes)
        except Exception as e:
            flash(f"Video overlay failed: {e}")
            if os.path.exists(video_path): os.remove(video_path)
            if os.path.exists(music_path): os.remove(music_path)
            return render_template_string(INDEX_HTML, download_url=None)

        # Combine with music
        final_filename = f"{video_id}_AMV.mp4"
        final_path = os.path.join(RESULTS_FOLDER, final_filename)
        try:
            combine_video_and_music(overlayed_path, music_path, final_path)
        except Exception as e:
            flash(f"Final video assembly failed: {e}")
            if os.path.exists(video_path): os.remove(video_path)
            if os.path.exists(music_path): os.remove(music_path)
            if os.path.exists(overlayed_path): os.remove(overlayed_path)
            return render_template_string(INDEX_HTML, download_url=None)

        # Clean up temp files
        for p in [video_path, music_path, overlayed_path]:
            if os.path.exists(p):
                os.remove(p)

        download_url = url_for('download', filename=final_filename)

    return render_template_string(INDEX_HTML, download_url=download_url)

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(RESULTS_FOLDER, filename, as_attachment=True)

# For Render/Railway: Gunicorn looks for 'app' object
if __name__ == '__main__':
    # Use host="0.0.0.0" for cloud platforms; default port is 5000 or as set by environment
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))