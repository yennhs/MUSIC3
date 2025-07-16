from flask import Flask, render_template, request, redirect, url_for
from pathlib import Path
import subprocess
import yt_dlp
from pydub import AudioSegment
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "2025")

# 建立基本資料夾
downloads = Path("downloads")
static_dir = Path("static")
downloads.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("youtube_url")
        cookies_file = request.files.get("cookies")

        if not url or not cookies_file:
            return "❗請提供 YouTube 連結與 cookies.txt", 400

        # 儲存上傳的 cookies.txt
        cookies_path = Path("cookies.txt")
        cookies_file.save(cookies_path)

        return redirect(url_for("separate", youtube_url=url))

    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head><meta charset="UTF-8"><title>Demucs 音源分離器</title></head>
    <body>
        <h2>Demucs 音源分離器</h2>
        <form method="POST" enctype="multipart/form-data">
            <label>輸入 YouTube 連結：</label><br>
            <input type="text" name="youtube_url" required><br><br>
            <label>上傳 cookies.txt：</label><br>
            <input type="file" name="cookies" accept=".txt" required><br><br>
            <button type="submit">下載並分離</button>
        </form>
    </body>
    </html>
    """

@app.route("/separate")
def separate():
    youtube_url = request.args.get("youtube_url")
    if not youtube_url:
        return "請輸入 YouTube 連結", 400

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
        "noplaylist": True,
        "cookiefile": "cookies.txt",
        "http_headers": {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
        "sleep_interval": 3,
        "max_sleep": 8,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
    except Exception as e:
        return f"❌ 音訊下載失敗：{e}", 500

    wav_path = Path(info["requested_downloads"][0]["filepath"]).with_suffix(".wav")
    title = wav_path.stem

    sep_dir = Path("separated/htdemucs") / title
    try:
        if not sep_dir.exists():
            subprocess.run([
                "python3", "-m", "demucs", "-n", "demucs_quantized", str(wav_path)
            ], check=True)
    except subprocess.CalledProcessError as e:
        return f"❌ 音源分離失敗：{e}", 500

    # 將音軌轉 mp3
    mp3_output_dir = static_dir / title
    mp3_output_dir.mkdir(parents=True, exist_ok=True)

    for part in ["vocals", "drums", "bass", "other"]:
        wav_file = sep_dir / f"{part}.wav"
        mp3_file = mp3_output_dir / f"{part}.mp3"
        if wav_file.exists():
            try:
                audio = AudioSegment.from_wav(wav_file)
                audio.export(mp3_file, format="mp3")
            except Exception as e:
                return f"❌ MP3 轉換錯誤（{part}）：{e}", 500

    # 清理暫存檔
    try:
        wav_path.unlink(missing_ok=True)
        Path("cookies.txt").unlink(missing_ok=True)
    except Exception:
        pass

    return redirect(url_for("mixer", title=title))

@app.route("/mixer/<title>")
def mixer(title):
    history = []

    # 歷史曲目紀錄（可擴充）
    mp3_folder = static_dir / title
    if mp3_folder.exists():
        history.append({
            "title": title,
            "folder": title
        })

    return render_template("mixer_template.html", title=title, folder=title, history=history)

@app.route("/reset")
def reset():
    return redirect(url_for("index"))

@app.route("/favicon.ico")
def favicon():
    return "", 204  # 避免 favicon 404

if __name__ == "__main__":
    app.run(debug=True)
