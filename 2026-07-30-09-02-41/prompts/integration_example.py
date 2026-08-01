"""
AI 8D 报告平台 — Prompt 集成示例

演示如何通过 Jinja2 在运行时组合 00_components/ 中的共享组件
与各步骤的 Prompt 模板，生成最终发送给 LLM 的完整 Prompt。

依赖: pip install jinja2
"""

from pathlib import Path
from jinja2 import Template

PROMPT_DIR = Path(__file__).parent


def load_component(name: str) -> str:
    """加载共享组件文件"""
    path = PROMPT_DIR / "00_components" / f"{name}.md"
    return path.read_text(encoding="utf-8")


def render_prompt(template_path: str, **variables) -> str:
    """通用的 Prompt 渲染函数"""
    template_str = (PROMPT_DIR / template_path).read_text(encoding="utf-8")
    template = Template(template_str)

    # 自动注入共享组件
    shared_components = {
        "defect_categories": load_component("defect_categories"),
        "root_cause_4m1e": load_component("root_cause_4m1e"),
        "output_rules": load_component("output_rules"),
    }
    return template.render(**shared_components, **variables)


# ─── 各步骤的 Prompt 渲染 ───

def step1_vision(image_base64: str) -> str:
    """Step 0: Vision 前置图片分析"""
    template = (PROMPT_DIR / "01_step1_intake/vision_description.md").read_text(encoding="utf-8")
    return template  # Vision Prompt 不含 Jinja2 变量，直接使用


def step1_5w2h(email, images, tenant_context) -> str:
    """Step 1: 多模态 5W2H 提取"""
    return render_prompt(
        "01_step1_intake/prompt_A_5w2h.md",
        email=email,
        images=images,
        tenant_context=tenant_context,
    )


def step1_5_containment(confirmed_5w2h, tenant_context) -> str:
    """Step 1.5: D3 应急围堵"""
    return render_prompt(
        "01_step1_intake/prompt_A5_containment.md",
        confirmed_5w2h=confirmed_5w2h,
        tenant_context=tenant_context,
    )


def step2_root_cause(confirmed_5w2h_summary, d2_fields, supplementary_docs, rag_public_docs, rag_private_docs) -> str:
    """Step 2: 5-Why 双维度根因推演"""
    return render_prompt(
        "02_step2_root_cause/prompt_B_5why.md",
        confirmed_5w2h_summary=confirmed_5w2h_summary,
        D2=type("D2", (), {"ai_5w2h": d2_fields}),
        supplementary_docs=supplementary_docs,
        rag_public_docs=rag_public_docs,
        rag_private_docs=rag_private_docs,
    )


def step3_responsibility(occurrence_cause, escape_cause, contributing_factors, excluded_causes, d2_fields, tenant_context) -> str:
    """Step 3: 责任归属判定"""
    return render_prompt(
        "02_step2_root_cause/prompt_C_responsibility.md",
        occurrence_cause=occurrence_cause,
        escape_cause=escape_cause,
        contributing_factors=contributing_factors,
        excluded_causes=excluded_causes,
        D2=type("D2", (), d2_fields),
        tenant_context=tenant_context,
    )


def step4_actions(confirmed_5w2h, confirmed_occurrence_cause, confirmed_escape_cause,
                  confirmed_responsibility, confirmed_containment, rag_public_docs, rag_private_docs, tenant_context) -> str:
    """Step 4: D5-D8 卡片生成"""
    return render_prompt(
        "03_step3_actions/prompt_D_d5_d8_cards.md",
        confirmed_5w2h=confirmed_5w2h,
        confirmed_occurrence_cause=confirmed_occurrence_cause,
        confirmed_escape_cause=confirmed_escape_cause,
        confirmed_responsibility=confirmed_responsibility,
        confirmed_containment=confirmed_containment,
        rag_public_docs=rag_public_docs,
        rag_private_docs=rag_private_docs,
        tenant_context=tenant_context,
    )


def etl_d1_extraction(d1_text: str) -> str:
    """ETL: D1 章节提取（ETL Prompt 不含 Jinja2 变量，直接传文本）"""
    # ETL 的通用 System Prompt + D1 章节 Prompt 在同一个文件中
    # 实际使用时应提取文件中对应章节的 Prompt 片段并拼接原始文本
    return load_etl_section_prompt("D1") + "\n\n" + d1_text


# ─── 示例：生成完整 Prompt B ───

if __name__ == "__main__":
    # 模拟数据
    confirmed_5w2h_summary = "客户A投诉2026年7月28日到货的瓦楞纸箱出现塌箱，涉及批次20260728-003，数量约5000pcs。"
    d2_fields = {
        "what": {"defect_name": "塌箱", "defect_category": "纸制品"},
        "who": {"customer_company": "客户A公司"},
        "how_much": {"severity_level": "major"},
        "how": {"quantity_affected": "5000pcs"},
        "where": {"discovery_location": "客户仓库"},
        "why_initial": {"preliminary_hypothesis": "纸板边压强度可能不达标"},
    }
    supplementary_docs = []
    rag_public_docs = [{"doc_name": "GB/T 6544-2008 瓦楞纸板", "similarity_score": 0.92, "excerpt": "边压强度检测方法..."}]
    rag_private_docs = [{"doc_name": "2025-Q3 同类塌箱-8D报告", "similarity_score": 0.95, "excerpt": "根因为原纸克重不足..."}]

    prompt_b = step2_root_cause(
        confirmed_5w2h_summary=confirmed_5w2h_summary,
        d2_fields=d2_fields,
        supplementary_docs=supplementary_docs,
        rag_public_docs=rag_public_docs,
        rag_private_docs=rag_private_docs,
    )

    print("=" * 60)
    print("生成的 Prompt B (前 500 字符):")
    print("=" * 60)
    print(prompt_b[:500])
    print("...")
    print(f"\n总长度: {len(prompt_b)} 字符")
