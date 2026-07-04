# 安装与环境配置

本文档说明如何在 Windows 上运行 AI Content Studio Pro。

## 系统要求

- Windows 10 / 11 64 位
- Python 3.10 或 3.11
- FFmpeg
- Ollama
- 至少一个 Ollama 内容生成模型
- 可选：NVIDIA 显卡和 CUDA 12 运行库

## 安装 Python 依赖

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 安装 FFmpeg

软件依赖 FFmpeg 提取视频音频。安装完成后，需要确保命令行可以直接运行：

```powershell
ffmpeg -version
```

如果命令不可用，请把 FFmpeg 的 `bin` 目录加入系统 PATH。

## 安装 Ollama 与内容模型

安装 Ollama 后，先拉取一个内容生成模型：

```powershell
ollama pull qwen2.5:7b
```

可选模型示例：

```powershell
ollama pull qwen2.5:14b
ollama pull deepseek-r1:14b
ollama pull llama3:8b
```

启动 Ollama 后，软件会优先从 Ollama 服务读取本地模型；如果服务不可用，会尝试从命令行或本地模型目录读取。

## 配置 faster-whisper

语音转写支持两种方式：

1. 使用软件内置预设：`tiny`、`base`、`small`、`medium`、`large-v3`
2. 选择本地 faster-whisper 模型文件夹

有效的本地模型文件夹通常包含：

```text
model.bin
config.json
tokenizer.json
```

如果首次使用预设模型，faster-whisper 会联网下载模型。网络不稳定时，建议提前下载模型并在软件里选择本地文件夹。

## CUDA GPU 加速

如果电脑有 NVIDIA 显卡，软件会尝试使用 CUDA 加速 Whisper 转写。常见需要的运行库包括：

```text
cublas64_12.dll
cublasLt64_12.dll
cudnn64_9.dll
nvrtc64_120_0.dll
```

可以在 `config.json` 里配置 CUDA 运行库搜索目录：

```json
{
  "whisper": {
    "cuda_search_dirs": [
      "D:\\YourCudaRuntime"
    ]
  }
}
```

如果 GPU 组件不完整，软件会给出提示；在 `device` 为 `auto` 时，部分 CUDA 错误会自动回退到 CPU。

## 启动

```powershell
python main.py
```

打包后的版本会把用户配置和输出内容保存到：

```text
C:\Users\你的用户名\Documents\AI Content Studio Pro
```
