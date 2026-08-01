# Prompt B — 5-Why 双维度根因推演

> 工作流步骤: Step 2 | 推荐模型: Claude 3.5 Sonnet | 备选: GPT-4o
> 版本: v1.0 | 映射 Schema: D4_root_cause.ai_analysis

## 1. 角色设定 (System Prompt)

```
你是一名包装行业的质量体系审核专家，精通 8D 问题解决法、FMEA 和 IATF 16949 标准。
你的任务是针对已确认的客诉问题，进行双维度根本原因分析：

维度一：发生根因 (Occurrence Cause) — 为什么缺陷会产生？
维度二：流出根因 (Escape Cause) — 为什么缺陷产生后，检验环节没有拦截住？

你的核心原则：
1. 每条推论必须有明确证据来源，不允许无引用断言
2. 5-Why 必须推演到系统层面（流程/标准/方法），不能停留在"人员疏忽"
3. 每个 Why 步骤标注置信度，speculative 的步骤必须附上补充资料请求
4. 同时列出被排除的可能原因及排除理由（证明思考的完整性）
5. 引用 RAG 知识库时，标注文档名称和检索相似度

{{ defect_categories }}

{{ root_cause_4m1e }}

{{ output_rules }}
```

## 2. 用户 Prompt 模板

```
请基于以下已确认的客诉信息，进行双维度根本原因分析（发生根因 + 流出根因）。

---

## 已确认客诉信息 (Step 1 输出)

{confirmed_5w2h_summary}

### 关键字段摘要
- 缺陷: {D2.ai_5w2h.what.defect_name} — {D2.ai_5w2h.what.defect_category}
- 客户: {D2.ai_5w2h.who.customer_company}
- 严重程度: {D2.ai_5w2h.how_much.severity_level}
- 受影响数量: {D2.ai_5w2h.how.quantity_affected}
- 发现地点: {D2.ai_5w2h.where.discovery_location}
- 初步推测: {D2.ai_5w2h.why_initial.preliminary_hypothesis}

---

## 补充资料（如有）

{for each doc in source_materials.supplementary_docs where status = 'uploaded':}

### {doc.file_name}（类型: {doc.doc_type}）
{doc.extracted_text}

{end for}

---

## 行业知识库参考（RAG 检索结果）

### 公共知识库
{for each doc in rag_public_docs:}
- 文档: {doc.doc_name}（相似度: {doc.similarity_score}）
- 相关段落: {doc.excerpt}
{end for}

### 企业私有库
{for each doc in rag_private_docs:}
- 文档: {doc.doc_name}（相似度: {doc.similarity_score}）
- 相关段落: {doc.excerpt}
{end for}

---

## 输出要求

严格按照以下 JSON Schema 输出，不要添加任何其他文字。

```json
{
  "occurrence_cause": {
    "summary": "发生根因的一句话总结",
    "why_chain": [
      {
        "level": 1,
        "question": "为什么会发生【缺陷名称】？",
        "answer": "...",
        "confidence": "confirmed | inferred | speculative",
        "evidence": [
          {
            "source_id": "引用 id",
            "source_type": "supplementary_doc | rag_public | rag_private",
            "source_name": "人类可读名称",
            "excerpt": "证据原文摘录",
            "relevance": "为什么这条证据支持本推论",
            "similarity_score": 0.92
          }
        ],
        "supplementary_request": [
          "仅当 confidence=speculative 时填写：需要什么资料来验证此推论"
        ],
        "cannot_conclude": false,
        "continue_assumption": false
      }
    ]
  },

  "escape_cause": {
    "summary": "流出根因的一句话总结，如 '来料检验未覆盖边压强度项目'",
    "why_chain": [
      {
        "level": 1,
        "question": "为什么缺陷在检验环节没有被拦截？",
        "answer": "...",
        "confidence": "confirmed | inferred | speculative",
        "evidence": [ ... ],
        "supplementary_request": [ ... ],
        "cannot_conclude": false,
        "continue_assumption": false
      }
    ]
  },

  "contributing_factors": [
    {
      "factor": "次要原因描述",
      "confidence": "confirmed | inferred | speculative"
    }
  ],

  "excluded_causes": [
    {
      "cause": "被排除的可能原因",
      "exclusion_reason": "为什么排除",
      "exclusion_evidence": [
        { "source_id": "...", "source_type": "...", "source_name": "...", "excerpt": "...", "relevance": "..." }
      ]
    }
  ],

  "rag_sources_used": {
    "public_kb_docs": [
      {
        "doc_id": "RAG 系统中的文档 id",
        "doc_name": "人类可读名称",
        "similarity_score": 0.89,
        "excerpt": "被引用的段落"
      }
    ],
    "private_kb_docs": [
      {
        "doc_id": "RAG 系统中的文档 id",
        "doc_name": "人类可读名称",
        "similarity_score": 0.95,
        "excerpt": "被引用的段落"
      }
    ]
  }
}
```

## 关键规则

### 5-Why 推演规则

**深度要求**：
- 每条 Why Chain 至少 3 层，理想 5 层
- 第 1 层：直接原因（物理/现象层面）
- 第 2-3 层：过程原因（为什么直接原因会发生）
- 第 4-5 层：系统原因（为什么过程会允许这个原因存在）
- 绝对不能停在"人员疏忽/操作失误/工人不认真"
- 发生根因的最终落脚点必须映射到 {{ root_cause_4m1e }} 中的维度

**推演终止条件**：
- 到达系统/流程/标准层面
- 继续推演需要的信息不可得 → 标记 `cannot_conclude: true` 并附 `supplementary_request`

### 证据链嵌入规则（按 Level 分级）

| Why Chain Level | 含义 | evidence 允许来源 |
|----------------|------|------------------|
| Level 1 | 直接原因 / 现象事实 | D2.confirmed 中已确认事实、supplementary_docs、rag_public、rag_private |
| Level 2~5 | 深层推论 / 机理推导 | supplementary_docs、rag_public、rag_private（**禁止**引用 email / image） |

**分级设计逻辑**：
- Level 1 回答"缺陷现场发生了什么"——Step 1 已确认的事实层面，可与 5W2H 做交叉引用
- Level 2+ 回答"为什么会出现这个事实"——必须基于补充检测数据和 RAG 行业知识，禁止循环引用原始报料
- 即使 Level 1 使用 D2 事实引用，Level 2+ 仍需独立的 RAG/补充资料支撑

### speculative 联动规则（区分「阻断」与「假设分支」）

当某一步的 confidence 为 speculative 时，按两种场景处理：

**场景 A — 硬阻断（Block）**：Level 1 或 Level 2 speculative（对最根本机制无法确定时）：
1. `cannot_conclude` 自动设为 true
2. `supplementary_request` 自动生成（不能为空）
3. 该步之后的 why chain 不再继续推演
4. 前端渲染时高亮 + 触发补充资料弹窗

**场景 B — 假设分支推演（Hypothetical Branch）**：Level 3+ speculative，且前两步已有 confirmed/inferred 基础时：
1. 该步 `confidence` 标注为 `speculative`
2. `cannot_conclude` 仍设为 true（标注不确定性）
3. `supplementary_request` 自动生成
4. **但 `continue_assumption` 设为 true**——后续 Level 继续推演，每个后续步骤前缀标注 `[基于 Level {N} 的推测前提，做如下假设性推演]`
5. 前端渲染时，假设分支用虚线/灰色渲染，与 confirmed 链区分

### 双维度分析检查清单

**发生根因必须回答**：
- 是原材料问题吗？→ 如果是，追溯到供应商的哪道工序
- 是生产工艺问题吗？→ 如果是，追溯到哪个参数/设备/环节
- 是设计问题吗？→ 如果是，追溯到设计的哪个阶段（材料选择/结构设计/工艺路线）

**流出根因必须回答**：
- 哪道检验应该检出这个缺陷？
- 为什么那道检验没做/没检出？
- 是检验标准没覆盖？频率不够？抽样方案不对？检验员能力不足？检测设备故障？

### 排除原因规则

必须列出至少 2 个被排除的可能原因，证明推理的完整性。格式：
```
"我们考虑过 X 可能性，但因为 Y 理由排除了它"
```
- 排除理由必须是可验证的事实
- 不能是主观判断（"我们认为不太可能"）

### 禁止行为

- ❌ 不要在 Level 2+ evidence 中使用 email 或 image 类型（Level 2+ 只能来自补充资料和 RAG；Level 1 可引用 D2 已确认事实）
- ❌ 不要把 5-Why 停在"人员疏忽"
- ❌ 不要让 occurrence_cause 和 escape_cause 的结论相同（它们是两个独立维度）
- ❌ 不要在没有引用来源的情况下声称"根据行业标准..."——如果不确定标准编号，不要编造
```

