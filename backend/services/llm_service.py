import os
from pathlib import Path
from jinja2 import Template
from litellm import completion
from models.schema import ProblemDescription5W2H

# Adjust this path based on where you run the server
PROMPT_DIR = Path(__file__).parent.parent / "prompts"

class LLMService:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name

    def load_component(self, name: str) -> str:
        """加载共享组件文件"""
        path = PROMPT_DIR / "00_components" / f"{name}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def render_prompt(self, template_path: str, **variables) -> str:
        """通用的 Prompt 渲染函数"""
        template_str = (PROMPT_DIR / template_path).read_text(encoding="utf-8")
        template = Template(template_str)

        # 自动注入共享组件
        shared_components = {
            "defect_categories": self.load_component("defect_categories"),
            "root_cause_4m1e": self.load_component("root_cause_4m1e"),
            "output_rules": self.load_component("output_rules"),
        }
        return template.render(**shared_components, **variables)

    def extract_5w2h(self, email_data: dict, images: list, tenant_context: dict) -> ProblemDescription5W2H:
        """
        调用 LLM 解析 5W2H
        """
        prompt = self.render_prompt(
            "01_step1_intake/prompt_A_5w2h.md",
            email=email_data,
            images=images,
            tenant_context=tenant_context,
        )

        # 构造发给大模型的消息
        messages = [
            {"role": "system", "content": "你是一名资深包装供应链质量工程师，具有15年现场经验。"},
            {"role": "user", "content": prompt}
        ]

        # LiteLLM 调用，并通过 response_format 强制输出符合 Pydantic schema 的 JSON
        response = completion(
            model=self.model_name,
            messages=messages,
            response_format=ProblemDescription5W2H
        )

        # litellm returns the structured response as a JSON string in message.content
        # You can parse it back to a Pydantic object
        content = response.choices[0].message.content
        return ProblemDescription5W2H.model_validate_json(content)
