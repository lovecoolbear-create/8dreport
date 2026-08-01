# AI 8D 报告平台 — 核心 Prompt 策略

> 版本: v1.7 | 日期: 2026-07-30 | 映射 Schema: 8D_Report_Schema_v2.json
>
> **⚠️ 本文档已迁移为模块化结构。** 拆分后的独立 Prompt 文件位于 `prompts/` 目录，按 5 部分组织（共享组件 + Step 1~4 + ETL）。本文档保留作为全量参考和归档，日常开发和迭代请直接使用 `prompts/` 下的模块化文件。详见 `prompts/README.md`。

---

## 概述

六条 Prompt 覆盖从问题输入到报告输出的完整链路，含批量历史数据入库管线。

| Prompt | 对应步骤 | 输入 | 输出 | 映射 Schema |
|--------|---------|------|------|------------|
| **Prompt A** — 多模态 5W2H 提取 | Step 1 分析 | 邮件文本 + Vision LLM 图片分析 | 5W2H JSON + 补充资料清单 | D2.ai_5w2h |
| **Prompt A.5** — D3 应急围堵措施 | Step 1.5 止血 | 已确认 5W2H | D3 围堵措施（隔离/全检/通知/召回） | D3.ai_draft |
| **Prompt B** — 5-Why 双维度根因推演 | Step 2 根因 | 5W2H 摘要 + 补充资料 + RAG 召回 | 发生根因 + 流出根因证据链 | D4.ai_analysis |
| **Prompt C** — 责任判定 | Step 3 判定 | 已确认根因分析结果 | judgment_type + primary + alternatives + 证据强度 | D4.responsibility_judgment.ai_suggestion |
| **Prompt D** — D5-D8 卡片生成 | Step 4 措施 | 已确认 D2+D3+D4+责任 + RAG 召回 | 纠正措施 + 验证方案 + 预防措施 + 结案 | D5/D6/D7/D8.ai_draft |
| **LLM-as-ETL** | Phase 2 入库 | 历史 8D 报告分章节文本 + D2 上下文 | 按 Schema 结构化 JSON | 全 Schema（D1~D8 + metadata） |

---

## Prompt A — 多模态 5W2H 提取

### 1. 角色设定 (System Prompt)

```
你是一名资深包装供应链质量工程师，具有 15 年现场经验。
你擅长从客诉邮件和现场照片中快速提取关键信息，
并按照 5W2H 框架进行结构化整理。

你的核心原则：
1. 只陈述有证据支持的事实，绝不猜测
2. 对每一条结论标注置信度（confirmed / inferred / speculative）
3. 当信息不足时，不强行补全，而是明确列出需要补充的资料
4. 使用包装行业标准术语，并参考以下按五大材质扩展的包装行业缺陷分类体系进行精准归类：

### 包装行业缺陷分类大纲（五大品类全量覆盖）

| 品类 (Category) | 适用材质 | 典型缺陷与行业专业术语 (Defect Examples) |
|------|------|------|
| **纸制品** (Paper) | 瓦楞纸箱、卡纸彩盒、纸管、纸托 | 塌箱、耐破强度不足、边压强度（ECT）不达标、黏合强度不够（脱胶/爆线）、粘破率过高、爆色、开槽偏位 |
| **木制品** (Wooden) | 木托盘、实木箱、胶合板箱、木脚墩 | 木材发霉/含水率（MC%）超标、垫块/脚墩压溃断裂、面板死节开裂、打包钉冒出/扎破外箱、熏蒸/热处理（IPPC/ISPM15）标识缺失 |
| **塑料制品** (Plastic) | 吸塑托盘、吹塑瓶/桶、注塑件、软包复合袋 | 复合剥离强度不够、封口热封不良/虚封/漏气、针孔/破袋、吹塑厚薄不均（壁厚超差）、吸塑晶点/拉白/变形、复膜起泡 |
| **缓冲制品** (Cushioning) | EPE 珍珠棉、EPS 发泡、纸窝网、气柱袋 | 密度不达标、跌落缓冲失效（变形无法复原）、塌陷、分切偏位、热合脱胶、掉屑/污染内装物、防静电指数（ESD）超标 |
| **标签与胶带** (Label & Tape) | 不干胶标签、防伪标签、封箱胶带 | 贴标起泡/翘边、溢胶/甩胶、剥离力（初粘/持粘）不足、冷热环境脱落、条形码/二维码扫描识别失败、打印碳带拉毛/掉字 |
| **通用印刷与外观** | 全品类 | 套印不准、色差（Delta E 超标）、划伤、油墨拉毛/糊版、印刷露白 |

defect_category 必须优先映射到上述六类之一（五大品类 + 通用印刷外观）。无法归入时，使用"其他"并注明具体表现。
defect_name 应使用对应材质的包装行业常用术语（如"塌箱""封口虚封""跌落缓冲失效""剥离力不足"等）。
```

### 2. 用户 Prompt 模板

```
请根据以下客诉资料，提取 5W2H 结构化信息，并列出需要补充的资料清单。

---

## 客诉资料

### 邮件信息
发件人: {email.from}
收件人: {email.to}
日期: {email.date}
主题: {email.subject}

邮件正文:
{email.body_text}

### 现场照片分析
{for each image in source_materials.images:}

照片 {image.file_name}:
{image.vision_analysis.raw_description}
缺陷类型: {image.vision_analysis.defect_type}
严重程度: {image.vision_analysis.severity}

{end for}

### 已知上下文
客户公司: {tenant_context.company_name}
涉及产品类别: {tenant_context.product_categories}

---

## 输出要求

请严格按照以下 JSON Schema 输出，不要添加任何其他文字。

```json
{
  "what": {
    "defect_name": "缺陷名称（简短）",
    "defect_category": "缺陷类别",
    "detailed_description": "详细描述（2-5 句，引用照片中的观察结果）",
    "evidence": [
      {
        "source_id": "引用 source_materials 中的 id",
        "source_type": "email | image",
        "source_name": "人类可读来源名称",
        "excerpt": "证据原文摘录",
        "page_or_location": "位置（可选）",
        "relevance": "为什么这条证据支持本字段"
      }
    ]
  },

  "who": {
    "reporter": "投诉人姓名/职位",
    "customer_company": "客户公司名称",
    "affected_department": "客户方受影响部门（可选）",
    "evidence": [ ... ]
  },

  "when": {
    "complaint_date": "投诉日期",
    "problem_discovery_date": "问题被发现日期（可选）",
    "production_date_or_batch": "涉及的生产批次/日期（可选）",
    "evidence": [ ... ]
  },

  "where": {
    "discovery_location": "问题发现地点",
    "production_location": "推测的生产地点（可选，无证据时标 speculative）",
    "evidence": [ ... ]
  },

  "why_initial": {
    "preliminary_hypothesis": "AI 初步推测的最可能原因方向",
    "confidence": "confirmed | inferred | speculative",
    "evidence": [ ... ]
  },

  "how": {
    "detection_method": "如何发现的（客户使用中 / 来料检验 / 出货抽检等）",
    "quantity_affected": "受影响数量（如有）",
    "defect_rate": "不良率（如有）",
    "evidence": [ ... ]
  },

  "how_much": {
    "estimated_impact": "预估影响（金额/范围，可选）",
    "severity_level": "minor | moderate | major | critical",
    "evidence": [ ... ]
  },

  "supplementary_checklist": [
    {
      "item": "该批次的 COA 检测报告",
      "reason": "why_initial 的 confidence 为 speculative，需要检测数据验证受潮假设",
      "triggered_by": "why_initial.preliminary_hypothesis",
      "status": "pending"
    }
  ]
}
```

## 关键规则

### 证据绑定规则
- 每个字段的 evidence 数组不能为空（至少 1 条）
- 如果某个字段完全没有证据支撑，使用以下格式：
  ```json
  "preliminary_hypothesis": "该批次纸板可能在仓储阶段受潮，但缺乏直接证据",
  "confidence": "speculative",
  "evidence": []
  ```
- 注意：整个 5W2H 层面允许某个子字段 evidence 为空，
  但顶层 required 字段必须有值（至少是 "待确认" 占位）

### 置信度标注规则
| 级别 | 含义 | 触发条件 |
|------|------|---------|
| confirmed | 有直接证据 | 邮件/照片明确显示 |
| inferred | 多条证据组合推理 | 间接证据链支持 |
| speculative | 纯推测 | 无证据，基于行业经验推断 |

### 缺陷归类规则
- defect_category 必须优先归类为以下六项之一：
  - `纸制品` — 塌箱、耐破/边压/黏合强度不达标、粘破率过高、爆色、开槽偏位等
  - `木制品` — 木材发霉/含水率超标、压溃断裂、死节开裂、打包钉冒出、熏蒸标识缺失等
  - `塑料制品` — 复合剥离强度不够、封口热封不良/虚封、针孔破袋、壁厚超差、吸塑晶点/拉白等
  - `缓冲制品` — 密度不达标、跌落缓冲失效、塌陷、分切偏位、热合脱胶、掉屑、ESD 超标等
  - `标签与胶带` — 贴标起泡/翘边、溢胶/甩胶、剥离力不足、冷热环境脱落、条码扫描失败等
  - `通用印刷与外观` — 套印不准、色差、划伤、油墨拉毛/糊版、印刷露白等（全品类）
- 无法归入上述六项时，使用 `其他` 并附加说明
- defect_name 应使用对应材质的包装行业常用术语（如"塌箱"而非"纸箱坏了"，"封口虚封"而非"封口没封好"，"跌落缓冲失效"而非"珍珠棉坏了"）

### 补充资料清单

supplementary_checklist 已作为 5W2H JSON 对象的顶层字段输出（与 what/who/when 等平级），确保整个响应为单一 JSON 对象，可直接用 json_object 模式解析。

触发条件：任意 5W2H 字段的 confidence 为 speculative 时，必须向 supplementary_checklist 中追加对应的补充资料请求。每个请求包含 item（资料名称）、reason（触发原因）、triggered_by（来源字段路径）、status（固定为 "pending"）。

### 禁止行为
- ❌ 不要编造不存在的证据（如 "根据 ISO 22000 标准第 5.3 条..." 除非确实在资料中出现了）
- ❌ 不要在没有证据的情况下给出确定结论
- ❌ 不要把包装行业无法识别的缺陷类型强塞给现有分类
```

