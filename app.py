from flask import Flask, render_template, request, redirect, url_for
from pathlib import Path
import yt_dlp
import subprocess
from pydub import AudioSegment

app = Flask(__name__)
app.secret_key = "2025"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("youtube_url")
        cookies_file = request.files.get("cookies")

        if not url or not cookies_file:
            return "請提供 YouTube 連結與 cookies.txt"

        # 儲存 cookies
        cookies_path = Path("cookies.txt")
        cookies_file.save(cookies_path)

        return redirect(url_for("separate", youtube_url=url))

    return render_template("index.html")

@app.route("/separate")
def separate():
    youtube_url = request.args.get("youtube_url")
    if not youtube_url:
        return "請提供 YouTube 連結"

    downloads = Path("downloads")
    downloads.mkdir(exist_ok=True)

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
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
    except Exception as e:
        return f"❌ 無法下載影片：{e}"

    wav_path = Path(info["requested_downloads"][0]["filepath"]).with_suffix(".wav")
    title = wav_path.stem

    sep_dir = Path("separated/htdemucs") / title
    if not sep_dir.exists():
        cmd = ["python3", "-m", "demucs", "-n", "demucs_quantized", str(wav_path)]
        subprocess.run(cmd, check=True)

    output_dir = Path("static") / title
    output_dir.mkdir(parents=True, exist_ok=True)

    for part in ["vocals", "drums", "bass", "other"]:
        wav_file = sep_dir / f"{part}.wav"
        mp3_file = output_dir / f"{part}.mp3"
        if wav_file.exists():
            audio = AudioSegment.from_wav(wav_file)
            audio.export(mp3_file, format="mp3")

    return f"✅ 成功分離！請在 static/{title} 中查看音訊。"

if __name__ == "__main__":
    app.run(debug=True)
