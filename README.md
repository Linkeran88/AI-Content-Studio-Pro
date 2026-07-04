# AI Content Studio Pro

AI Content Studio Pro 是一款 Windows 桌面端的本地 AI 内容工作流工具。它可以把短视频或课程视频转成文字，再基于本地大模型自动生成知识文章、小红书文案、公众号稿、学习总结、标题库和 HTML 演示页。

项目重点是本地化、隐私友好、可打包交付：视频、转写文本和生成内容默认保存在本机；语音识别使用 faster-whisper；内容生成使用 Ollama 本地模型。

## 功能亮点

- 拖拽或选择视频文件
- 使用 FFmpeg 自动提取音频
- 使用 faster-whisper 本地语音转写
- 支持 CUDA GPU 加速，也可自动回退 CPU
- 自动读取本地 faster-whisper 模型目录
- 自动读取 Ollama 已安装模型，并过滤 embedding 模型
- 一次生成多种内容：
  - Markdown 知识文章
  - 小红书爆款文案
  - 公众号格式
  - 学习总结
  - 爆款标题库
  - HTML 演示 PPT
- 输出文件可预览、复制、打开目录
- 支持将认可的 Markdown / TXT / HTML 文件推送到 Obsidian 仓库
- 提供 PyInstaller EXE 和 Inno Setup 安装包配置

## 界面预览

当前版本采用 PyQt6 深色桌面界面，核心操作流程是：

```text
导入视频 -> 选择语音模型 -> 选择内容模型 -> 勾选输出模式 -> 开始分析 -> 查看和导出内容
```

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 桌面界面 | PyQt6 |
| 视频 / 音频处理 | FFmpeg |
| 语音转写 | faster-whisper / CTranslate2 |
| 本地大模型 | Ollama |
| 内容生成 | Prompt + 本地 LLM |
| HTML 演示页 | 内置 Markdown 转 HTML |
| 打包 | PyInstaller |
| 安装包 | Inno Setup |

## 项目结构

```text
AI-Studio-Pro/
├── main.py
├── config.json
├── config.example.json
├── requirements.txt
├── assets/
│   └── styles.qss
├── core/
│   ├── ffmpeg.py
│   ├── whisper.py
│   ├── llm.py
│   ├── writer.py
│   ├── slides.py
│   ├── obsidian.py
│   ├── model_discovery.py
│   └── orchestrator.py
├── ui/
│   └── main_window.py
├── packaging/
│   ├── build_exe.ps1
│   └── installer.iss
└── docs/
    ├── INSTALLATION.md
    ├── USER_GUIDE.md
    ├── DEVELOPMENT.md
    └── GITHUB_UPLOAD.md
```

## 快速开始

### 1. 安装基础环境

- Windows 10 / 11
- Python 3.10 或 3.11
- FFmpeg
- Ollama
- 可选：NVIDIA 显卡 + CUDA 12 运行库，用于 Whisper GPU 转写

### 2. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. 准备模型

内容生成模型示例：

```powershell
ollama pull qwen2.5:7b
```

语音转写可以使用 faster-whisper 预设模型，也可以在软件里选择本地模型文件夹。有效的本地 faster-whisper 模型目录通常包含：

```text
model.bin
config.json
tokenizer.json
```

### 4. 启动软件

```powershell
python main.py
```

## 打包 Windows 软件

生成 EXE：

```powershell
.\packaging\build_exe.ps1
```

生成安装包：

1. 先完成 EXE 构建。
2. 安装 Inno Setup。
3. 用 Inno Setup 编译 `packaging/installer.iss`。

安装包默认输出：

```text
dist/AI_Content_Studio_Pro_Setup.exe
```

## 文档

- [安装与环境配置](docs/INSTALLATION.md)
- [使用说明](docs/USER_GUIDE.md)
- [开发与打包说明](docs/DEVELOPMENT.md)
- [上传 GitHub 前检查](docs/GITHUB_UPLOAD.md)
- [更新记录](CHANGELOG.md)

## 注意事项

- `dist/`、`build/`、`output/`、`temp/`、`__pycache__/` 不建议上传到 GitHub。
- 不要把个人模型路径、Obsidian 仓库路径、测试视频或生成内容提交到公开仓库。
- Ollama 模型和 faster-whisper 模型体积较大，应由用户自行下载或选择本地目录。

## License

请在公开发布前自行选择许可证。若暂不添加开源许可证，则默认保留全部权利。
