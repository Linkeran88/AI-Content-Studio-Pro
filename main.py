from __future__ import annotations

import json
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


APP_NAME = "AI Content Studio Pro"


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path.home() / "Documents" / APP_NAME
    return Path(__file__).resolve().parent


def resource_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parent


def load_config(base_dir: Path, resource_dir: Path) -> dict:
    user_config = base_dir / "config.json"
    bundled_config = resource_dir / "config.json"
    config_path = user_config if user_config.exists() else bundled_config

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)
    else:
        config = {}

    config["_base_dir"] = str(base_dir)
    config["_resource_dir"] = str(resource_dir)
    return config


def load_stylesheet(resource_dir: Path) -> str:
    qss_path = resource_dir / "assets" / "styles.qss"
    if not qss_path.exists():
        return ""
    return qss_path.read_text(encoding="utf-8")


def main() -> int:
    base_dir = app_base_dir()
    resource_dir = resource_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("AI Content Studio")
    app.setStyleSheet(load_stylesheet(resource_dir))

    window = MainWindow(load_config(base_dir, resource_dir))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
