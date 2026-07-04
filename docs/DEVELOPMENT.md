# 开发与打包说明

本文档面向需要二次开发或重新打包的开发者。

## 架构概览

```text
GUI (PyQt6)
  ↓
TaskOrchestrator
  ↓
FFmpeg 音频提取
  ↓
faster-whisper 转写
  ↓
Ollama 本地模型生成
  ↓
Markdown / TXT / HTML 输出
  ↓
Obsidian 推送
```

## 核心模块

| 文件 | 说明 |
| --- | --- |
| `main.py` | 应用入口，加载配置和 QSS |
| `ui/main_window.py` | PyQt6 主界面、文件选择、模型选择、输出预览 |
| `core/orchestrator.py` | 串联音频提取、转写、生成和导出 |
| `core/ffmpeg.py` | 调用 FFmpeg 提取 WAV 音频 |
| `core/whisper.py` | faster-whisper 转写和 CUDA 路径处理 |
| `core/llm.py` | Ollama API 客户端 |
| `core/writer.py` | 内容输出类型和 Prompt |
| `core/slides.py` | Markdown 演示稿转 HTML |
| `core/obsidian.py` | 推送文件到 Obsidian Vault |
| `core/model_discovery.py` | 发现本地 Whisper 和 Ollama 模型 |
| `assets/styles.qss` | UI 样式 |

## 配置加载逻辑

源码运行时，默认读取项目根目录的 `config.json`。

打包后运行时，会优先读取：

```text
C:\Users\你的用户名\Documents\AI Content Studio Pro\config.json
```

如果用户配置不存在，则读取打包内置的 `config.json`。

## 内容输出扩展

新增一种输出类型主要修改：

1. 在 `core/writer.py` 的 `OUTPUT_DEFINITIONS` 中增加定义
2. 在 `ui/main_window.py` 中增加对应勾选项
3. 如果需要特殊导出逻辑，在 `core/orchestrator.py` 中处理

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## 构建 EXE

```powershell
.\packaging\build_exe.ps1
```

构建完成后生成：

```text
dist/AI Content Studio Pro/AI Content Studio Pro.exe
```

## 构建安装包

1. 安装 Inno Setup
2. 先运行 `packaging/build_exe.ps1`
3. 用 Inno Setup 编译 `packaging/installer.iss`

输出：

```text
dist/AI_Content_Studio_Pro_Setup.exe
```

## 发布建议

GitHub 源码仓库建议只上传源码和文档，不上传：

- `dist/`
- `build/`
- `.venv/`
- `output/`
- `temp/`
- `__pycache__/`
- 本地模型文件
- 测试视频
- 生成内容

安装包可以放到 GitHub Releases，而不是放进源码仓库。