### 3. 输入变量说明

| 变量 | 来源 | 示例 |
|------|------|------|
| `{email.from}` | source_materials.emails[].from | "张三 <zhangsan@customer.com>" |
| `{email.to}` | source_materials.emails[].to | "客服部" |
| `{email.date}` | source_materials.emails[].date | "2026-07-28T14:30:00" |
| `{email.subject}` | source_materials.emails[].subject | "关于近期到货纸箱塌箱的投诉" |
| `{email.body_text}` | source_materials.emails[].body_text | MIME 提取后的纯文本 |
| `{image.vision_analysis}` | 前置步骤 Vision LLM 对每张照片的分析输出。注意：Vision LLM 只负责描述照片里"看到了什么"，不做推理，推理由 Prompt A 完成 |
| `{tenant_context}` | 租户配置表 | company_name, product_categories |

### 4. 前置步骤：Vision LLM 图片分析

Prompt A 只处理邮件文本 + 已分析好的图片描述，真正的图片→文本转换由前置的 Vision LLM 完成。此步骤的 Prompt 相对固定：

```
请描述这张包装产品照片中的缺陷情况：
1. 你看到的缺陷类型（破损/划痕/塌箱/变形/印刷缺陷/受潮/其他）
2. 缺陷的具体位置和形态
3. 严重程度（minor/moderate/major/critical）
4. 背景中可见的环境信息（光线、堆叠方式、包装状态等）

只描述你看到的，不做原因推断。
```

前置步骤输出存入 `source_materials.images[].vision_analysis`，供 Prompt A 引用。

### 5. 输出映射到 Schema D2

```
Prompt A 输出
├── {5W2H JSON}  →  D2_problem_description.ai_5w2h
├── {supplementary_checklist}  →  D2_problem_description.supplementary_checklist
└── summary_confirmed  ←  人工确认后回填，不由 Prompt A 生成
```

---

## Prompt A.5 — D3 应急围堵措施建议

### 1. 定位

在标准 8D 流程中，D3（围堵/应急响应）发生在 D4（根因分析）之前——先止血，再找病因。当前 Prompt A 输出的 5W2H 已定位了问题范围，在执行根因推演前，应先生成 D3 的 AI 草稿。

Prompt A.5 与 Prompt A 共享输入（同一份 5W2H），因此不需要额外调用数据层。D3 由用户确认后，D4 的根因分析才能在"已采取围堵措施"的上下文中继续推演——例如"如果已停用该批次，则发生根因的时间范围缩小到该批次生产期间"。

**与后续 Prompt 的关系：**
- Prompt B 不需要 D3 作为输入（根因分析关注的是"为什么"，而非"已经做了什么"）
- Prompt D 需要 `{confirmed_containment}` 作为输入（确保 D5 纠正措施不与 D3 重复）
- D3 是独立节点，在 Prompt A 确认后、Prompt B 启动前执行

### 2. System Prompt

```
你是一名包装供应链质量工程师，正在处理一个客诉案件的应急响应。
基于已确认的 5W2H 问题描述，制定围堵措施。

核心原则：
1. 围堵措施的优先级：隔离 > 全检 > 通知 > 记录
2. 成本意识：在确保效果的前提下选择成本最低的方案
3. 时效性：围堵是应急动作，措施必须能在 24-48 小时内启动
4. 不要与根因分析混淆——你现在不追究"为什么"，只处理"眼下怎么办"
```

### 3. 输入变量

| 变量 | 来源 | 说明 |
|------|------|------|
| `{confirmed_5w2h}` | D2 (Step 1 已确认) | 完整的 5W2H JSON |
| `{tenant_context}` | 租户配置 | 仓库位置、物流能力等 |

### 4. 输出 JSON Schema

```json
{
  "D3_containment": [
    {
      "action": "围堵措施具体描述",
      "type": "isolation | full_inspection | notification | recall | other",
      "scope": "影响范围描述（如'该批次所有在途 + 在库产品'）",
      "owner": "负责人/部门",
      "deadline": "完成期限（必须是 24-48h 内的时间点）",
      "rationale": "为什么选择此措施的简要理由",
      "effectiveness_check": "如何验证此围堵措施已生效"
    }
  ]
}
```

### 5. 关键规则

- **type 枚举**：
  - `isolation`（隔离/停用）——如停止使用该批次、移库单独存放
  - `full_inspection`（全检/加严抽检）——如在库产品、在途产品全面筛查
  - `notification`（通知相关方）——如通知客户暂停使用、通知供应商到场
  - `recall`（召回）——仅限严重安全/合规问题
  - `other`（其他）
- **action 描述要求具体操作，不用空话**：
  - ✅ "立即通知仓库停止发货该批次（批号 20260728-003），并移库至隔离区"
  - ❌ "加强管控"
- **至少包含 isolation 或 full_inspection 之一**——纯"通知"不算围堵
- **scope 必须量化**——不能写"受影响产品"，要写"批次号 XXX，数量约 5000pcs，分布在 A 仓 3000pcs + 在途 2000pcs"

### 6. 禁止行为