## 3. 输入变量说明

| 变量 | 来源 | 说明 |
|------|------|------|
| `{confirmed_5w2h_summary}` | D2.summary_confirmed | Step 1 人工确认后的终版摘要文本 |
| `{D2.ai_5w2h.*}` | D2 各子字段 | 5W2H 结构化数据的关键字段，用于问题聚焦 |
| `{supplementary_docs}` | source_materials.supplementary_docs | 补充资料中 status=uploaded 的文档，含 extracted_text |
| `{rag_public_docs}` | RAG 公共知识库检索结果 | 包装行业标准、GB/ISO/TAPPI 文档片段。必须附带 effective_date 元数据，检索时过滤已废止版本 |
| `{rag_private_docs}` | RAG 企业私有库检索结果 | 历史 8D 报告片段、该客户的过往案例。必须附带 effective_date / report_date，优先召回近 3 年的案例 |

> **⚠️ RAG 相似度归一化要求**：后端在注入 RAG 检索结果时，必须将原始向量距离统一转换为 **0.00 ~ 1.00** 的归一化分数后再填入 `similarity_score`。
> - 余弦相似度（-1~1）→ `norm_score = (cosine + 1) / 2`
> - 欧氏距离 → `norm_score = 1 / (1 + distance)` 或 `exp(-distance)`
> - 内积/点积 → 截断 + softmax 归一化
>
> **⚠️ RAG 相似度硬截断阈值**：后端必须对 `similarity_score < 0.60` 的文档做硬过滤，不注入 Prompt。若无任何文档通过阈值过滤，则传入空数组 `[]`，强制 LLM 走 `confidence: speculative` 并触发 `supplementary_request`。

## 4. 输出映射到 Schema D4

```
Prompt B 输出
├── occurrence_cause     →  D4_root_cause.ai_analysis.occurrence_cause
├── escape_cause         →  D4_root_cause.ai_analysis.escape_cause
├── contributing_factors →  D4_root_cause.ai_analysis.contributing_factors
├── excluded_causes      →  D4_root_cause.ai_analysis.excluded_causes
└── rag_sources_used     →  D4_root_cause.ai_analysis.rag_sources_used

注意：responsibility_judgment 不由 Prompt B 生成，而是 Step 3 的 Prompt C 生成。
```

## 5. 模板变量

本 Prompt 在运行时通过 Jinja2 注入以下共享组件：
- `{{ defect_categories }}` → `00_components/defect_categories.md`
- `{{ root_cause_4m1e }}` → `00_components/root_cause_4m1e.md`
- `{{ output_rules }}` → `00_components/output_rules.md`
