from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {".md", ".txt", ".html"}


def is_obsidian_vault(path: Path) -> bool:
    return path.is_dir() and (path / ".obsidian").is_dir()


def push_to_obsidian(source_path: Path, config: dict[str, Any]) -> Path:
    if not source_path.exists():
        raise RuntimeError("请选择一个已经生成的文件。")
    if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise RuntimeError("当前只支持推送 Markdown、TXT 或 HTML 文件。")

    obsidian_config = config.get("obsidian", {})
    vault_dir = Path(str(obsidian_config.get("vault_dir", ""))).expanduser()
    if not is_obsidian_vault(vault_dir):
        raise RuntimeError("请先绑定 Obsidian 仓库目录。")

    inbox_name = str(obsidian_config.get("inbox_dir", "AI Content Studio")).strip() or "AI Content Studio"
    target_dir = vault_dir / inbox_name
    target_dir.mkdir(parents=True, exist_ok=True)

    target_name = _target_name(source_path)
    target_path = _unique_path(target_dir / target_name)
    shutil.copy2(source_path, target_path)
    return target_path


def _target_name(source_path: Path) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    parent_name = source_path.parent.name.strip() or "content"
    safe_parent = _safe_name(parent_name)
    safe_stem = _safe_name(source_path.stem)
    return f"{safe_parent}_{safe_stem}_{stamp}{source_path.suffix.lower()}"


def _safe_name(value: str) -> str:
    cleaned = "".join("_" if char in '<>:"/\\|?*' else char for char in value)
    cleaned = "_".join(cleaned.split())
    return cleaned.strip("._ ")[:80] or "content"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