- ❌ 不要在这里做根因分析（那是 Prompt B 的事）
- ❌ 不要写"加强培训""更新 SOP"等永久措施（那些是 D5/D7 的事）
- ❌ 不要遗漏 isolation 或 full_inspection 类型的措施

---

## Prompt B — 5-Why 双维度根因推演

### 1. 角色设定 (System Prompt)

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
```

### 2. 用户 Prompt 模板

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
        "cannot_conclude": false
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
        "cannot_conclude": false
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
- 绝对不能停在"人员疏忽/操作失误/工人不认真"——必须推到"为什么会出现这个疏忽"，如"缺少防呆装置""SOP 未明确操作标准""培训未覆盖该工序"
- 发生根因的最终落脚点必须映射到以下包装行业 4M1E 工序维度之一：

### 包装行业 4M1E 根因追溯维度（全品类覆盖）

#### 1. 料 (Material) — 原辅材料

| 适用品类 | 典型根因方向 |
|---------|-------------|
| 纸制品 | 原纸克重波动、面纸抗张力不足、胶水黏度异常、油墨性能不符 |
| 木制品 | 木材烘干不充分（MC% 超标）、节子/死节过多、胶合板胶水等级不够 |
| 塑料/软包 | PE/PP 树脂粒料牌号混淆、热封层薄膜厚度偏差、溶剂残留超标 |
| 缓冲制品 | EPE/EPS 发泡倍率不对、原材料密度不均、防静电剂添加比例不足 |
| 标签 | 面材拉伸强度不足、底纸（格拉辛）厚薄不均、压敏胶涂布量偏差 |

#### 2. 机 (Machine) — 设备与工序参数

| 适用品类 | 典型根因方向 |
|---------|-------------|
| 纸制品 — 成型与印刷 | 瓦楞辊磨损、模切压力设定偏差、UV 固化不完全 |
| 木制品 — 木工与组装 | 自动打钉机气压不足（发钉偏斜/打穿）、板材锯切尺寸公差失控 |
| 塑料/软包 — 塑胶与吹膜 | 吹膜机风环冷却不均（壁厚偏差）、注塑机模温/压力不足、热封刀温度/时间/压力设置不当 |
| 标签/缓冲 — 模切与发泡 | 发泡机模具温度异常、标签模切刀深度压穿底纸（导致拉断） |

#### 3. 法 (Method) — 工艺规范与检验标准

| 适用品类 | 典型根因方向 |
|---------|-------------|
| 工艺设计（全品类） | 缓冲设计静垫系数（C 值）计算错误导致保护不足、托盘承重结构未做动载/静载验算 |
| 标准覆盖（全品类） | SOP 缺少木材含水率抽检要求、来料检验（IQC）未配备防静电测试仪或粘着力测试仪 |

#### 4. 环 (Environment) — 仓储与运输

| 适用品类 | 典型根因方向 |
|---------|-------------|
| 环境湿热（全品类） | 海运集装箱"集装箱雨"诱发木托盘发霉/纸箱吸湿降强、软包胶水高温回黏 |
| 物流堆码（全品类） | 超越托盘设计承重极限、拉伸膜缠绕层数不足导致散包 |

每条 Why Chain 的末层（最终结论）必须在 summary 和最后一层 answer 中明确落到上述 4M1E 之一，并指明对应品类。例如：`"边压强度不达标的根因是**料(Material)-纸制品**：该批次原纸克重从承诺的 180g 降至 165g，导致纸板整体强度下降。"` 或 `"封口漏气的根因是**机(Machine)-塑料/软包**：热封刀实际温度 135°C，低于工艺要求的 160±5°C。"`

**推演终止条件**：
- 到达系统/流程/标准层面
- 继续推演需要的信息不可得 → 标记 `cannot_conclude: true` 并附 `supplementary_request`

**证据链嵌入规则（按 Level 分级）**：

| Why Chain Level | 含义 | evidence 允许来源 |
|----------------|------|------------------|
| Level 1 | 直接原因 / 现象事实 | `D2.confirmed` 中已确认事实、supplementary_docs、rag_public、rag_private |
| Level 2~5 | 深层推论 / 机理推导 | supplementary_docs、rag_public、rag_private（**禁止**引用 email / image） |

**分级设计逻辑**：
- Level 1 回答"缺陷现场发生了什么"——这是 Step 1 已经确认的事实层面，可以与 5W2H 中的已确认数据做交叉引用。例如："Level 1 答案：边压强度实测值 3.2 kN/m，低于标准 4.5 kN/m → evidence 引用 {supplementary_docs.COATestReport}"
- Level 2+ 回答"为什么会出现这个事实"——此时推理已脱离原始报料，必须基于补充检测数据和 RAG 行业知识，禁止循环引用"因为原始图片显示塌箱所以塌箱"
- 即使 Level 1 使用 D2 事实引用，Level 2+ 仍需独立的 RAG/补充资料支撑，避免推理链在第一层就切断

- 每个 why_chain step 的 evidence 数组不能为空
- 引用 RAG 文档时，必须填写 `similarity_score`

### 置信度规则（同 Prompt A）

| 级别 | 含义 | 在此 Prompt 中的触发条件 |
|------|------|------------------------|
| confirmed | 直接证据 | 补充资料中有明确的检测数据支持 |
| inferred | 组合推理 | 多条间接证据 + RAG 行业知识支持 |
| speculative | 推测 | 无直接检测数据，基于行业经验和案例推断 |

**speculative 联动规则（区分「阻断」与「假设分支」）**：

当某一步的 confidence 为 speculative 时，按两种场景处理：

**场景 A — 硬阻断（Block）**：当 speculative 步骤是 Level 1 或 Level 2（即对最根本的物理/化学/生物机制无法确定时），继续推演无意义：
1. `cannot_conclude` 自动设为 true
2. `supplementary_request` 自动生成（不能为空）
3. 该步之后的 why chain 不再继续推演
4. 前端渲染时高亮 + 触发补充资料弹窗

**场景 B — 假设分支推演（Hypothetical Branch）**：当 speculative 出现在 Level 3+，且前两步已有 confirmed/inferred 基础时，允许继续：
1. 该步 `confidence` 标注为 `speculative`
2. `cannot_conclude` 仍设为 true（标注不确定性）
3. `supplementary_request` 自动生成
4. **但 continue_assumption 设为 true**——后续 Level 继续推演，每个后续步骤前缀标注 `[基于 Level {N} 的推测前提，做如下假设性推演]`
5. 前端渲染时，假设分支用虚线/灰色渲染，与 confirmed 链区分

**为什么需要假设分支**：实操中绝大多数客诉的深层根因（Level 3~5）在首次分析时都是推测的。如果 Level 3 就截断，Step 3（责任判定）和 Step 4（措施生成）将完全无法拿到有效的根因上下文，整个系统退化为纯人工填写。假设分支允许 AI 给出"有条件的草案"，同时诚实标注其不确定性，让用户决定是否接受还是等待补充资料。

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

必须列出至少 2 个被排除的可能原因，证明推理的完整性：
```
"我们考虑过 X 可能性，但因为 Y 理由排除了它"
```
- 排除理由必须是可验证的事实（"抽样结果显示该批次同一供应商的其他产品未出现同类缺陷"）
- 不能是主观判断（"我们认为不太可能"）

### 禁止行为
- ❌ 不要在 Level 2+ evidence 中使用 email 或 image 类型（Level 2+ 只能来自补充资料和 RAG；Level 1 可引用 D2 已确认事实）
- ❌ 不要把 5-Why 停在"人员疏忽"
- ❌ 不要让 occurrence_cause 和 escape_cause 的结论相同（它们是两个独立维度）
- ❌ 不要在没有引用来源的情况下声称"根据行业标准..."——如果不确定标准编号，不要编造
```

### 3. 输入变量说明

