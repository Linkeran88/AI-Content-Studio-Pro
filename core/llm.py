from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class OllamaClient:
    def __init__(self, config: dict[str, Any]) -> None:
        ollama_config = config.get("ollama", {})
        self.base_url = str(ollama_config.get("base_url", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = int(ollama_config.get("timeout_seconds", 300))
        self.temperature = float(ollama_config.get("temperature", 0.7))
        self.num_ctx = int(ollama_config.get("num_ctx", 8192))

    def generate(self, model: str, prompt: str) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
            },
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "无法连接 Ollama。请确认 Ollama 已启动，并已拉取所选模型，例如：ollama pull qwen2.5:7b。"
            ) from exc

        generated = str(data.get("response", "")).strip()
        if not generated:
            raise RuntimeError("Ollama 没有返回有效内容。请检查模型是否可用。")
        return generated
