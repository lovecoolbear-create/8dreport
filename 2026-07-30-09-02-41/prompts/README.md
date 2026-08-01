# AI 8D 报告平台 — Prompt 策略库

> 版本: v1.0 | 原文档: `Core_Prompts_Strategy.md` (v1.7, 保留作全量参考)

## 目录结构

```
prompts/
├── 00_components/                   # 共享组件与知识库
│   ├── defect_categories.md          # 5 大包装材质缺陷分类大纲
│   ├── root_cause_4m1e.md            # 包装行业 4M1E 追溯维度
│   └── output_rules.md              # 通用 JSON 格式与置信度规则
│
├── 01_step1_intake/                 # 问题定义与应急 (Step 1 & 1.5)
│   ├── vision_description.md        # Vision LLM 前置图片描述 Prompt
│   ├── prompt_A_5w2h.md              # Step 1: 多模态 5W2H 提取
│   └── prompt_A5_containment.md     # Step 1.5: D3 应急围堵措施建议
│
├── 02_step2_root_cause/             # 根因推演与责任 (Step 2 & 3)
│   ├── prompt_B_5why.md              # Step 2: 5-Why 双维度根因推演
│   └── prompt_C_responsibility.md   # Step 3: 责任归属判定
│
├── 03_step3_actions/                # 措施卡片生成 (Step 4)
│   └── prompt_D_d5_d8_cards.md       # Step 4: D5-D8 行动方案生成
│
├── 04_etl_pipeline/                 # 历史数据清洗管线 (Phase 2)
│   └── prompt_ETL_extraction.md      # LLM-as-ETL 历史报告结构化提取
│
├── integration_example.py           # Python 集成示例
└── README.md                        # 本文件
```

## 各部分职责

| 目录 | 职责 | 推荐模型 |
|------|------|---------|
| `00_components/` | 存放多处复用的业务静态知识和通用约束。修改一处，所有引用自动生效 | — |
| `01_step1_intake/` | 将原始文本/图片转化为事实数据并制定紧急止血方案 | GPT-4o / Claude 3.5 Sonnet |
| `02_step2_root_cause/` | 从事实出发做深度因果推演与责任划分 | Claude 3.5 Sonnet / GPT-4o |
| `03_step3_actions/` | 基于已确认根因生成纠正/验证/预防/结案卡片 | GPT-4o |
| `04_etl_pipeline/` | 离线批量将 Word/PDF 历史报告解析并结构化入库 | DeepSeek-V3 / Qwen3-235B |

## 使用方式

所有 Prompt 文件是纯 Markdown，System Prompt 和 User Prompt 模板分别标识。运行时通过 Jinja2 注入共享组件：

```python
from pathlib import Path
from jinja2 import Template

PROMPT_DIR = Path("./prompts")

def render_prompt_b(confirmed_5w2h, rag_docs):
    # 1. 读取共享组件
    defect_categories = (PROMPT_DIR / "00_components/defect_categories.md").read_text()
    root_cause_4m1e = (PROMPT_DIR / "00_components/root_cause_4m1e.md").read_text()
    output_rules = (PROMPT_DIR / "00_components/output_rules.md").read_text()

    # 2. 读取 Prompt 模板
    template_str = (PROMPT_DIR / "02_step2_root_cause/prompt_B_5why.md").read_text()
    template = Template(template_str)

    # 3. 渲染
    return template.render(
        defect_categories=defect_categories,
        root_cause_4m1e=root_cause_4m1e,
        output_rules=output_rules,
        confirmed_5w2h_summary=confirmed_5w2h["summary"],
        # ...
    )
```

完整示例见 `integration_example.py`。

## 工作流顺序

```
Vision 前置 (vision_description.md)
    ↓
Prompt A (prompt_A_5w2h.md) ─── 人工确认 5W2H
    ↓
Prompt A.5 (prompt_A5_containment.md) ─── 人工确认 D3
    ↓
Prompt B (prompt_B_5why.md) ─── 人工确认根因
    ↓
Prompt C (prompt_C_responsibility.md) ─── 人工确认责任
    ↓
Prompt D (prompt_D_d5_d8_cards.md) ─── 人工审核 D5-D8
    ↓
ETL (prompt_ETL_extraction.md) ─── Phase 2 批量入库
```