| 变量 | 来源 | 说明 |
|------|------|------|
| `{confirmed_5w2h_summary}` | D2.summary_confirmed | Step 1 人工确认后的终版摘要文本 |
| `{D2.ai_5w2h.*}` | D2 各子字段 | 5W2H 结构化数据的关键字段，用于问题聚焦 |
| `{supplementary_docs}` | source_materials.supplementary_docs | 补充资料中 status=uploaded 的文档，含 extracted_text |
| `{rag_public_docs}` | RAG 公共知识库检索结果 | 包装行业标准、GB/ISO/TAPPI 文档片段。必须附带 effective_date（生效日期）元数据，检索时过滤已废止版本 |
| `{rag_private_docs}` | RAG 企业私有库检索结果 | 历史 8D 报告片段、该客户的过往案例。必须附带 effective_date / report_date，优先召回近 3 年的案例 |

> **⚠️ RAG 相似度归一化要求**：后端在向 Prompt B 注入 RAG 检索结果时，必须将原始向量距离（欧氏距离/余弦距离/内积等）统一转换为 **0.00 ~ 1.00** 的归一化分数后再填入 `similarity_score`。若直接传入未归一化的大于 1 的原始值，LLM 可能产生困惑并输出异常分数。建议映射方式：
> - 余弦相似度（范围 -1~1）→ 线性映射至 0~1：`norm_score = (cosine + 1) / 2`
> - 欧氏距离 → `norm_score = 1 / (1 + distance)` 或 `exp(-distance)`
> - 内积/点积 → 截断 + softmax 归一化
>
> **⚠️ RAG 相似度硬截断阈值**：归一化之后，后端必须对 `similarity_score < 0.60` 的文档做硬过滤，不注入 Prompt B。阈值以下的低质量片段是纯噪声，LLM 可能"硬套"这些段落作为 Level 2+ 的推理证据，产生虚假因果关系。若无任何文档通过阈值过滤（即全部 < 0.60），则传入空数组 `[]`，强制 Prompt B 在 Level 2+ 走 `confidence: speculative` 并触发 `supplementary_request`，确保推理链的严肃性。

### 4. 输出映射到 Schema D4

```
Prompt B 输出
├── occurrence_cause     →  D4_root_cause.ai_analysis.occurrence_cause
├── escape_cause         →  D4_root_cause.ai_analysis.escape_cause
├── contributing_factors →  D4_root_cause.ai_analysis.contributing_factors
├── excluded_causes      →  D4_root_cause.ai_analysis.excluded_causes
└── rag_sources_used     →  D4_root_cause.ai_analysis.rag_sources_used

注意：responsibility_judgment 不由 Prompt B 生成，
      而是 Step 3 的责任判定专用 Prompt（下一阶段设计）。
```

---

## 模型选择建议

| Prompt | 推荐模型 | 备选 | 理由 |
|--------|---------|------|------|
| Prompt A（5W2H） | GPT-4o / Claude 3.5 Sonnet | DeepSeek-V3 | 多模态理解 + 结构化 JSON 输出，需要强模型 |
| Prompt B（5-Why） | Claude 3.5 Sonnet | GPT-4o | Claude 在推理链上的严谨性和"不愿编造"特性更适合 5-Why |
| Prompt C（责任判定） | GPT-4o-mini / DeepSeek-V3 | — | 基于已确认根因做分类判定，无需强推理，mini 模型即可胜任 |
| Vision 前置步骤 | GPT-4o-mini | Qwen-VL | 只需描述所见，不需推理，mini 模型足够 |

---

## Prompt C — 责任判定（Step 3）

### 1. 角色设定 (System Prompt)

```
你是一名包装供应链质量经理，精通 8D 报告中的责任归属判定。
你的任务是基于已确认的根本原因分析结果，给出责任归属的专业建议。

你的核心原则：
1. 你只做「建议」，不做「最终判定」——最终决策权在用户手中
2. 每个建议的判定理由必须引用根因分析中的具体证据
3. 必须给出主要建议（primary）+ 至少 2 个备选方案（alternatives）
4. 对每个备选方案标注支持该方案的证据强度，无证据的标注为「无直接证据支持」
5. 当根因涉及多方因素时，优先考虑「多方共担」方案

责任方类型定义：
- 供应商：缺陷由供应商的原辅材料、生产工艺、质量管理体系导致
- 客户方：缺陷由客户的使用方式、仓储条件、来料规格要求不合理导致
- 设计缺陷：缺陷由产品/包装设计方案本身的不合理性导致（而非执行偏差）
- 第三方(物流等)：缺陷由运输、装卸、中转仓储等第三方环节导致
- 多方共担：两个及以上责任方共同导致，需明确各自占比和依据
- 不可抗力：自然灾害、战争、突发政策变动等不可预见、不可避免的外部事件
```

### 2. 用户 Prompt 模板

```
请基于以下已确认的根因分析结果，给出责任归属的判定建议。

---

## 已确认根因分析 (Step 2 输出)

### 发生根因 (Occurrence Cause)
{occurrence_cause.summary}

5-Why 推理链：
{for each step in occurrence_cause.why_chain:}
- Level {step.level}: {step.question}
  → {step.answer}（置信度: {step.confidence}）
{end for}

### 流出根因 (Escape Cause)
{escape_cause.summary}

5-Why 推理链：
{for each step in escape_cause.why_chain:}
- Level {step.level}: {step.question}
  → {step.answer}（置信度: {step.confidence}）
{end for}

### 次要影响因素 (Contributing Factors)
{for each factor in contributing_factors:}
- {factor.factor}（{factor.confidence}）
{end for}

### 已排除原因
{for each cause in excluded_causes:}
- {cause.cause}：{cause.exclusion_reason}
{end for}

---

## 关键上下文

- 缺陷: {D2.what.defect_name}（{D2.what.defect_category}）
- 客户公司: {D2.who.customer_company}
- 严重程度: {D2.how_much.severity_level}
- 涉及产品: {tenant_context.product_categories}

---

## 输出要求

严格按照以下 JSON Schema 输出单一 JSON 对象。

```json
{
  "judgment_type": "SINGLE | JOINT",
  "primary_responsibility": "供应商 | 客户方 | 设计缺陷 | 第三方(物流等) | 不可抗力",
  "primary_rationale": "判定为主要责任方的核心理由（2-4 句），引用根因分析中的具体发现",

  "primary_evidence_summary": [
    {
      "source": "引用来源（occurrence_cause.why_chain[1].answer 等）",
      "excerpt": "证据关键句摘录",
      "links_to": "指向该证据支撑的结论"
    }
  ],

  "alternatives": [
    {
      "responsibility": "备选责任方（judgment_type=SINGLE 时列出其他四方；JOINT 时列出单方独揽方案）",
      "rationale": "判定理由或排除理由",
      "evidence_strength": "strong | moderate | weak | none",
      "evidence_summary": [
        {
          "source": "引用来源",
          "excerpt": "证据关键句摘录（无证据时填 '无直接证据支持'）"
        }
      ]
    }
  ],

  "multi_party_split": {
    "applicable": false,
    "allocation": []
  },

  "need_more_info": false,
  "info_requests": []
}
```
```

### 3. 关键规则

#### judgment_type 判定规则

| judgment_type | 含义 | 触发条件 | 后续字段 |
|--------------|------|---------|---------|
| `SINGLE` | 单方主责 | 发生根因 + 流出根因的主要责任明确指向同一方，或一方占比 > 80% | primary_responsibility 填写具体方；alternatives 列出剩余 4 种责任方作为备选 |
| `JOINT` | 多方共担 | 发生根因和流出根因指向不同责任方；或根因涉及两个及以上独立原因链 | primary_responsibility 填写争议最大的一方（作为默认推荐）；alternatives 列出"单方独揽"的全责方案（如"仅供应商全责"）；multi_party_split.applicable = true 且必须填写 allocation |

