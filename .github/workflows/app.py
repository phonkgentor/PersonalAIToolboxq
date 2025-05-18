from flask import Flask, render_template, request, send_from_directory
import os
from modules import anime_editor
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/edit', methods=['POST'])
def edit():
    video = request.files['anime_file']
    music_url = request.form['music_url']
    filename = f"{uuid.uuid4()}_{video.filename}"
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    video.save(video_path)
    edited_filename = f"edited_{filename}"
    edited_path = os.path.join(RESULTS_FOLDER, edited_filename)
    anime_editor.edit(video_path, music_url, edited_path)
    return render_template('index.html', download_url=f'/download/{edited_filename}')

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(RESULTS_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)