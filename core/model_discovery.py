from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelOption:
    label: str
    value: str
    source: str


WHISPER_PRESETS = ["tiny", "base", "small", "medium", "large-v3"]
WHISPER_PRESET_LABELS = {
    "tiny": "预设：tiny（首次下载约 80MB）",
    "base": "预设：base（首次下载约 150MB）",
    "small": "预设：small（首次下载约 480MB）",
    "medium": "预设：medium（首次下载约 1.5GB）",
    "large-v3": "预设：large-v3（首次下载约 3GB）",
}


def discover_whisper_models(config: dict[str, Any]) -> list[ModelOption]:
    local_options: list[ModelOption] = []

    for folder in _whisper_search_roots(config):
        for model_dir in _find_whisper_model_dirs(folder):
            label = _whisper_label(model_dir)
            value = str(model_dir)
            if not any(option.value == value for option in local_options):
                local_options.append(ModelOption(f"本地：{label}", value, "local"))

    preset_options = [
        ModelOption(WHISPER_PRESET_LABELS.get(model, f"预设：{model}"), model, "preset")
        for model in WHISPER_PRESETS
    ]
    return local_options + preset_options


def resolve_whisper_model_folder(path: Path) -> Path:
    path = path.expanduser().resolve()
    if is_whisper_model_dir(path):
        return path

    snapshots_dir = path / "snapshots"
    if snapshots_dir.exists():
        candidates = sorted(
            [candidate for candidate in snapshots_dir.iterdir() if is_whisper_model_dir(candidate)],
            key=lambda candidate: candidate.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]

    nested_candidates = sorted(
        _find_whisper_model_dirs(path),
        key=lambda candidate: candidate.stat().st_mtime,
        reverse=True,
    )
    return nested_candidates[0] if nested_candidates else path


def is_whisper_model_dir(path: Path) -> bool:
    return path.is_dir() and (path / "model.bin").exists() and (path / "config.json").exists()


def list_ollama_models(config: dict[str, Any]) -> tuple[list[str], str]:
    api_models = _list_ollama_models_from_api(config)
    if api_models:
        return api_models, "已从 Ollama 服务读取本地模型。"

    cli_models = _list_ollama_models_from_cli()
    if cli_models:
        return cli_models, "已从 Ollama 命令读取本地模型。"

    disk_models = _list_ollama_models_from_disk(config)
    if disk_models:
        return disk_models, "已从 Ollama 本地模型目录读取模型。"

    return [], "未读取到 Ollama 模型。请确认 Ollama 已安装，并至少拉取过一个模型。"


def list_ollama_models_from_folder(path: Path) -> list[str]:
    return _content_generation_models(_list_ollama_models_from_root(path.expanduser().resolve()))


def _whisper_search_roots(config: dict[str, Any]) -> list[Path]:
    roots: list[Path] = []

    for key in ["HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"]:
        value = os.environ.get(key)
        if value:
            roots.append(Path(value))

    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        roots.append(Path(hf_home) / "hub")

    roots.append(Path.home() / ".cache" / "huggingface" / "hub")

    whisper_config = config.get("whisper", {})
    for configured_root in whisper_config.get("local_model_dirs", []):
        roots.append(Path(configured_root))

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = str(root.expanduser())
        if resolved not in seen:
            seen.add(resolved)
            unique_roots.append(root.expanduser())
    return unique_roots


def _find_whisper_model_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []

    candidates: list[Path] = []
    for path in root.rglob("model.bin"):
        folder = path.parent
        if is_whisper_model_dir(folder):
            candidates.append(folder)

    return candidates


def _whisper_label(model_dir: Path) -> str:
    parts = model_dir.parts
    for part in reversed(parts):
        if part.startswith("models--"):
            return part.removeprefix("models--").replace("--", "/")
    normalized_name = model_dir.name.lower()
    if normalized_name.startswith("systranfaster-whisper-"):
        return "Systran/" + model_dir.name.removeprefix("Systran")
    return model_dir.name