**核心设计逻辑**：`judgment_type` 是元数据标签，`primary_responsibility` 始终是"前端默认高亮推荐的那个选项"。当 JOINT 时，`primary_responsibility` 选占比最大的那方作为默认起点，用户可以在确认框中调整 allocation 百分比或切换为 SINGLE。这样前端单选确认框的交互逻辑无需为 JOINT 场景重新设计——primary 始终是初始高亮项，alternatives 始终是可选的备选。

#### alternatives 规则（按 judgment_type 区分）

**SINGLE 模式**：
- 列出所有剩余 4 种责任方类型作为备选（primary 已选的除外）
- 每个备选标注 `evidence_strength`：
  - `strong`：根因分析中有多条直接证据支持
  - `moderate`：有间接证据或部分相关
  - `weak`：仅轻微关联
  - `none`：无任何证据支持
- `evidence_strength` 为 `none` 时，rationale 应写成排除性陈述

**JOINT 模式**：
- alternatives 列出 2-3 个「单方独揽全责」的方案——即"如果不由多方共担，单独由某一方全责"的场景
- 每个 alternative 标注为何不如 JOINT 方案合理
- 示例：当 JOINT 建议"供应商 70% + 客户方 30%"时，alternatives 列举：
  - "仅供应商全责"（weak：流出根因缺失无法由供应商负责）
  - "仅客户方全责"（weak：发生根因与原纸质量直接相关）

#### 判定逻辑规则

| 情形 | judgment_type | primary | 示例 |
|------|-------------|---------|------|
| 发生根因指向原辅材料不达标 | SINGLE | 供应商 | "原纸克重从 180g 降至 165g" |
| 发生根因指向工艺参数偏差 + 供应商生产环节 | SINGLE | 供应商 | "瓦楞辊磨损导致黏合强度不足" |
| 流出根因指出客户验收标准缺项 | SINGLE | 客户方 | "客户来料检验未覆盖边压强度项目" |
| 发生根因指向设计方案不合理 | SINGLE | 设计缺陷 | "配纸方案未考虑海运高湿环境" |
| 流出根因 + 环境因素指向运输环节 | SINGLE | 第三方(物流等) | "运输堆码超出托盘承重极限" |
| 发生根因在供应商，流出根因在客户 | JOINT | 供应商（默认推荐） | allocation: 发生 70% 供方 + 流出 30% 客户 |
| 发生+流出根因分属不同方且各自独立 | JOINT | 占比最大方 | allocation 按证据强度加权分配 |
| 无明确人为因素，纯外部事件 | SINGLE | 不可抗力 | 极少使用，严格限定 |

#### primary_rationale 编写要求

必须包含三要素：
1. **归因**：明确说明为什么判给这个责任方
2. **引证**：引用根因分析中的 1-2 条关键证据
3. **排除**：简要说明为什么不是其他责任方（至少 1 条排除理由）

示例：
```
"纸箱边压强度不达标的发生根因为供应商批次原纸克重不足（165g vs 要求 180g），
该结论有供应商 COA 检测数据直接支撑。流出根因虽涉及客户方检验标准未覆盖 ECT 项目，
但发生根因是主因且占比超过 80%，故主要责任方判定为供应商。
排除客户方作为主要责任方：虽检验标准有缺项，但 ECT 检测非客户方来料检验常规项目。"
```

#### 多方共担规则

当 `judgment_type` 为 `JOINT` 时，`multi_party_split` 必须填写：

```json
"multi_party_split": {
  "applicable": true,
  "allocation": [
    {
      "party": "供应商",
      "percentage": 70,
      "reason": "发生根因：原纸克重不达标",
      "based_on": "occurrence_cause.summary"
    },
    {
      "party": "客户方",
      "percentage": 30,
      "reason": "流出根因：来料检验未覆盖 ECT",
      "based_on": "escape_cause.summary"
    }
  ]
}
```

各责任方 percentage 之和必须为 100。

> **⚠️ 百分比自检要求**：在输出 JSON 之前，请务必自行核对 `multi_party_split.allocation` 中所有 `percentage` 数值之和，必须精准等于 100。大模型在生成纯数值计算时偶发性会出现 70+35=105 或 60+30=90 等微小失误，导致下游校验失败。
>
> **后端兜底归一化**：后端在接收 Prompt C 输出 JSON 后、存入数据库前，应执行一行 Python 兜底校验代码：
> ```python
> # 自动按比例 Scale 至 100%（仅当微小偏差时修正，偏差过大需告警）
> allocations = json_output["multi_party_split"]["allocation"]
> total = sum(a["percentage"] for a in allocations)
> if total > 0 and total != 100:
>     if 90 <= total <= 110:  # 微小偏差，自动修正
>         for a in allocations:
>             a["percentage"] = round(a["percentage"] * 100 / total)
>     else:  # 严重偏差，记录告警后修正
>         log_warning(f"multi_party_split total={total}, expected 100, auto-scaled")
>         for a in allocations:
>             a["percentage"] = round(a["percentage"] * 100 / total)
> ```

#### 信息不足处理

当根因分析中存在 speculating 步骤（`cannot_conclude: true`）且影响了责任归属准确性时：

- `need_more_info` 设为 `true`
- `info_requests` 填写需要补充的信息（如"该批次纸板是否来自同一供应商的其他产线"）
- primary 仍给出当前最佳判断，但在 rationale 中标注"基于现有信息的最佳推断，补充资料后可能需要修正"

### 禁止行为
- ❌ 不要在没有证据的情况下给出 strong 证据强度
- ❌ 不要把 JOINT 当甩锅工具——只有在确实有多个独立原因链且各占显著比例时才用
- ❌ SINGLE 模式不要输出超过 4 个 alternatives（5 种责任方减 1 个 primary）；JOINT 模式 alternatives 是"单方全责方案"而非逐个责任方枚举
- ❌ 不要给出模糊的责任方名称（如"相关方"）——必须使用五种枚举值之一（供应商/客户方/设计缺陷/第三方/不可抗力）
```

### 4. 输入变量说明

| 变量 | 来源 | 说明 |
|------|------|------|
| `{occurrence_cause}` | D4.ai_analysis.occurrence_cause (已确认) | 发生根因的 summary + why_chain |
| `{escape_cause}` | D4.ai_analysis.escape_cause (已确认) | 流出根因的 summary + why_chain |
| `{contributing_factors}` | D4.ai_analysis.contributing_factors | 次要影响因素列表 |
| `{excluded_causes}` | D4.ai_analysis.excluded_causes | 已排除原因及排除理由 |
| `{D2.*}` | D2 关键字段 | 缺陷名称、类别、客户、严重程度（用于上下文） |
| `{tenant_context}` | 租户配置 | 产品类别等辅助信息 |

### 5. 输出映射到 Schema D4

```
Prompt C 输出
├── judgment_type            →  D4.responsibility_judgment.ai_suggestion.judgment_type
├── primary_responsibility   →  D4.responsibility_judgment.ai_suggestion.primary_responsibility
├── primary_rationale        →  D4.responsibility_judgment.ai_suggestion.primary_rationale
├── primary_evidence_summary →  D4.responsibility_judgment.ai_suggestion.primary_evidence_summary
├── alternatives             →  D4.responsibility_judgment.ai_suggestion.alternatives
├── multi_party_split        →  D4.responsibility_judgment.ai_suggestion.multi_party_split
├── need_more_info           →  D4.responsibility_judgment.ai_suggestion.need_more_info
└── info_requests            →  D4.responsibility_judgment.ai_suggestion.info_requests

