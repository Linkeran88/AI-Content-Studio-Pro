from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def extract_audio(video_path: Path, temp_dir: Path) -> Path:
    if not video_path.exists():
        raise RuntimeError("视频文件不存在。")

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("未检测到 FFmpeg。请先安装 FFmpeg，并确保 ffmpeg 可以在命令行中运行。")

    temp_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = temp_dir / f"{video_path.stem}_{timestamp}.wav"

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if completed.returncode != 0 or not audio_path.exists():
        details = completed.stderr.strip()[-1200:] or "FFmpeg 未返回详细错误。"
        raise RuntimeError(f"音频提取失败。\n\n{details}")

    return audio_path
