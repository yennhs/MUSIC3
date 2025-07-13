from flask import Flask, render_template, request, redirect, url_for, session
from pathlib import Path
import subprocess
import yt_dlp
from pydub import AudioSegment
import os

app = Flask(__name__)
app.secret_key = "2025"  # session 使用

# 確保 static 資料夾存在
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("youtube_url")
        if url:
            return redirect(url_for("separate", youtube_url=url))
    return """
        <h2>Demucs 音源分離器</h2>
        <form method="POST">
            <input name="youtube_url" placeholder="YouTube URL">
            <button type="submit">下載並分離</button>
        </form>
    """

@app.route("/separate")
def separate():
    youtube_url = request.args.get("youtube_url")
    if not youtube_url:
        return "請輸入 YouTube 連結"

    downloads = Path("downloads")
    downloads.mkdir(exist_ok=True)

    # --- 下載音檔 ---
    ydl_opts = {
        "format": "bestaudio/best",
        "restrictfilenames": True,
        "outtmpl": str(downloads / "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192",
        }],
        "quiet": True,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)

    wav_path = Path(info["requested_downloads"][0]["filepath"]).with_suffix(".wav")
    title = wav_path.stem

    # --- 分離 ---
    sep_dir = Path("separated/htdemucs") / title
    if not sep_dir.exists():
        cmd = ["python3", "-m", "demucs","-n", "demucs_quantized", str(wav_path)]
        subprocess.run(cmd, check=True)

    # --- 轉 mp3 存到 static/title/ ---
    mp3_output_dir = static_dir / title
    mp3_output_dir.mkdir(parents=True, exist_ok=True)

    for part in ["vocals", "drums", "bass", "other"]:
        wav_file = sep_dir / f"{part}.wav"
        mp3_file = mp3_output_dir / f"{part}.mp3"
        if wav_file.exists():
            audio = AudioSegment.from_wav(wav_file)
            audio.export(mp3_file, format="mp3")

    return redirect(url_for("mixer", title=title))

@app.route("/mixer/<title>")
def mixer(title):
    return render_template("mixer_template.html", title=title, folder=title)

@app.route("/reset")
def reset():
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