def _list_ollama_models_from_api(config: dict[str, Any]) -> list[str]:
    base_url = str(config.get("ollama", {}).get("base_url", "http://127.0.0.1:11434")).rstrip("/")
    request = urllib.request.Request(f"{base_url}/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return []

    names = [model.get("name", "") for model in data.get("models", [])]
    return _content_generation_models(name for name in names if name)


def _list_ollama_models_from_cli() -> list[str]:
    ollama = shutil.which("ollama")
    if not ollama:
        return []

    completed = subprocess.run(
        [ollama, "list"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=8,
    )
    if completed.returncode != 0:
        return []

    models: list[str] = []
    for line in completed.stdout.splitlines()[1:]:
        columns = line.split()
        if columns:
            models.append(columns[0])
    return _content_generation_models(models)


def _list_ollama_models_from_disk(config: dict[str, Any]) -> list[str]:
    roots = []
    ollama_models = os.environ.get("OLLAMA_MODELS")
    if ollama_models:
        roots.append(Path(ollama_models))
    roots.append(Path.home() / ".ollama" / "models")

    for configured_root in config.get("ollama", {}).get("local_model_dirs", []):
        roots.append(Path(configured_root))

    # User-configured model roots can be absolute paths to either the models
    # directory itself or its manifests subdirectory.
    # Example: C:\Users\...\ .ollama\models
    # Example: D:\OllamaModels
    extra_roots = os.environ.get("AI_CONTENT_STUDIO_OLLAMA_MODELS")
    if extra_roots:
        roots.extend(Path(path) for path in extra_roots.split(os.pathsep) if path)

    models: set[str] = set()
    for root in roots:
        models.update(_list_ollama_models_from_root(root.expanduser()))
    return _content_generation_models(models)


def _content_generation_models(models: Any) -> list[str]:
    return sorted({model for model in models if model and not _is_embedding_model(model)})


def _is_embedding_model(model: str) -> bool:
    lower = model.lower()
    return "embed" in lower or "embedding" in lower


def _list_ollama_models_from_root(root: Path) -> set[str]:
    models: set[str] = set()
    for manifests in _candidate_ollama_manifest_dirs(root):
        models.update(_list_ollama_models_from_manifests(manifests))
    return models


def _candidate_ollama_manifest_dirs(root: Path) -> list[Path]:
    candidates: list[Path] = []

    current = root
    for _ in range(8):
        if current.name.lower() == "manifests":
            candidates.append(current)
            break
        parent = current.parent
        if parent == current:
            break
        current = parent

    if root.name.lower() == "manifests":
        candidates.append(root)
    if (root / "manifests").exists():
        candidates.append(root / "manifests")
    if (root / "models" / "manifests").exists():
        candidates.append(root / "models" / "manifests")
    if (root.parent / "manifests").exists():
        candidates.append(root.parent / "manifests")
    if (root.parent / "models" / "manifests").exists():
        candidates.append(root.parent / "models" / "manifests")

    for nested in _find_nested_manifest_dirs(root, max_depth=3):
        candidates.append(nested)

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = str(candidate)
        if candidate.exists() and resolved not in seen:
            seen.add(resolved)
            unique_candidates.append(candidate)
    return unique_candidates


def _find_nested_manifest_dirs(root: Path, max_depth: int) -> list[Path]:
    if not root.exists() or not root.is_dir():
        return []

    found: list[Path] = []
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        folder, depth = stack.pop()
        if folder.name.lower() == "manifests":
            found.append(folder)
            continue
        if depth >= max_depth:
            continue
        try:
            children = list(folder.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                stack.append((child, depth + 1))
    return found


def _list_ollama_models_from_manifests(manifests: Path) -> set[str]:
    models: set[str] = set()
    if not manifests.exists():
        return models

    for manifest in manifests.rglob("*"):
        if not manifest.is_file():
            continue
        relative = manifest.relative_to(manifests)
        parts = relative.parts
        if len(parts) < 4:
            continue
        namespace = parts[1]
        model = parts[2]
        tag = parts[3]
        if namespace == "library":
            models.add(f"{model}:{tag}")
        else:
            models.add(f"{namespace}/{model}:{tag}")
    return models
