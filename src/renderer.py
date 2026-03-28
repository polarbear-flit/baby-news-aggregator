import os
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader


def render(articles: list[dict], analysis: dict) -> str:
    """Jinja2テンプレートを使ってHTML文字列を返す"""
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(os.path.abspath(template_dir)))
    template = env.get_template("index.html.j2")

    jst = timezone(timedelta(hours=9))
    generated_at = datetime.now(jst).strftime("%Y年%m月%d日 %H:%M JST")

    return template.render(
        articles=articles,
        analysis=analysis,
        generated_at=generated_at,
    )
