from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from core.ffmpeg import extract_audio
from core.llm import OllamaClient
from core.slides import export_html_slides
from core.whisper import transcribe_audio
from core.writer import ContentWriter


ProgressCallback = Callable[[str, int, int, str], None]
FileCallback = Callable[[Path], None]


@dataclass(frozen=True)
class AnalysisOptions:
    whisper_model: str
    llm_model: str
    outputs: list[str]


class TaskOrchestrator:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.base_dir = Path(config.get("_base_dir", Path.cwd()))
        self.output_root = self._resolve_dir(config.get("output_dir", "output"))
        self.temp_dir = self._resolve_dir(config.get("temp_dir", "temp"))

    def run(
        self,
        video_path: Path,
        options: AnalysisOptions,
        progress_callback: ProgressCallback,
        file_callback: FileCallback,
    ) -> dict[str, Any]:
        video_path = video_path.resolve()
        if not video_path.exists():
            raise RuntimeError("视频文件不存在。")

        self.output_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        progress_callback("audio", 8, 5, "准备音频")
        audio_path = extract_audio(video_path, self.temp_dir)
        progress_callback("audio", 100, 25, "音频提取完成")

        progress_callback("whisper", 10, 30, "载入Whisper")
        transcript = transcribe_audio(audio_path, options.whisper_model, self.config)
        progress_callback("whisper", 100, 55, "转写完成")

        output_dir = self._create_output_dir(video_path)
        transcript_path = output_dir / "transcript.txt"
        transcript_path.write_text(transcript, encoding="utf-8")
        file_callback(transcript_path)

        llm = OllamaClient(self.config)
        writer = ContentWriter(llm, options.llm_model)

        def on_writer_step(label: str, index: int, total: int) -> None:
            stage_percent = int(((index - 1) / total) * 100)
            overall = 55 + int(((index - 1) / total) * 35)
            progress_callback("llm", stage_percent, overall, f"生成{label}")

        contents = writer.generate(transcript, options.outputs, on_step=on_writer_step)
        progress_callback("llm", 100, 92, "AI分析完成")

        created_files = [transcript_path]
        for key, content in contents.items():
            file_path = output_dir / writer.filename_for(key)
            file_path.write_text(content.strip() + "\n", encoding="utf-8")
            created_files.append(file_path)
            file_callback(file_path)
            if key == "slides":
                html_path = output_dir / "slides.html"
                export_html_slides(content, html_path, title=video_path.stem)
                created_files.append(html_path)
                file_callback(html_path)

        metadata_path = output_dir / "metadata.json"
        metadata = {
            "video": str(video_path),
            "audio": str(audio_path),
            "whisper_model": options.whisper_model,
            "llm_model": options.llm_model,
            "outputs": options.outputs,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        created_files.append(metadata_path)
        file_callback(metadata_path)

        progress_callback("export", 100, 100, "完成")

        return {
            "output_dir": str(output_dir),
            "files": [str(path) for path in created_files],
        }

    def _resolve_dir(self, path_text: str) -> Path:
        path = Path(path_text)
        if path.is_absolute():
            return path
        return self.base_dir / path

    def _create_output_dir(self, video_path: Path) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = _safe_name(video_path.stem)
        output_dir = self.output_root / f"{name}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir


def _safe_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\s]+', "_", value).strip("_")
    return cleaned[:60] or "video"
