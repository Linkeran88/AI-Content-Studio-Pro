from __future__ import annotations

import html
import re
from pathlib import Path


def export_html_slides(markdown_text: str, output_path: Path, title: str = "AI Content Studio Pro") -> Path:
    slides = _split_slides(markdown_text)
    rendered_slides = "\n".join(_render_slide(slide, index + 1, len(slides)) for index, slide in enumerate(slides))
    document = HTML_TEMPLATE.format(
        title=html.escape(title),
        slides=rendered_slides,
        total=len(slides),
    )
    output_path.write_text(document, encoding="utf-8")
    return output_path


def _split_slides(markdown_text: str) -> list[str]:
    normalized = markdown_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ["# 演示稿\n\n暂无内容"]

    slides = [part.strip() for part in re.split(r"\n\s*---\s*\n", normalized) if part.strip()]
    if len(slides) > 1:
        return slides

    heading_splits = re.split(r"(?=\n#{1,2}\s+)", "\n" + normalized)
    slides = [part.strip() for part in heading_splits if part.strip()]
    return slides or [normalized]


def _render_slide(markdown_text: str, index: int, total: int) -> str:
    content = _markdown_to_html(markdown_text)
    return f"""<section class="slide" data-slide="{index}">
  <div class="slide-inner">
    {content}
    <footer>{index} / {total}</footer>
  </div>
</section>"""


def _markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    list_type: str | None = None
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(part.strip() for part in paragraph if part.strip())
            if text:
                output.append(f"<p>{_inline(text)}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    for line in lines:
        raw = line.rstrip()
        stripped = raw.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(raw)
            continue

        if not stripped:
            flush_paragraph()
            close_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = min(len(heading.group(1)), 3)
            output.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            close_list()
            output.append(f"<blockquote>{_inline(stripped.lstrip('>').strip())}</blockquote>")
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", stripped)
        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if bullet or ordered:
            flush_paragraph()
            next_list_type = "ul" if bullet else "ol"
            if list_type != next_list_type:
                close_list()
                output.append(f"<{next_list_type}>")
                list_type = next_list_type
            item = bullet.group(1) if bullet else ordered.group(1)
            output.append(f"<li>{_inline(item)}</li>")
            continue

        close_list()
        paragraph.append(stripped)

    flush_paragraph()
    close_list()
    if in_code:
        output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(output)


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #090b10;
      --panel: #111722;
      --text: #f7fafc;
      --muted: #a9b8cc;
      --accent: #36c98f;
      --blue: #3775ef;
      --line: #243044;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      overflow: hidden;
      background:
        radial-gradient(circle at 15% 18%, rgba(54, 201, 143, 0.18), transparent 28%),
        radial-gradient(circle at 85% 20%, rgba(55, 117, 239, 0.18), transparent 28%),
        var(--bg);
      color: var(--text);
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    }}
    .deck {{
      width: 100vw;
      height: 100vh;
      position: relative;
    }}
    .slide {{
      display: none;
      width: 100vw;
      height: 100vh;
      padding: 5vh 6vw;
    }}
    .slide.active {{
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .slide-inner {{
      width: min(1180px, 100%);
      min-height: min(680px, 82vh);
      display: flex;
      flex-direction: column;
      justify-content: center;
      position: relative;
      padding: 56px 64px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: linear-gradient(145deg, rgba(17, 23, 34, 0.96), rgba(9, 12, 18, 0.96));
      box-shadow: 0 32px 100px rgba(0, 0, 0, 0.35);
    }}
    h1 {{
      margin: 0 0 22px;
      font-size: 56px;
      line-height: 1.08;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 24px;
      font-size: 42px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    h3 {{
      margin: 16px 0 12px;
      color: var(--accent);
      font-size: 28px;
    }}
    p, li {{
      font-size: 25px;
      line-height: 1.55;
      color: var(--muted);
    }}
    p {{
      margin: 10px 0;
    }}
    ul, ol {{
      margin: 12px 0 0;
      padding-left: 34px;
    }}
    li {{
      margin: 10px 0;
    }}
    strong {{
      color: var(--text);
    }}
    blockquote {{
      margin: 22px 0;
      padding: 18px 22px;
      border-left: 5px solid var(--accent);
      background: rgba(54, 201, 143, 0.09);
      color: var(--text);
      font-size: 27px;
      line-height: 1.5;
    }}
    code {{
      padding: 2px 7px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--text);
    }}
    pre {{
      max-height: 330px;
      overflow: auto;
      padding: 18px;
      border-radius: 12px;
      background: #070a0f;
      border: 1px solid var(--line);
    }}
    footer {{
      position: absolute;
      right: 34px;
      bottom: 24px;
      color: #728197;
      font-size: 15px;
    }}
    .controls {{
      position: fixed;
      left: 50%;
      bottom: 22px;
      transform: translateX(-50%);
      display: flex;
      gap: 10px;
      align-items: center;
      color: var(--muted);
      font-size: 14px;
    }}
    button {{
      border: 1px solid var(--line);
      border-radius: 9px;
      background: rgba(17, 23, 34, 0.9);
      color: var(--text);
      padding: 9px 13px;
      cursor: pointer;
    }}
    button:hover {{
      border-color: var(--blue);
    }}
    @media print {{
      body {{ overflow: visible; background: white; }}
      .deck {{ height: auto; }}
      .slide {{ display: flex; page-break-after: always; background: #090b10; }}
      .controls {{ display: none; }}
    }}
  </style>
</head>
<body>
  <main class="deck">
    {slides}
  </main>
  <nav class="controls">
    <button onclick="previousSlide()">上一页</button>
    <span id="counter">1 / {total}</span>
    <button onclick="nextSlide()">下一页</button>
  </nav>
  <script>
    const slides = Array.from(document.querySelectorAll('.slide'));
    let current = 0;
    function showSlide(index) {{
      current = Math.max(0, Math.min(slides.length - 1, index));
      slides.forEach((slide, i) => slide.classList.toggle('active', i === current));
      document.getElementById('counter').textContent = `${{current + 1}} / ${{slides.length}}`;
    }}
    function nextSlide() {{ showSlide(current + 1); }}
    function previousSlide() {{ showSlide(current - 1); }}
    window.addEventListener('keydown', event => {{
      if (['ArrowRight', 'PageDown', ' '].includes(event.key)) nextSlide();
      if (['ArrowLeft', 'PageUp', 'Backspace'].includes(event.key)) previousSlide();
      if (event.key === 'Home') showSlide(0);
      if (event.key === 'End') showSlide(slides.length - 1);
    }});
    showSlide(0);
  </script>
</body>
</html>
"""
