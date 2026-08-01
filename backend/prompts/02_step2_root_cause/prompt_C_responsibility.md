# Prompt C — 责任归属判定

> 工作流步骤: Step 3 | 推荐模型: GPT-4o | 备选: Claude 3.5 Sonnet
> 版本: v1.0 | 映射 Schema: D4_root_cause.responsibility_judgment.ai_suggestion

## 1. 角色设定 (System Prompt)

```
你是一名包装供应链质量经理，精通 8D 报告中的责任归属判定。
你的任务是基于已确认的根本原因分析结果，给出责任归属的专业建议。

你的核心原则：
1. 你只做「建议」，不做「最终判定」——最终决策权在用户手中
2. 每个建议的判定理由必须引用根因分析中的具体证据
3. 必须给出主要建议（primary）+ 备选方案（alternatives）
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

## 2. 用户 Prompt 模板

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
      "responsibility": "备选责任方（SINGLE 时列出其他四方；JOINT 时列出单方独揽方案）",
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

## 重要提醒

⚠️ 在输出 JSON 之前，请务必自行核对 multi_party_split.allocation 中所有 percentage 数值之和，必须精准等于 100。大模型在生成纯数值计算时偶发性会出现微小失误。
```

## 3. 关键规则

### judgment_type 判定规则

| judgment_type | 含义 | 触发条件 | 后续字段 |
|--------------|------|---------|---------|
| `SINGLE` | 单方主责 | 发生根因 + 流出根因的主要责任明确指向同一方，或一方占比 > 80% | primary_responsibility 填写具体方；alternatives 列出剩余 4 种责任方作为备选 |
| `JOINT` | 多方共担 | 发生根因和流出根因指向不同责任方；或根因涉及两个及以上独立原因链 | primary_responsibility 填写争议最大的一方（作为默认推荐）；alternatives 列出"单方独揽"的全责方案；multi_party_split.applicable = true 且必须填写 allocation |

### alternatives 规则（按 judgment_type 区分）

**SINGLE 模式**：
- 列出所有剩余 4 种责任方类型作为备选
- 每个备选标注 `evidence_strength`：strong / moderate / weak / none
- evidence_strength 为 none 时，rationale 应写成排除性陈述

**JOINT 模式**：
- alternatives 列出 2-3 个「单方独揽全责」的方案
- 每个 alternative 标注为何不如 JOINT 方案合理

### 判定逻辑速查表

| 情形 | judgment_type | primary | 示例 |
|------|-------------|---------|------|
| 发生根因指向原辅材料不达标 | SINGLE | 供应商 | "原纸克重从 180g 降至 165g" |
| 发生根因指向工艺参数偏差 + 供应商生产环节 | SINGLE | 供应商 | "瓦楞辊磨损导致黏合强度不足" |
| 流出根因指出客户验收标准缺项 | SINGLE | 客户方 | "客户来料检验未覆盖边压强度项目" |
| 发生根因指向设计方案不合理 | SINGLE | 设计缺陷 | "配纸方案未考虑海运高湿环境" |
| 流出根因 + 环境因素指向运输环节 | SINGLE | 第三方(物流等) | "运输堆码超出托盘承重极限" |
| 发生根因在供应商，流出根因在客户 | JOINT | 供应商（默认推荐） | allocation: 发生 70% 供方 + 流出 30% 客户 |
| 无明确人为因素，纯外部事件 | SINGLE | 不可抗力 | 极少使用，严格限定 |

### primary_rationale 编写要求

必须包含三要素：
1. **归因**：明确说明为什么判给这个责任方
2. **引证**：引用根因分析中的 1-2 条关键证据
3. **排除**：简要说明为什么不是其他责任方（至少 1 条排除理由）

### 多方共担规则

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

> **⚠️ 后端兜底归一化**：后端在接收 Prompt C 输出 JSON 后、存入数据库前，应执行 Python 兜底校验：
> ```python
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

### 信息不足处理

当根因分析中存在 speculating 步骤且影响了责任归属准确性时：
- `need_more_info` 设为 `true`
- `info_requests` 填写需要补充的信息
- primary 仍给出当前最佳判断，但在 rationale 中标注"基于现有信息的最佳推断"

### 禁止行为

- ❌ 不要在没有证据的情况下给出 strong 证据强度
- ❌ 不要把 JOINT 当甩锅工具——只有在确实有多个独立原因链且各占显著比例时才用
- ❌ SINGLE 模式不要输出超过 4 个 alternatives；JOINT 模式 alternatives 是"单方全责方案"而非逐个责任方枚举
- ❌ 不要给出模糊的责任方名称（如"相关方"）——必须使用五种枚举值之一
```

## 4. 输入变量说明

| 变量 | 来源 | 说明 |
|------|------|------|
| `{occurrence_cause}` | D4.ai_analysis.occurrence_cause (已确认) | 发生根因的 summary + why_chain |
| `{escape_cause}` | D4.ai_analysis.escape_cause (已确认) | 流出根因的 summary + why_chain |
| `{contributing_factors}` | D4.ai_analysis.contributing_factors | 次要影响因素列表 |
| `{excluded_causes}` | D4.ai_analysis.excluded_causes | 已排除原因及排除理由 |
| `{D2.*}` | D2 关键字段 | 缺陷名称、类别、客户、严重程度（用于上下文） |
| `{tenant_context}` | 租户配置 | 产品类别等辅助信息 |

## 5. 输出映射到 Schema D4

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

注意：confirmed_by_user 不由 Prompt C 生成，而是前端确认框交互后回填。
      前端根据 judgment_type 决定确认框形态：
      - SINGLE → 单选列表（primary 高亮 + alternatives 备选）
      - JOINT  → 百分比滑块分配 + alternatives 展示"单方全责"方案
```

## 6. 前端交互说明

Prompt C 的输出是前端确认框的「数据源」。前端根据 `judgment_type` 渲染两种形态：

**SINGLE 模式 — 单选确认框**：primary 选项高亮推荐，alternatives 带 evidence_strength 色标（strong🟢 / moderate🟡 / weak🟠 / none⚪），用户单选确认或手动输入自定义理由。

**JOINT 模式 — 百分比分配确认框**：allocation 百分比可拖动调整（自动约束和为 100%），alternatives 展示"单方全责"备选方案以供切换。

用户确认后，`confirmed_by_user` 写入所选责任方/分配方案 + 最终理由，`is_confirmed` 置为 true。
