# 使用说明

AI Content Studio Pro 的核心流程是：导入视频、选择模型、勾选输出、开始分析、查看结果。

## 1. 导入视频

支持拖拽视频到窗口，也可以点击选择文件。

建议格式：

- MP4
- MOV
- MKV
- AVI
- WEBM

## 2. 选择语音转写模型

语音转写区域支持：

- 预设模型：`tiny`、`base`、`small`、`medium`、`large-v3`
- 本地模型文件夹：选择包含 `model.bin` 和 `config.json` 的 faster-whisper 模型目录

模型越大，识别准确率通常越高，但速度更慢，占用资源也更高。

## 3. 选择内容生成模型

内容生成使用 Ollama 本地模型。点击刷新本地模型后，软件会自动读取可用于写作生成的模型。

推荐模型：

- `qwen2.5:7b`
- `qwen2.5:14b`
- `deepseek-r1:14b`
- `llama3:8b`

软件会过滤 `nomic-embed-text` 这类 embedding 模型，因为它们不适合写作生成。

## 4. 勾选输出模式

可选输出包括：

- Markdown 知识文章：适合知识库、公众号草稿、Notion 沉淀
- 小红书爆款文案：包含标题、钩子、正文、互动引导和标签
- 公众号格式：偏完整成稿和排版结构
- 学习总结：适合课程整理、复盘、个人笔记
- 爆款标题库：生成标题和开头钩子
- HTML 演示 PPT：生成 `slides.md` 和可用浏览器打开的 `slides.html`

## 5. 查看输出文件

分析完成后，右侧输出列表会显示生成文件。常见文件包括：

```text
transcript.txt
article.md
xiaohongshu.md
wechat.md
summary.md
hooks.txt
slides.md
slides.html
metadata.json
```

可以选中文件后预览内容，也可以打开输出目录。

## 6. 打开 HTML 演示 PPT

勾选“HTML演示PPT”后，会生成：

```text
slides.html
```

打开方式：

1. 在输出列表中选中 `slides.html`
2. 点击打开，或在文件夹中双击
3. 浏览器里使用左右方向键翻页

## 7. 推送到 Obsidian

如果你认可某篇文章，可以直接推送到 Obsidian。

首次使用：

1. 点击“绑定Obsidian”
2. 选择你的 Obsidian Vault 根目录
3. 目录中必须包含 `.obsidian` 文件夹

推送文章：

1. 在输出文件列表中选中 `article.md`、`wechat.md`、`summary.md`、`slides.md`、`hooks.txt` 或 `slides.html`
2. 点击“推送Obsidian”
3. 文件会复制到 Vault 下的 `AI Content Studio` 文件夹

默认支持推送：

- `.md`
- `.txt`
- `.html`

## 8. 常见问题

### 无法连接 Ollama

请确认 Ollama 已启动，并且模型已经下载：

```powershell
ollama list
```

### faster-whisper 下载失败

如果错误里出现网络中断、连接关闭、下载不完整等信息，建议选择本地 faster-whisper 模型文件夹。

### 提示缺少 CUDA DLL

说明 GPU 加速运行库不完整。可以安装 CUDA 12 相关运行库，或把语音转写设备改成 CPU。

### 安装时提示文件被占用

请关闭正在运行的软件窗口，再点安装器里的重试。如果仍然失败，重启电脑后重新安装。
