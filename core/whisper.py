from __future__ import annotations

import os
from pathlib import Path
from typing import Any


_CUDA_DLL_HANDLES: list[Any] = []
_CUDA_PATHS_CONFIGURED = False


def _configure_cuda_dll_paths(config: dict[str, Any]) -> None:
    global _CUDA_PATHS_CONFIGURED
    if _CUDA_PATHS_CONFIGURED:
        return
    _CUDA_PATHS_CONFIGURED = True

    cuda_dirs = _candidate_cuda_bin_dirs(config)
    if not cuda_dirs:
        return

    path_parts = [str(path) for path in cuda_dirs]
    existing_path = os.environ.get("PATH", "")
    os.environ["PATH"] = ";".join(path_parts + [existing_path])

    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is None:
        return

    for folder in cuda_dirs:
        try:
            _CUDA_DLL_HANDLES.append(add_dll_directory(str(folder)))
        except OSError:
            continue


def _candidate_cuda_bin_dirs(config: dict[str, Any]) -> list[Path]:
    roots: list[Path] = []
    whisper_config = config.get("whisper", {})

    for configured_root in whisper_config.get("cuda_search_dirs", []):
        roots.append(Path(configured_root))

    for env_key in ["AI_CONTENT_STUDIO_CUDA_ROOT", "WHISPER_CUDA_HOME", "CUDA_PATH", "CUDA_HOME"]:
        value = os.environ.get(env_key)
        if value:
            roots.append(Path(value))

    candidates: list[Path] = []
    for root in roots:
        root = root.expanduser()
        candidates.extend(
            [
                root,
                root / "bin",
                root / "runtime" / "nvidia" / "cublas" / "bin",
                root / "runtime" / "nvidia" / "cudnn" / "bin",
                root / "runtime" / "nvidia" / "cuda_nvrtc" / "bin",
                root / "nvidia" / "cublas" / "bin",
                root / "nvidia" / "cudnn" / "bin",
                root / "nvidia" / "cuda_nvrtc" / "bin",
            ]
        )

    valid_dirs: list[Path] = []
    seen: set[str] = set()
    for folder in candidates:
        try:
            resolved = folder.resolve()
        except OSError:
            continue
        if not resolved.is_dir():
            continue
        has_cuda_dll = any(
            (resolved / dll_name).exists()
            for dll_name in ["cublas64_12.dll", "cublasLt64_12.dll", "cudnn64_9.dll", "nvrtc64_120_0.dll"]
        )
        if not has_cuda_dll:
            continue
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            valid_dirs.append(resolved)
    return valid_dirs


def _resolve_device(requested_device: str) -> str:
    if requested_device != "auto":
        return requested_device

    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        pass
    return "cpu"


def _resolve_compute_type(device: str, requested_compute_type: str) -> str:
    if requested_compute_type != "auto":
        return requested_compute_type
    return "float16" if device == "cuda" else "int8"


def _looks_like_cuda_runtime_error(message: str) -> bool:
    upper = message.upper()
    markers = [
        "CUBLAS",
        "CUDNN",
        "CUDA",
        "CUDA DRIVER",
        "CUDA RUNTIME",
        "CANNOT BE LOADED",
        "DLL IS NOT FOUND",
    ]
    return any(marker in upper for marker in markers)


def _looks_like_model_download_error(message: str) -> bool:
    upper = message.upper()
    markers = [
        "PEER CLOSED CONNECTION",
        "WITHOUT SENDING COMPLETE MESSAGE BODY",
        "INCOMPLETEREAD",
        "CONNECTIONRESETERROR",
        "CONNECTIONABORTEDERROR",
        "EOF_OCCURRED",
        "UNEXPECTED_EOF",
        "HTTPSCONNECTIONPOOL",
        "MAX RETRIES",
    ]
    return any(marker in upper for marker in markers) or ("RECEIVED" in upper and "EXPECTED" in upper)


def _model_download_help(model_name: str, original_message: str) -> str:
    return (
        "语音模型下载中断。\n\n"
        f"当前语音模型：{model_name}\n"
        "如果这是 tiny / base / small / medium / large-v3 这类预设模型，首次使用需要联网下载。"
        "网络中途断开时就会出现这个错误。\n\n"
        "处理建议：\n"
        "1. 先在语音转写里选择 small 或 base 后重试。\n"
        "2. 如果你已经有本地 faster-whisper 模型，点击“选择文件夹”选择包含 model.bin 和 config.json 的目录。\n"
        "3. 保持网络或代理稳定后再次开始，下载完整后下次会直接使用缓存。\n\n"
        f"原始错误：\n{original_message}"
    )


def _run_transcription(
    whisper_model: Any,
    audio_path: Path,
    model_name: str,
    device: str,
    compute_type: str,
    language: str | None,
    beam_size: int,
    vad_filter: bool,
) -> str:
    model = whisper_model(model_name, device=device, compute_type=compute_type)
    segments, _ = model.transcribe(
        str(audio_path),
        beam_size=beam_size,
        language=language,
        vad_filter=vad_filter,
    )

    transcript_parts: list[str] = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            transcript_parts.append(text)

    return "\n".join(transcript_parts).strip()


def transcribe_audio(audio_path: Path, model_name: str, config: dict[str, Any]) -> str:
    if not audio_path.exists():
        raise RuntimeError("音频文件不存在。")

    _configure_cuda_dll_paths(config)

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("未安装 faster-whisper。请先运行 pip install -r requirements.txt。") from exc

    whisper_config = config.get("whisper", {})
    requested_device = whisper_config.get("device", "auto")
    requested_compute_type = whisper_config.get("compute_type", "auto")
    device = _resolve_device(requested_device)
    compute_type = _resolve_compute_type(device, whisper_config.get("compute_type", "auto"))
    language = whisper_config.get("language", "zh") or None
    beam_size = int(whisper_config.get("beam_size", 5))
    vad_filter = bool(whisper_config.get("vad_filter", True))

    try:
        transcript = _run_transcription(
            WhisperModel,
            audio_path,
            model_name,
            device,
            compute_type,
            language,
            beam_size,
            vad_filter,
        )
    except Exception as exc:  # noqa: BLE001 - convert download failures into usable product copy.
        original_message = str(exc)
        if device == "cuda" and requested_device == "auto" and _looks_like_cuda_runtime_error(original_message):
            transcript = _run_transcription(
                WhisperModel,
                audio_path,
                model_name,
                "cpu",
                _resolve_compute_type("cpu", requested_compute_type),
                language,
                beam_size,
                vad_filter,
            )
        elif _looks_like_cuda_runtime_error(original_message):
            raise RuntimeError(
                "GPU 加速组件不完整。\n\n"
                "当前系统缺少 CUDA / cuBLAS / cuDNN 运行库，Whisper 无法使用 GPU 转写。\n"
                "请把语音转写设备改为 CPU，或安装完整的 NVIDIA CUDA 12 运行环境后重试。\n\n"
                f"原始错误：\n{original_message}"
            ) from exc
        elif _looks_like_model_download_error(original_message):
            raise RuntimeError(_model_download_help(model_name, original_message)) from exc
        else:
            raise

    if not transcript:
        raise RuntimeError("Whisper 没有识别到有效文本。请确认视频中有人声，或尝试更大的模型。")

    return transcript
