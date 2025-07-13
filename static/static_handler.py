import streamlit as st
import base64
from pathlib import Path


def serve_audio_file(filename: str):
    path = Path("static") / filename
    if not path.exists():
        st.error(f"找不到檔案：{filename}")
        return None

    # 轉成 base64
    audio_bytes = path.read_bytes()
    b64 = base64.b64encode(audio_bytes).decode()
    mime = "audio/mp3"
    return f"data:{mime};base64,{b64}"
