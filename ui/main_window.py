from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.orchestrator import AnalysisOptions, TaskOrchestrator
from core.obsidian import is_obsidian_vault, push_to_obsidian
from core.model_discovery import (
    discover_whisper_models,
    is_whisper_model_dir,
    list_ollama_models,
    list_ollama_models_from_folder,
    resolve_whisper_model_folder,
)


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}

WHISPER_HINTS = {
    "tiny": "首次使用需联网下载，体积最小，适合快速测试。",
    "base": "首次使用需联网下载，速度较快，适合短视频粗转写。",
    "small": "首次使用需联网下载，速度和准确率均衡，普通电脑更稳。",
    "medium": "首次下载约 1.5GB；准确率更稳，但网络不稳定时容易中断。",
    "large-v3": "首次下载体积最大；准确率最高，占用显存和时间更多。",
}

LLM_HINTS = {
    "qwen2.5:7b": "推荐。中文写作稳定，速度和质量比较均衡。",
    "qwen2.5:14b": "质量更强，对电脑性能要求更高。",
    "llama3:8b": "通用写作模型，适合英文或混合内容。",
    "llama3.1:8b": "通用能力更稳。",
}


class NoticeDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, message: str, kind: str = "info") -> None:
        super().__init__(parent)
        self.setObjectName("noticeDialog")
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(680, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        marker = QLabel("!" if kind == "error" else "i")
        marker.setObjectName("dialogMarker")
        marker.setProperty("kind", kind)
        marker.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("dialogTitle")

        header.addWidget(marker)
        header.addWidget(title_label, 1)
        layout.addLayout(header)

        text = QPlainTextEdit()
        text.setObjectName("dialogText")
        text.setReadOnly(True)
        text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        text.setPlainText(message)
        layout.addWidget(text, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        copy_button = QPushButton("复制信息")
        copy_button.setObjectName("ghostButton")
        copy_button.clicked.connect(lambda: QApplication.clipboard().setText(message))

        ok_button = QPushButton("知道了")
        ok_button.setObjectName("primaryButton")
        ok_button.clicked.connect(self.accept)

        buttons.addWidget(copy_button)
        buttons.addWidget(ok_button)
        layout.addLayout(buttons)


def show_notice(parent: QWidget | None, title: str, message: str, kind: str = "info") -> None:
    NoticeDialog(parent, title, message, kind).exec()


class DropZone(QFrame):
    file_selected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(12)

        self.title = QLabel("拖拽视频到这里")
        self.title.setObjectName("dropTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.subtitle = QLabel("支持 MP4 / MOV / MKV / AVI / WEBM")
        self.subtitle.setObjectName("dropSubtitle")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.button = QPushButton("选择文件")
        self.button.setObjectName("ghostButton")
        self.button.clicked.connect(self.choose_file)

        layout.addStretch(1)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

    def choose_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频",
            "",
            "Video Files (*.mp4 *.mov *.mkv *.avi *.m4v *.webm);;All Files (*)",
        )
        if file_name:
            self._emit_if_video(file_name)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            first_url = event.mimeData().urls()[0]
            if first_url.isLocalFile() and Path(first_url.toLocalFile()).suffix.lower() in VIDEO_EXTENSIONS:
                self.setProperty("dragging", True)
                self.style().unpolish(self)
                self.style().polish(self)
                event.acceptProposedAction()
                return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self._emit_if_video(url.toLocalFile())
                event.acceptProposedAction()
                return
        event.ignore()

    def _emit_if_video(self, file_name: str) -> None:
        path = Path(file_name)
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            show_notice(self, "文件格式不支持", "请选择 MP4、MOV、MKV、AVI、M4V 或 WEBM 视频文件。", "error")
            return
        self.file_selected.emit(str(path))

    def set_file(self, file_name: str) -> None:
        path = Path(file_name)
        self.title.setText(path.name)
        self.subtitle.setText(str(path.parent))


class ProgressRow(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("progressTitle")

        self.message_label = QLabel("等待中")
        self.message_label.setObjectName("progressMessage")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)

        layout.addWidget(self.title_label, 0, 0)
        layout.addWidget(self.message_label, 0, 1)
        layout.addWidget(self.bar, 1, 0, 1, 2)

    def update_value(self, value: int, message: str) -> None:
        self.bar.setValue(max(0, min(100, value)))
        self.message_label.setText(message)

    def reset(self) -> None:
        self.update_value(0, "等待中")


class AnalysisWorker(QThread):
    progress_changed = pyqtSignal(str, int, int, str)
    output_created = pyqtSignal(str)
    finished_successfully = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, video_path: str, options: AnalysisOptions, config: dict[str, Any]) -> None:
        super().__init__()
        self.video_path = video_path
        self.options = options
        self.config = config

    def run(self) -> None:
        try:
            orchestrator = TaskOrchestrator(self.config)

            def report(stage: str, stage_percent: int, overall_percent: int, message: str) -> None:
                self.progress_changed.emit(stage, stage_percent, overall_percent, message)

            def on_file_created(path: Path) -> None:
                self.output_created.emit(str(path))

            result = orchestrator.run(
                video_path=Path(self.video_path),
                options=self.options,
                progress_callback=report,
                file_callback=on_file_created,
            )
            self.finished_successfully.emit(result)
        except Exception as exc:  # noqa: BLE001 - display a friendly UI error.
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__()
        self.config = config
        self.video_path: str | None = None
        self.worker: AnalysisWorker | None = None
        self.output_folder: Path | None = None
        self.generated_files: list[Path] = []

        self.setWindowTitle("AI Content Studio Pro")
        self.setMinimumSize(1180, 820)
        self.resize(1320, 860)

        self._build_ui()
        self._reset_progress()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        header = self._build_header()
        main_layout.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(18)
        main_layout.addLayout(body, 1)

        left_scroll = QScrollArea()
        left_scroll.setObjectName("leftScroll")
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)

        left_content = QWidget()
        left_content.setObjectName("leftContent")
        left = QVBoxLayout(left_content)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(14)

        left_scroll.setWidget(left_content)
        body.addWidget(left_scroll, 5)

        right = QVBoxLayout()
        right.setSpacing(14)
        body.addLayout(right, 4)

        left.addWidget(self._build_input_panel())
        left.addWidget(self._build_progress_panel())

        right.addWidget(self._build_output_panel(), 1)

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(4)

        title = QLabel("AI Content Studio Pro")
        title.setObjectName("appTitle")

        subtitle = QLabel("短视频内容理解 · 爆款写作 · 本地 AI 工作流")
        subtitle.setObjectName("appSubtitle")

        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        badge = QLabel("Local AI")
        badge.setObjectName("statusBadge")

        layout.addLayout(title_wrap)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addWidget(badge)
        return header

    def _build_input_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        section_title = QLabel("视频输入")
        section_title.setObjectName("sectionTitle")
        layout.addWidget(section_title)

        self.drop_zone = DropZone()
        self.drop_zone.file_selected.connect(self.on_video_selected)
        self.drop_zone.setFixedHeight(142)
        layout.addWidget(self.drop_zone)

        model_title = QLabel("模型选择")
        model_title.setObjectName("sectionTitle")
        layout.addWidget(model_title)

        self.whisper_combo = QComboBox()
        self.whisper_combo.setEditable(False)
        self.whisper_combo.currentTextChanged.connect(self.update_model_hints)

        self.llm_combo = QComboBox()
        self.llm_combo.setEditable(False)
        self.llm_combo.currentTextChanged.connect(self.update_model_hints)

        model_grid = QGridLayout()
        model_grid.setHorizontalSpacing(12)
        model_grid.setVerticalSpacing(12)
        model_grid.addWidget(
            self._build_model_card(
                "语音转写",
                "Whisper / faster-whisper",
                self.whisper_combo,
                [
                    ("选择文件夹", self.choose_whisper_folder),
                    ("刷新本地", self.refresh_whisper_models),
                ],
            ),
            0,
            0,
        )
        model_grid.addWidget(
            self._build_model_card(
                "内容生成",
                "Ollama 本地模型",
                self.llm_combo,
                [
                    ("选择目录", self.choose_ollama_folder),
                    ("刷新模型", self.refresh_ollama_models),
                ],
            ),
            0,
            1,
        )
        model_grid.setColumnStretch(0, 1)
        model_grid.setColumnStretch(1, 1)
        layout.addLayout(model_grid)
        self.refresh_whisper_models(select_value=self.config.get("default_whisper_model", "medium"), quiet=True)
        self.refresh_ollama_models(select_value=self.config.get("default_llm_model", "qwen2.5:14b"), quiet=True)

        output_title = QLabel("输出模式")
        output_title.setObjectName("sectionTitle")
        layout.addWidget(output_title)

        self.output_checks: dict[str, QCheckBox] = {
            "article": QCheckBox("Markdown知识文章"),
            "xiaohongshu": QCheckBox("小红书爆款文案"),
            "wechat": QCheckBox("公众号格式"),
            "summary": QCheckBox("学习总结"),
            "titles": QCheckBox("爆款标题库"),
            "slides": QCheckBox("HTML演示PPT"),
        }
        output_grid = QGridLayout()
        output_grid.setHorizontalSpacing(12)
        output_grid.setVerticalSpacing(10)
        for index, checkbox in enumerate(self.output_checks.values()):
            checkbox.setChecked(True)
            output_grid.addWidget(checkbox, index // 2, index % 2)
        layout.addLayout(output_grid)

        self.start_button = QPushButton("开始分析")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_analysis)
        layout.addWidget(self.start_button)

        return panel

    def _build_model_card(
        self,
        title: str,
        subtitle: str,
        combo: QComboBox,
        actions: list[tuple[str, Any]],
    ) -> QWidget:
        card = QFrame()
        card.setObjectName("modelCard")
        card.setMinimumHeight(150)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName("modelLabel")

        sub_label = QLabel(subtitle)
        sub_label.setObjectName("modelSubtitle")

        hint = QLabel()
        hint.setObjectName("modelHint")
        hint.setWordWrap(True)
        hint.setMinimumHeight(38)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        picker_row.addWidget(combo, 1)
        for label_text, callback in actions:
            button = QPushButton(label_text)
            button.setObjectName("smallButton")
            button.clicked.connect(lambda checked=False, cb=callback: cb())
            picker_row.addWidget(button)

        card_layout.addWidget(label)
        card_layout.addWidget(sub_label)
        card_layout.addLayout(picker_row)
        card_layout.addWidget(hint)

        if combo is self.whisper_combo:
            self.whisper_hint = hint
        else:
            self.llm_hint = hint
        return card

    def _build_progress_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        title = QLabel("处理进度")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setValue(0)
        layout.addWidget(self.overall_bar)

        self.stage_rows: dict[str, ProgressRow] = {
            "audio": ProgressRow("音频提取"),
            "whisper": ProgressRow("Whisper转写"),
            "llm": ProgressRow("AI分析"),
            "export": ProgressRow("文件导出"),
        }
        for row in self.stage_rows.values():
            layout.addWidget(row)

        log_title = QLabel("运行日志")
        log_title.setObjectName("smallSectionTitle")
        layout.addWidget(log_title)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(110)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.log_view)

        return panel

    def _build_output_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("输出文件")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.open_folder_button = QPushButton("打开目录")
        self.open_folder_button.setObjectName("ghostButton")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        header.addWidget(self.open_folder_button)

        self.bind_obsidian_button = QPushButton("绑定Obsidian")
        self.bind_obsidian_button.setObjectName("ghostButton")
        self.bind_obsidian_button.clicked.connect(self.bind_obsidian_vault)
        header.addWidget(self.bind_obsidian_button)

        self.push_obsidian_button = QPushButton("推送Obsidian")
        self.push_obsidian_button.setObjectName("ghostButton")
        self.push_obsidian_button.clicked.connect(self.push_selected_to_obsidian)
        header.addWidget(self.push_obsidian_button)

        self.copy_button = QPushButton("复制预览")
        self.copy_button.setObjectName("ghostButton")
        self.copy_button.clicked.connect(self.copy_preview)
        header.addWidget(self.copy_button)

        layout.addLayout(header)

        self.output_list = QListWidget()
        self.output_list.itemSelectionChanged.connect(self.preview_selected_file)
        self.output_list.itemDoubleClicked.connect(self.open_selected_file)
        layout.addWidget(self.output_list, 2)

        self.preview_stack = QStackedWidget()
        self.empty_preview = QLabel("分析完成后会显示生成内容")
        self.empty_preview.setObjectName("emptyPreview")
        self.empty_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("生成内容预览")

        self.preview_stack.addWidget(self.empty_preview)
        self.preview_stack.addWidget(self.preview)
        layout.addWidget(self.preview_stack, 3)

        return panel

    def _select_combo_data(self, combo: QComboBox, data: str) -> None:
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _combo_value(self, combo: QComboBox) -> str:
        data = combo.currentData()
        if data is not None:
            return str(data).strip()
        return combo.currentText().strip()

    def _select_or_first(self, combo: QComboBox, value: str | None) -> None:
        if value:
            index = combo.findData(value)
            if index >= 0:
                combo.setCurrentIndex(index)
                return
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def refresh_whisper_models(self, select_value: str | None = None, quiet: bool = False) -> None:
        previous_value = select_value or self._combo_value(self.whisper_combo)
        options = discover_whisper_models(self.config)
        local_options = [option for option in options if option.source == "local"]
        if quiet and local_options:
            previous_value = local_options[0].value
        elif quiet and previous_value == "medium":
            previous_value = "small"

        self.whisper_combo.blockSignals(True)
        self.whisper_combo.clear()
        for option in options:
            self.whisper_combo.addItem(option.label, option.value)
        self._select_or_first(self.whisper_combo, previous_value)
        self.whisper_combo.blockSignals(False)
        self.update_model_hints()
        if not quiet:
            local_count = sum(1 for option in options if option.source == "local")
            self.append_log(f"已刷新语音模型：发现 {local_count} 个本地缓存模型。")

    def choose_whisper_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择 faster-whisper 模型文件夹", str(Path.home()))
        if not folder:
            return

        model_folder = resolve_whisper_model_folder(Path(folder))
        if not is_whisper_model_dir(model_folder):
            show_notice(
                self,
                "模型文件夹不完整",
                "请选择包含 model.bin 和 config.json 的 faster-whisper 模型文件夹。\n\n"
                "如果你选择的是 Hugging Face 缓存目录，可以选择对应模型的 snapshots 子目录。",
                "error",
            )
            return

        value = str(model_folder)
        index = self.whisper_combo.findData(value)
        if index < 0:
            self.whisper_combo.addItem(f"本地文件夹：{model_folder.name}", value)
            index = self.whisper_combo.findData(value)
        self.whisper_combo.setCurrentIndex(index)
        self.append_log(f"已选择本地语音模型：{value}")

    def refresh_ollama_models(self, select_value: str | None = None, quiet: bool = False) -> None:
        previous_value = select_value or self._combo_value(self.llm_combo)
        models, message = list_ollama_models(self.config)

        self.llm_combo.blockSignals(True)
        self.llm_combo.clear()
        if models:
            for model in models:
                self.llm_combo.addItem(model, model)
            self._select_or_first(self.llm_combo, previous_value)
        else:
            self.llm_combo.addItem("未读取到本地 Ollama 模型", "")
        self.llm_combo.blockSignals(False)
        self.update_model_hints()
        if not quiet:
            self.append_log(message)
            if not models:
                show_notice(self, "没有读取到本地模型", message, "info")

    def choose_ollama_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择 Ollama 模型目录",
            str(Path.home() / ".ollama" / "models"),
        )
        if not folder:
            return

        models = list_ollama_models_from_folder(Path(folder))
        if not models:
            show_notice(
                self,
                "没有识别到 Ollama 模型",
                "请选择 Ollama 的 models 目录或 manifests 目录。\n\n"
                "常见位置：C:\\Users\\你的用户名\\.ollama\\models\n\n"
                "如果你把 Ollama 模型放在其他磁盘，请选择那个模型根目录或 manifests 目录。\n\n"
                "注意：blobs 目录和单个 GGUF 文件目录不等于 Ollama 模型目录。",
                "error",
            )
            return

        previous_value = self._combo_value(self.llm_combo)
        self.llm_combo.blockSignals(True)
        self.llm_combo.clear()
        for model in models:
            self.llm_combo.addItem(model, model)
        self._select_or_first(self.llm_combo, previous_value)
        self.llm_combo.blockSignals(False)
        self.update_model_hints()
        self.append_log(f"已从目录读取内容生成模型：{len(models)} 个。")

    def update_model_hints(self) -> None:
        if hasattr(self, "whisper_hint"):
            whisper_model = self._combo_value(self.whisper_combo)
            if not whisper_model:
                self.whisper_hint.setText("请选择一个语音模型。")
            elif Path(whisper_model).exists():
                self.whisper_hint.setText(f"本地模型文件夹：{whisper_model}。推荐，运行时不需要重新下载。")
            else:
                self.whisper_hint.setText(WHISPER_HINTS.get(whisper_model, "预设模型会优先使用本地缓存，没有缓存时需要联网下载。"))
        if hasattr(self, "llm_hint"):
            llm_model = self._combo_value(self.llm_combo)
            if not llm_model:
                self.llm_hint.setText("请先在 Ollama 中安装模型，然后点击刷新模型。")
            else:
                self.llm_hint.setText(LLM_HINTS.get(llm_model, "已读取到的本机 Ollama 模型。"))

    def on_video_selected(self, file_name: str) -> None:
        self.video_path = file_name
        self.drop_zone.set_file(file_name)

    def selected_outputs(self) -> list[str]:
        return [key for key, checkbox in self.output_checks.items() if checkbox.isChecked()]

    def start_analysis(self) -> None:
        if not self.video_path:
            show_notice(self, "请选择视频", "先拖拽或选择一个视频文件。", "info")
            return

        outputs = self.selected_outputs()
        if not outputs:
            show_notice(self, "请选择输出模式", "至少选择一种输出内容。", "info")
            return

        self._reset_progress()
        self.output_list.clear()
        self.preview.clear()
        self.preview_stack.setCurrentWidget(self.empty_preview)
        self.generated_files.clear()
        self.output_folder = None
        self.open_folder_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.start_button.setText("分析中")
        self.append_log("开始分析任务。")
        whisper_model = self._combo_value(self.whisper_combo)
        llm_model = self._combo_value(self.llm_combo)
        if not whisper_model:
            show_notice(self, "请选择语音模型", "请先选择一个 Whisper 模型，或点击“选择文件夹”选择本地模型。", "info")
            self.start_button.setEnabled(True)
            self.start_button.setText("开始分析")
            return
        if not llm_model:
            show_notice(self, "请选择内容生成模型", "请先启动 Ollama 并点击“刷新模型”，选择一个本机已安装模型。", "info")
            self.start_button.setEnabled(True)
            self.start_button.setText("开始分析")
            return

        options = AnalysisOptions(
            whisper_model=whisper_model,
            llm_model=llm_model,
            outputs=outputs,
        )
        self.worker = AnalysisWorker(self.video_path, options, self.config)
        self.worker.progress_changed.connect(self.on_progress_changed)
        self.worker.output_created.connect(self.on_output_created)
        self.worker.finished_successfully.connect(self.on_analysis_finished)
        self.worker.failed.connect(self.on_analysis_failed)
        self.worker.start()

    def on_progress_changed(self, stage: str, stage_percent: int, overall_percent: int, message: str) -> None:
        self.overall_bar.setValue(max(0, min(100, overall_percent)))
        row = self.stage_rows.get(stage)
        if row:
            row.update_value(stage_percent, message)
        if stage_percent in {8, 10, 100} or stage == "llm":
            self.append_log(message)

    def on_output_created(self, path_text: str) -> None:
        path = Path(path_text)
        self.generated_files.append(path)

        item = QListWidgetItem(path.name)
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        self.output_list.addItem(item)

        if self.output_list.count() == 1:
            self.output_list.setCurrentItem(item)

    def on_analysis_finished(self, result: dict) -> None:
        self.start_button.setEnabled(True)
        self.start_button.setText("开始分析")
        self.output_folder = Path(result.get("output_dir", "")) if result.get("output_dir") else None
        self.open_folder_button.setEnabled(bool(self.output_folder and self.output_folder.exists()))
        self.overall_bar.setValue(100)
        self.stage_rows["export"].update_value(100, "完成")
        self.append_log("分析完成，文件已生成。")
        show_notice(self, "分析完成", "内容已经生成，可以在右侧预览、复制，或打开输出目录。", "info")

    def on_analysis_failed(self, message: str) -> None:
        self.start_button.setEnabled(True)
        self.start_button.setText("开始分析")
        friendly_message = self._friendly_error(message)
        self.append_log("处理失败：" + friendly_message)
        show_notice(self, "处理失败", friendly_message, "error")

    def preview_selected_file(self) -> None:
        items = self.output_list.selectedItems()
        if not items:
            self.preview_stack.setCurrentWidget(self.empty_preview)
            return

        path = Path(items[0].data(Qt.ItemDataRole.UserRole))
        if not path.exists():
            self.preview.setPlainText("文件不存在。")
        else:
            self.preview.setPlainText(path.read_text(encoding="utf-8", errors="replace"))
        self.preview_stack.setCurrentWidget(self.preview)

    def open_selected_file(self, item: QListWidgetItem) -> None:
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        if path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_output_folder(self) -> None:
        if self.output_folder and self.output_folder.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_folder)))

    def bind_obsidian_vault(self) -> None:
        current = self.config.get("obsidian", {}).get("vault_dir") or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "选择 Obsidian 仓库目录", str(current))
        if not folder:
            return

        vault_dir = Path(folder)
        if not is_obsidian_vault(vault_dir):
            show_notice(
                self,
                "不是 Obsidian 仓库",
                "请选择 Obsidian 仓库根目录，也就是里面包含 .obsidian 文件夹的目录。",
                "error",
            )
            return

        obsidian_config = dict(self.config.get("obsidian", {}))
        obsidian_config["vault_dir"] = str(vault_dir)
        obsidian_config.setdefault("inbox_dir", "AI Content Studio")
        self.config["obsidian"] = obsidian_config
        self._save_user_config()
        show_notice(self, "绑定成功", f"已绑定 Obsidian 仓库：\n{vault_dir}", "info")
        self.append_log(f"已绑定 Obsidian：{vault_dir}")

    def push_selected_to_obsidian(self) -> None:
        items = self.output_list.selectedItems()
        if not items:
            show_notice(self, "请选择文件", "请先在右侧输出文件列表里选中你认可的文章。", "info")
            return

        try:
            source_path = Path(items[0].data(Qt.ItemDataRole.UserRole))
            target_path = push_to_obsidian(source_path, self.config)
        except RuntimeError as exc:
            if "绑定" in str(exc):
                self.bind_obsidian_vault()
                return
            show_notice(self, "推送失败", str(exc), "error")
            return

        self.append_log(f"已推送到 Obsidian：{target_path}")
        show_notice(self, "推送成功", f"已推送到 Obsidian：\n{target_path}", "info")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_path.parent)))

    def copy_preview(self) -> None:
        text = self.preview.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _save_user_config(self) -> None:
        base_dir = Path(str(self.config.get("_base_dir", Path.home() / "Documents" / "AI Content Studio Pro")))
        base_dir.mkdir(parents=True, exist_ok=True)
        clean_config = {key: value for key, value in self.config.items() if not key.startswith("_")}
        (base_dir / "config.json").write_text(
            json.dumps(clean_config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def append_log(self, message: str) -> None:
        if not hasattr(self, "log_view"):
            return
        clean_message = " ".join(message.strip().split())
        if not clean_message:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{timestamp}] {clean_message}")

    def _friendly_error(self, message: str) -> str:
        raw = message.strip()
        upper = raw.upper()
        download_failed = (
            "PEER CLOSED CONNECTION" in upper
            or "WITHOUT SENDING COMPLETE MESSAGE BODY" in upper
            or ("RECEIVED" in upper and "EXPECTED" in upper)
            or "INCOMPLETEREAD" in upper
            or "CONNECTIONRESETERROR" in upper
            or "CONNECTIONABORTEDERROR" in upper
        )
        if download_failed:
            return (
                "语音模型下载中断。\n\n"
                "当前选择的是 Whisper 预设模型，第一次使用需要联网下载模型文件。"
                "这次连接在下载中途断开，所以转写没有继续。\n\n"
                "建议这样处理：\n"
                "1. 在“语音转写”里先选择 small 或 base，再重新开始分析。\n"
                "2. 如果你已经下载了 faster-whisper 本地模型，点击“选择文件夹”选择模型目录。\n"
                "3. 保持网络或代理稳定后重试；模型完整下载后，下次会直接使用本地缓存。\n\n"
                f"原始错误：\n{raw}"
            )
        if "SSL" in upper or "EOF_OCCURRED" in upper or "UNEXPECTED_EOF" in upper:
            return (
                "Whisper 模型下载或联网读取失败。\n\n"
                "通常是网络、代理或证书连接不稳定导致的。可以这样处理：\n"
                "1. 先确认网络可以访问 Hugging Face。\n"
                "2. 换成 small 模型再试一次，下载更轻。\n"
                "3. 如果你已经有本地 faster-whisper 模型，可以点击“选择文件夹”选择本地模型目录。\n"
                "4. 也可以稍后重试，模型下载完成后就不会每次都联网。\n\n"
                f"原始错误：\n{raw}"
            )
        return raw or "未知错误。"

    def _reset_progress(self) -> None:
        self.overall_bar.setValue(0)
        for row in self.stage_rows.values():
            row.reset()
        if hasattr(self, "log_view"):
            self.log_view.clear()
            self.append_log("等待开始。")
