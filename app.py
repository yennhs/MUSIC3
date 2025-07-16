from flask import Flask, render_template, request, redirect, url_for, jsonify
from pathlib import Path
import subprocess
import yt_dlp
from pydub import AudioSegment
import os
import sys
import threading
import uuid
import traceback

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "2025")

downloads = Path("downloads")
static_dir = Path("static")
jobs = {}

downloads.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)


def separate_background(task_id, youtube_url):
    try:
        jobs[task_id] = "下載中..."
        print(f"[任務 {task_id}] 狀態：下載中...")

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

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)

        wav_path = Path(info["requested_downloads"][0]["filepath"]).with_suffix(".wav")
        title = wav_path.stem
        jobs[task_id] = f"音源分離中：{title}"
        print(f"[任務 {task_id}] 狀態：音源分離中：{title}")

        sep_dir = Path("separated/htdemucs") / title
        if not sep_dir.exists():
            subprocess.run([
                sys.executable, "-m", "demucs", "-n", "htdemucs", str(wav_path)
            ], check=True)

        mp3_output_dir = static_dir / title
        mp3_output_dir.mkdir(parents=True, exist_ok=True)

        for part in ["vocals", "drums", "bass", "other"]:
            wav_file = sep_dir / f"{part}.wav"
            mp3_file = mp3_output_dir / f"{part}.mp3"
            if wav_file.exists():
                audio = AudioSegment.from_wav(wav_file)
                audio.export(mp3_file, format="mp3")

        wav_path.unlink(missing_ok=True)
        Path("cookies.txt").unlink(missing_ok=True)

        jobs[task_id] = f"完成:{title}"
        print(f"[任務 {task_id}] 狀態：完成:{title}")
    except Exception as e:
        print("[錯誤]", traceback.format_exc())
        jobs[task_id] = f"錯誤: {str(e)}"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("youtube_url")
        cookies_file = request.files.get("cookies")

        if not url or not cookies_file:
            return "❗請提供 YouTube 連結與 cookies.txt", 400

        cookies_path = Path("cookies.txt")
        cookies_file.save(cookies_path)

        task_id = str(uuid.uuid4())
        thread = threading.Thread(target=separate_background, args=(task_id, url))
        thread.start()
        return redirect(url_for("status", task_id=task_id))

    return render_template("index.html")


@app.route("/status")
def status():
    task_id = request.args.get("task_id")
    return render_template("status.html", task_id=task_id)


@app.route("/status_api")
def status_api():
    task_id = request.args.get("task_id")
    status = jobs.get(task_id, "任務不存在")
    print(f"[查詢] 任務 {task_id} 狀態：{status}")

    if status.startswith("完成:"):
        return jsonify({"status": "done", "title": status.replace("完成:", "")})
    elif status.startswith("錯誤:"):
        return jsonify({"status": "error", "message": status})
    else:
        return jsonify({"status": "processing", "message": status})


@app.route("/mixer/<title>")
def mixer(title):
    history = []
    mp3_folder = static_dir / title
    if mp3_folder.exists():
        history.append({
            "title": title,
            "folder": title
        })
    return render_template("mixer_template.html", title=title, folder=title, history=history)


@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5173)