注意：responsibility_judgment.confirmed_by_user 不由 Prompt C 生成，
      而是前端确认框交互后回填。
      前端根据 judgment_type 决定确认框形态：
      - SINGLE → 单选列表（primary 高亮 + alternatives 备选）
      - JOINT  → 百分比滑块分配 + alternatives 展示"单方全责"方案
      用户确认后写入 confirmed_by_user。
```

### 6. 前端交互说明

Prompt C 的输出是前端确认框的「数据源」。前端根据 `judgment_type` 渲染两种形态：

#### SINGLE 模式 — 单选确认框

```
┌──────────────────────────────────────────────┐
│ 🏭 责任判定 — AI 建议（判定类型：单方主责）       │
│                                              │
│  ● 供应商（推荐）← AI 建议高亮，显示 primary   │
│    基于根因分析的判定详情（primary_rationale）   │
│    证据：(显示 primary_evidence_summary)        │
│                                              │
│  ○ 客户方                                    │
│    证据强度: moderate / rationale 摘要         │
│                                              │
│  ○ 设计缺陷                                   │
│    证据强度: weak / rationale 摘要             │
│                                              │
│  ○ 第三方(物流等)                              │
│    证据强度: none / 排除说明                   │
│                                              │
│  ○ 不可抗力                                   │
│    证据强度: none / 排除说明                   │
│                                              │
│  [确认判定]  [手动输入自定义理由]               │
└──────────────────────────────────────────────┘
```

#### JOINT 模式 — 百分比分配确认框

```
┌──────────────────────────────────────────────┐
│ 🏭 责任判定 — AI 建议（判定类型：多方共担）       │
│                                              │
│  AI 建议分配方案：                             │
│  ┌────────────────────────────────────────┐  │
│  │ 供应商   ████████████████░░░░  70%     │  │
│  │ 客户方   ██████░░░░░░░░░░░░░░  30%     │  │
│  │ [拖动滑块调整百分比]                    │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  备选方案（单方全责）：                         │
│  ○ 仅供应商全责（weak：流出根因缺失无法解释）     │
│  ○ 仅客户方全责（weak：发生根因与原纸直接相关）   │
│                                              │
│  [确认分配方案]  [切换为单方判定]               │
└──────────────────────────────────────────────┘
```

- 选中 primary 的选项默认高亮（推荐标签）
- 每个备选显示 evidence_strength 标识（strong🟢 / moderate🟡 / weak🟠 / none⚪）
- JOINT 模式时 allocation 百分比可拖动调整（自动约束和为 100%）
- 用户确认后，`confirmed_by_user` 写入所选责任方/分配方案 + 最终理由，`is_confirmed` 置为 true

---

## Prompt D — D5-D8 卡片生成

### 1. 定位

Prompt D 是四步工作流的**收尾环节**。此时 Step 1-3 的全部分析结果（D2 问题描述、D4 根因 + 责任归属）都已完成确认，Prompt D 基于这些「已确认事实」生成仅存最后一轮人工审核的行动方案。

与 Prompt A/B/C 不同，Prompt D 不是"AI 推断 → 人确认"，而是**"AI 草拟方案 → 人审核修改"**。因为 D5~D8 涉及工程判断（措施可行性、资源排期、组织协调），AI 给的建议可能不完全贴合实际，需要工程师根据现场情况调整。

**核心设计原则：**
- D5（纠正措施）**必须直接对应已确认的根因**——每条措施标注针对 occurrence 还是 escape
- D6（验证方案）**必须与 D5 中的每条纠正措施一一对应**，避免"有措施无验证"或"验证了没采取的措施"
- D7（预防措施）**必须上升到系统/流程层面**，不是 D5 的简单重复
- D8（结案）**必须诚实**——信息不足时不强行结案

### 2. System Prompt

```
你是一名包装供应链质量部经理，拥有 15 年现场管理经验。
你正在为一个已完成根因分析的客诉案件制定后续行动方案。

你的核心原则：
1. 纠正措施必须直接解决已确认的根因——不能绕开根因提泛泛的方案
2. 每一条纠正措施必须有对应的验证方案——没有验证的措施等于没做
3. 预防措施必须防止同类问题在「所有类似产品/产线」上再次发生——不是仅限本案
4. 对于你不确定的排期、负责人等字段，标记为 "待定" 而不是随意编造
5. 结案判定必须基于"所有措施是否闭环"——不完整时如实标注
6. 所有方案必须符合包装行业实际——不接受"加强管理""提高意识"等空话
```

### 3. 输入变量说明

| 变量 | 来源 | 说明 |
|------|------|------|
| `{confirmed_5w2h}` | D2.problem_description.confirmed | 已确认的 5W2H 完整对象 |
| `{confirmed_occurrence_cause}` | D4.root_cause.confirmed.occurrence_cause | 已确认的发生根因（含 why_chain） |
| `{confirmed_escape_cause}` | D4.root_cause.confirmed.escape_cause | 已确认的流出根因（含 why_chain） |
| `{confirmed_responsibility}` | D4.root_cause.responsibility_judgment.confirmed_by_user | 已确认的责任归属 + 理由 |
| `{confirmed_containment}` | D3.containment_actions.confirmed | 已执行的围堵措施（用于 D5 参考——不要重复已做的事） |
| `{rag_public_docs}` | 公共知识库召回 | 同行业标准纠正/预防措施范例、GB/ISO 相关章节，必须附带 effective_date 元数据过滤已废止标准 |
| `{rag_private_docs}` | 私有知识库召回 | 历史 8D 报告中同类缺陷的有效纠正措施，必须附带 report_date，优先召回近 3 年案例 |
| `{tenant_context}` | 租户配置 | 产品类别、客户要求等辅助信息 |

> ⚠️ RAG 相似度归一化与截断：`{rag_public_docs}` 和 `{rag_private_docs}` 中的 `similarity_score` 已由后端归一化为 0.00~1.00 区间，且已过滤 similarity_score < 0.60 的低质量噪声片段，可直接使用。

### 4. 输出 JSON Schema

```json
{
  "D5_corrective": [
    {
      "action": "纠正/永久措施的具体描述",
      "target_root_cause": "此措施针对 occurrence 还是 escape 根因，引用根因原文",
      "owner": "负责人/部门",
      "deadline": "完成期限",
      "verification_method": "此项措施的验证方法",
      "rationale": "为什么选择此措施",
      "evidence_refs": ["引用的 RAG 文档 ID 或根因步骤索引"]
    }
  ],
  "D6_verification": [
    {
      "corrective_action_ref": "对应 D5 中哪条措施（用 action 文本匹配）",
      "verification_method": "具体验证方法",
      "verification_criteria": "通过标准（量化指标或判定条件）",
      "actual_result": null,
      "status": "pending",
      "evidence_refs": []
    }
  ],
  "D7_preventive": [
    {
      "action": "系统性预防措施描述",
      "scope": "流程改进 | 标准更新 | 培训 | 系统防呆 | 供应商管理 | 检测加严 | 其他",
      "target_system": "影响的体系/流程名称",
      "owner": "负责人/部门",
      "deadline": "完成期限",
      "rationale": "此项措施如何从系统层面防止同类问题再现",
      "effectiveness_metric": "衡量防再发效果的量化指标",
      "evidence_refs": []
    }
  ],
  "D8_recognition": {
    "summary": "整个 8D 过程的一句话总结（从问题发现到关闭）",
    "key_learnings": [
      "关键经验教训 1（可操作、可复用的认知）",
      "关键经验教训 2"
    ],
    "team_contributions": [
      {
        "member": "角色/人名（未知时填'待定'）",
        "contribution": "在本案中的贡献"
      }
    ],
    "closure_status": "可结案 | 需持续监控 | 建议升级"
  }
}
```

### 5. 关键规则

#### D5 — 纠正措施规则

- **每条措施必须精确对应一条已确认根因**——不是泛泛的"加强质检"，而是"在瓦楞线热板段增加在线边压检测点，每 30 分钟抽检一次，确保 ECT ≥ 4.5 kN/m"
- **不要与 D3 围堵措施重复**——如果 D3 已做了"隔离该批次产品并发紧急通知"，D5 不应再提
- **区分发生/O&E 根因处理**：
  - 发生根因 → 防止缺陷再次产生（如更换供方、校准设备参数）
  - 流出根因 → 防止缺陷再次漏检（如增加检验项目、提高抽检频率）
- **未知字段用"待定"**：owner/deadline/evidence_refs 不确定时填"待定"，不编造
- **必须拉取 RAG 建议**：如有历史同类案例的有效措施，优先引用

#### D6 — 验证规则

- **一对一映射**：每条 D5 措施至少对应一条 D6 验证记录，`corrective_action_ref` 用 D5 的 `action` 文本精确匹配
- **验证标准必须量化**：
  - ❌ "检查边压强度是否合格"
  - ✅ "连续 3 个批次边压强度 ≥ 4.5 kN/m，且 CpK ≥ 1.33"
- **status 初始为 pending**，`actual_result` 初始为 null——这些由人工在执行验证后填写
- **不需要验证围堵措施**（D3）——围堵是紧急止损，验证的是永久纠正措施

#### D7 — 预防措施规则

- **必须上升到系统层面**——不是"在这个班次加强抽检"，而是"在 ERP 系统中增加供应商批次原纸克重的必录字段，低于承诺值自动报警"
- **scope 必须选择枚举值**：流程改进 / 标准更新 / 培训 / 系统防呆 / 供应商管理 / 检测加严 / 其他
- **至少要覆盖检测加严和系统防呆两类**——如果只输出"加强培训"，说明推理深度不够
- **effectiveness_metric 必须可量化**："6 个月内同类客诉≤0 起"而非"客诉减少"

#### D8 — 结案规则

- **summary** 应包含：问题简述 → 根因 → 措施 → 验证状态，200 字以内
- **key_learnings** 必须是可被其他案例复用的认知，不是流水账：
  - ✅ "原纸克重验收标准应写入采购合同技术附则，而非仅依赖供方口头承诺"
  - ❌ "本次问题已解决"
- **closure_status 判定条件**：
  - `可结案`：所有 D5 措施完成 + D6 验证通过
  - `需持续监控`：措施已部署但验证周期较长（如需要跟踪 3 个月的交货表现）
  - `建议升级`：根因涉及系统性问题超出现有权限范围，或存在未关闭的 `cannot_conclude` 步骤

### 6. 输出映射

```
Prompt D 输出
├── D5_corrective[ ]    →  D5_corrective_actions.ai_draft[ ]
├── D6_verification[ ]  →  D6_verification.ai_draft[ ]
├── D7_preventive[ ]    →  D7_preventive_actions.ai_draft[ ]
└── D8_recognition      →  D8_recognition.ai_draft

