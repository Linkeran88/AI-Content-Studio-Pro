from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.llm import OllamaClient


ProgressCallback = Callable[[str, int, int], None]


@dataclass(frozen=True)
class OutputDefinition:
    key: str
    label: str
    filename: str
    instruction: str


OUTPUT_DEFINITIONS: dict[str, OutputDefinition] = {
    "article": OutputDefinition(
        key="article",
        label="Markdown知识文章",
        filename="article.md",
        instruction=(
            "输出一篇适合公众号、Notion 和知识库沉淀的 Markdown 知识文章。"
            "要求包含：标题、摘要、核心观点、结构化正文、行动建议、金句摘录。"
            "语言要专业、清晰、去口语化。"
        ),
    ),
    "xiaohongshu": OutputDefinition(
        key="xiaohongshu",
        label="小红书爆款文案",
        filename="xiaohongshu.md",
        instruction=(
            "输出小红书爆款文案。要求包含：3个标题备选、开头钩子、正文、情绪强化表达、"
            "互动引导、话题标签。语气要有传播感，但不要虚假夸张。"
        ),
    ),
    "wechat": OutputDefinition(
        key="wechat",
        label="公众号格式",
        filename="wechat.md",
        instruction=(
            "输出微信公众号成稿。要求包含：标题、导语、分段小标题、正文、结尾观点、"
            "适合排版的引用金句。整体要稳重、有观点、有可读性。"
        ),
    ),
    "summary": OutputDefinition(
        key="summary",
        label="学习总结",
        filename="summary.md",
        instruction=(
            "输出学习总结。要求包含：一句话结论、知识框架、关键概念、可执行清单、"
            "复盘问题。内容要适合个人学习和课程整理。"
        ),
    ),
    "titles": OutputDefinition(
        key="titles",
        label="爆款标题库",
        filename="hooks.txt",
        instruction=(
            "输出 20 条标题和开头组合。每条包含：标题、前3秒钩子、适合平台。"
            "标题要具体、清楚、有点击欲望，避免标题党。"
        ),
    ),
    "slides": OutputDefinition(
        key="slides",
        label="HTML演示PPT",
        filename="slides.md",
        instruction=(
            "输出一份 Markdown 演示稿，用于自动生成 HTML PPT。"
            "要求：8到12页；每页用单独一行 --- 分隔；每页包含一个清晰标题和3到5条要点；"
            "第一页是标题页，最后一页是行动建议或总结页。"
            "内容要适合演讲展示，句子短、层级清楚、不要堆长段落。"
        ),
    ),
}


BASE_PROMPT = """你是内容分析 + 爆款写作专家。

请基于视频转写内容完成商业级内容处理：

1. 提取核心观点，最多5条
2. 分析逻辑结构
3. 提取金句
4. 去口语化重写
5. 保留原视频的核心观点，不编造事实
6. 适合中文自媒体发布

本次具体输出要求：
{instruction}

视频转写内容：
{transcript}
"""


class ContentWriter:
    def __init__(self, llm: OllamaClient, model_name: str) -> None:
        self.llm = llm
        self.model_name = model_name

    def generate(self, transcript: str, output_keys: list[str], on_step: ProgressCallback | None = None) -> dict[str, str]:
        selected_definitions = [OUTPUT_DEFINITIONS[key] for key in output_keys if key in OUTPUT_DEFINITIONS]
        if not selected_definitions:
            raise RuntimeError("没有可生成的输出模式。")

        contents: dict[str, str] = {}
        total = len(selected_definitions)
        for index, definition in enumerate(selected_definitions, start=1):
            if on_step:
                on_step(definition.label, index, total)
            prompt = BASE_PROMPT.format(instruction=definition.instruction, transcript=transcript)
            contents[definition.key] = self.llm.generate(self.model_name, prompt)
        return contents

    @staticmethod
    def filename_for(key: str) -> str:
        return OUTPUT_DEFINITIONS[key].filename
