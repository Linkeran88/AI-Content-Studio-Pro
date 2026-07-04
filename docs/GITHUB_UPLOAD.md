# 上传 GitHub 前检查

这份清单用于避免把本地隐私文件、模型文件和打包产物误传到 GitHub。

## 建议上传的内容

```text
assets/
core/
docs/
packaging/
ui/
main.py
config.json
config.example.json
requirements.txt
README.md
CHANGELOG.md
.gitignore
```

## 不建议上传的内容

```text
.venv/
build/
dist/
output/
temp/
__pycache__/
*.pyc
*.spec
```

模型文件也不要上传，例如：

```text
model.bin
*.gguf
Ollama blobs/
faster-whisper 模型目录
```

## 上传前检查个人路径

请确认这些内容没有写死个人电脑路径：

- Obsidian Vault 路径
- Ollama 模型目录
- faster-whisper 模型目录
- CUDA 运行库目录
- 测试视频路径
- 输出内容路径

本项目已提供 `config.example.json`，公开仓库里建议使用通用配置。

## 推荐 Git 命令

在项目根目录执行：

```powershell
git init
git add .
git status
```

确认没有 `dist/`、`output/`、`temp/`、本地模型或私人文件后，再提交：

```powershell
git commit -m "Initial release"
```

绑定远程仓库：

```powershell
git branch -M main
git remote add origin https://github.com/你的用户名/AI-Content-Studio-Pro.git
git push -u origin main
```

## 安装包发布建议

如果需要给别人下载双击安装包，建议把安装包上传到 GitHub Releases：

```text
AI_Content_Studio_Pro_Setup.exe
```

不要把安装包直接提交到源码仓库。安装包较大，会让仓库变慢，也不利于后续维护。