所有 ai_draft 在 Step 4 的确认画布中展示，
用户逐张卡片审核/修改后写入对应的 confirmed 字段。
```

### 7. 禁止行为

- ❌ 不要在不知情时编造 owner 或 deadline——填"待定"
- ❌ 不要把 D3 围堵措施重复写进 D5——D5 是永久纠正措施，不是应急措施
- ❌ 不要让 D6_verification 的条目数少于 D5 的条目数
- ❌ 不要把 D7 写成 D5 的换一种说法——D7 要回答"即使本案解决了，如何防止类似案例在其他产品/产线上发生"
- ❌ 不要在 D6/D7 有"需持续监控"事项时将 closure_status 标为"可结案"

---

## LLM-as-ETL — 历史报告结构化提取

### 1. 定位

LLM-as-ETL 不是工作流 Prompt，而是 **Phase 2 的批量数据处理管线**。它负责将历史 8D 报告（可能是 Word/PDF/手写扫描件的 OCR 结果）转换为与系统 Schema 一致的 JSON 结构，最终入库为私有知识库的向量数据。

核心理念：**用便宜大模型替代传统正则/NER，按 JSON Schema 自动抓取关键字段，出错时自动重试修正。**

### 2. 管线架构

```
历史报告文件
    │
    ▼
┌─────────────────┐
│ ① 预处理         │  PDF → txt (pdfplumber/OCR)
│                  │  Word → txt (python-docx)
│                  │  识别 D1~D8 章节边界（正则匹配标题）
└────────┬────────┘
         ▼
┌─────────────────┐
│ ② 分段提取       │  每章调用一次 ETL Prompt
│   (D1→D8 逐个)  │  每段独立 LLM 调用，互不干扰
│                  │  ⚠ D3~D8 提取时必须将 D2 文本作为
│                  │    全局上下文注入 System Prompt（解决
│                  │    "因上述第2项缺陷导致..."类指代丢失）
└────────┬────────┘
         ▼
┌─────────────────┐
│ ③ JSON Schema   │  jsonschema 库校验
│    自动校验      │  不合格 → 错误信息喂回 LLM 重试（最多 3 次）
└────────┬────────┘
         ▼
┌─────────────────┐
│ ④ 拼合 + 入库   │  8 段 JSON 合并为完整 8D 对象
│                  │  metadata 用文件名推断生成
│                  │  向量化 → Milvus/Qdrant 入库
└─────────────────┘
```

### 3. System Prompt（按章节定制）

**因为是分段提取，System Prompt 分为通用部分 + 章节特定部分。**

#### 通用 System Prompt（所有章节共用前缀）

```
你是一个专业的包装行业 8D 报告数据提取引擎。
你的任务是从一段 8D 报告的原始文本中提取结构化数据。

工作原则：
1. 只提取文本中明确写到的信息——不要推断、不要补全、不要编造
2. 如果某个字段在原文中找不到对应信息，填 null 或空字符串，严禁猜测
3. 严格遵循输出的 JSON Schema 格式
4. 保留原文的专业术语和措辞——不要改写或"润色"
5. 包装行业术语优先：塌箱/爆线/糊盒/模切/ECT/瓦楞等
```

> **⚠️ D2 全局上下文注入规则**：提取 D3~D8 章节时，必须在 User Prompt 的开头注入已提取的 D2 问题描述文本作为上下文前缀。例如：
> ```
> ## 本报告的问题描述（供参照）
> {extracted_D2_problem_statement}
> 
> ---
> 
> ## 当前提取任务：D4 根因分析
> {D4_section_raw_text}
> ```
> 
> 这是因为历史 8D 报告中，D4 常出现"因上述第 2 项缺陷导致..."等跨章节指代。若只传 D4 文本给 LLM，这些指代会丢失上下文。D2 作为事实基础，是所有后续章节的必要参照。

#### D1 章节提取（团队信息）

```
你正在提取 D1 — 团队信息章节。从以下文本中提取：

输出格式：
{
  "team_members": [
    {
      "name": "姓名",
      "role": "角色（如 QA经理/工艺工程师/供应商代表）",
      "department": "部门"
    }
  ],
  "team_lead": "组长姓名",
  "champion": "发起人姓名（如有）"
}
```

#### D2 章节提取（问题描述）

```
你正在提取 D2 — 问题描述章节。从以下文本中提取：

输出格式：
{
  "problem_statement": "完整的问题描述（原文）",
  "defect_name": "缺陷名称（塌箱/色差/耐破不足等）",
  "defect_category": "缺陷类别",
  "customer": "客户名称",
  "product": "涉及产品",
  "batch_info": "批次号/日期",
  "severity": "客户投诉严重程度",
  "discovery_channel": "发现渠道（客诉/内部检验/退货等）"
}
```

#### D3 章节提取（围堵措施）

```
你正在提取 D3 — 围堵措施章节。从以下文本中提取：

输出格式：
{
  "containment_actions": [
    {
      "action": "围堵措施描述",
      "owner": "负责人",
      "deadline": "完成期限",
      "status": "completed | in_progress | pending",
      "evidence": "效果证据"
    }
  ]
}
```

#### D4 章节提取（根因分析）

```
你正在提取 D4 — 根因分析章节。从以下文本中提取：

输出格式：
{
  "root_cause_analysis": {
    "occurrence_cause": {
      "summary": "发生根因一句话总结",
      "why_chain": [
        {
          "level": 1,
          "question": "为什么产生了缺陷",
          "answer": "答案"
        }
      ]
    },
    "escape_cause": {
      "summary": "流出根因一句话总结",
      "why_chain": [
        {
          "level": 1,
          "question": "为什么没拦截住",
          "answer": "答案"
        }
      ]
    },
    "contributing_factors": ["次要因素"],
    "excluded_causes": ["已排除的原因"],
    "responsibility": "供应商 | 客户方 | 设计缺陷 | 第三方 | 多方共担 | 不可抗力"
  }
}
```

#### D5~D8 章节提取

```
你正在提取 D5~D8（后续行动章节）。从以下文本中提取：

⚠️ 重要：很多老旧 8D 报告可能没有单独的 D7（预防措施）或 D8（团队表彰）章节，而只写了"纠正措施及效果验证"。如果文本中确实不存在对应章节的内容，请将 D7 和 D8 设为 null，切勿强行编造。

输出格式：
{
  "D5_corrective_actions": [{ "action": "...", "owner": "...", "deadline": "..." }],
  "D6_verification": [{ "verification_method": "...", "status": "pending|passed|failed" }],
  "D7_preventive_actions": [{ "action": "...", "scope": "..." }] | null,
  "D8_recognition": {
    "summary": "...",
    "key_learnings": ["..."],
    "closure_status": "可结案 | 需持续监控 | 建议升级"
  } | null
}

规则：
- D7_preventive_actions：如果报告中完全没有预防措施或标准化内容 → 输出 null；如果仅有简单提及（如"加强管理"）→ 按原文提取
- D8_recognition：如果报告中完全没有团队表彰/经验总结/关闭确认 → 输出 null；如果有"小组确认 OK"等简单结束语 → closure_status 填"可结案"，其他字段为原文内容
- 不要因为历史报告缺少 D7/D8 而触发校验失败——null 是合法输出
```

### 4. 校验与重试流程

```
for each section in [D1, D2, D3, D4, D5~D8]:
    response = call_llm(section_prompt + section_text)

    for attempt in [1, 2, 3]:
        is_valid, errors = validate_json_schema(response, section_schema)

        if is_valid:
            section_results[section] = response
            break
        else:
            if attempt < 3:
                response = call_llm(
                    section_prompt +
                    "## 上一次输出校验失败，错误如下：\n" +
                    json.dumps(errors) +
                    "\n\n## 请修正后重新输出\n" +
                    section_text
                )
            else:
                # 3 次重试仍失败 → 标记为人工审核
                section_results[section] = response
                section_failures.append({
                    "section": section,
                    "errors": errors,
                    "last_output": response
                })

# 拼合
full_report = merge_sections(section_results)
# 生成 metadata（从文件名推断 create_date, tenant 等）
full_report["metadata"] = generate_metadata(filename)

# 入库
vectorize_and_store(full_report)
```

### 5. 模型选择与成本

| 模型 | 单段调用成本 | 单份报告（6 段） | 适用场景 |
|------|------------|----------------|---------|
| DeepSeek-V3 | ~¥0.002/段 | ~¥0.012 | **推荐首选**——中文好、便宜、支持长上下文 |
| Qwen3-235B | ~¥0.003/段 | ~¥0.018 | 备选，复杂报告提取精度更高 |
| GPT-4o-mini | ~¥0.005/段 | ~¥0.03 | 不推荐——中文包装术语理解不如国产模型 |

D1~D8 拆为 6 段（D5~D8 合并一段，因为历史报告中这四个章节经常混在一起写），每段约 500~2000 tokens 输入。

> **⚠️ D5~D8 段 Schema 宽容设计**：D7_preventive_actions 和 D8_recognition 在 JSON Schema 中定义为 `{"oneOf": [<完整结构>, {"type": "null"}]}`。历史报告中这两个章节缺失极为常见（很多老报告只写到 D6 纠正措施验证），null 是合法输出，jsonschema 校验器不应因此触发重试。

**批量处理估算：**
- 100 份历史报告 × 6 段 × ¥0.002 = **¥1.20**（用 DeepSeek-V3）
- 加 10% 重试损耗 → **约 ¥1.50 / 100 份报告**

### 6. 预处理规则

#### 章节边界识别

历史 8D 报告的章节标题不统一，需要模式匹配：

| 章节 | 常见标题模式 |
|------|------------|
| D1 | "D1" / "D1." / "团队组建" / "Team Establishment" / "小组" |
| D2 | "D2" / "D2." / "问题描述" / "Problem Description" / "现象描述" |
| D3 | "D3" / "D3." / "围堵措施" / "Containment" / "临时措施" / "应急措施" |
| D4 | "D4" / "D4." / "根因分析" / "Root Cause" / "原因分析" |
| D5 | "D5" / "D5." / "纠正措施" / "Corrective Action" / "永久措施" |
| D6 | "D6" / "D6." / "验证" / "Verification" / "效果确认" |
| D7 | "D7" / "D7." / "预防措施" / "Preventive Action" / "防再发" |
| D8 | "D8" / "D8." / "结案" / "Recognition" / "总结" / "表彰" |

**分段策略：** 优先按 D1~D8 标题分，如报告未明确分章节，则按关键词分段（"问题描述"→D2、"原因分析"→D4、"纠正"→D5 等）。

#### 脏数据处理

- 页眉页脚 → 正则移除（形如 "第X页/共Y页" / "文档编号:XXX" / 日期行）
- 表格 → 尽量保留行列关系，用 Markdown table 格式传给 LLM
- 手写扫描 OCR → 标注 `[OCR_UNCERTAIN: 识别内容]`，提示模型该段可能不准确

### 7. 增量更新支持

已入库的历史报告可能后续修订。ETL 管线应支持 **upsert** 模式：

- 用 `report_id` 或 `文件名 + 修订版本号` 做唯一键
- 发现已存在时，用新版本覆盖旧向量数据
- audit_log 中记录每次入库操作的 file_name + hash + timestamp

---

## 模型选型建议汇总

| Prompt | 推荐模型 | 备选 | 理由 |
|--------|---------|------|------|
| Prompt A（5W2H） | GPT-4o / Claude 3.5 Sonnet | DeepSeek-V3 | 多模态理解 + 结构化 JSON 输出，需要强模型 |
| Prompt A.5（D3 围堵） | GPT-4o-mini | DeepSeek-V3 | 基于确认事实做分类判断 + 措施枚举，无需深度推理 |
| Prompt B（5-Why） | Claude 3.5 Sonnet | GPT-4o | Claude 在推理链上的严谨性和"不愿编造"特性更适合 5-Why |
| Prompt C（责任判定） | GPT-4o | Claude 3.5 Sonnet | 责任判定偏逻辑归纳+证据权衡，GPT-4o 在因果关系判断上表现稳定 |
| Prompt D（D5-D8 卡片） | GPT-4o | Claude 3.5 Sonnet | 工程方案生成需要创造力+行业常识，GPT-4o 覆盖面更广 |
| LLM-as-ETL | DeepSeek-V3 | Qwen3-235B | 纯提取任务，不需要推理深度，便宜 + 中文好是王道 |
| Vision 前置步骤 | GPT-4o-mini | Qwen-VL | 只需描述所见，不需推理，mini 模型足够 |
