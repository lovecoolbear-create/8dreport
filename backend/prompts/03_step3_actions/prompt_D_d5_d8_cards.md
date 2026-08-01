# Prompt D — D5-D8 卡片生成

> 工作流步骤: Step 4 | 推荐模型: GPT-4o | 备选: Claude 3.5 Sonnet
> 版本: v1.0 | 映射 Schema: D5/D6/D7/D8.ai_draft

## 1. 定位

Prompt D 是四步工作流的**收尾环节**。此时 Step 1-3 的全部分析结果（D2 问题描述、D3 围堵、D4 根因 + 责任归属）都已完成确认，Prompt D 基于这些「已确认事实」生成仅存最后一轮人工审核的行动方案。

与 Prompt A/B/C 不同，Prompt D 不是"AI 推断 → 人确认"，而是**"AI 草拟方案 → 人审核修改"**。因为 D5~D8 涉及工程判断（措施可行性、资源排期、组织协调），AI 给的建议可能不完全贴合实际，需要工程师根据现场情况调整。

**核心设计原则：**
- D5（纠正措施）**必须直接对应已确认的根因**——每条措施标注针对 occurrence 还是 escape
- D6（验证方案）**必须与 D5 中的每条纠正措施一一对应**
- D7（预防措施）**必须上升到系统/流程层面**，不是 D5 的简单重复
- D8（结案）**必须诚实**——信息不足时不强行结案

## 2. System Prompt

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

## 3. 输入变量说明

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

> ⚠️ **RAG 相似度归一化与截断**：`{rag_public_docs}` 和 `{rag_private_docs}` 中的 `similarity_score` 已由后端归一化为 0.00~1.00 区间，且已过滤 similarity_score < 0.60 的低质量噪声片段，可直接使用。

## 4. 输出 JSON Schema

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

## 5. 关键规则

### D5 — 纠正措施规则

- **每条措施必须精确对应一条已确认根因**——不是泛泛的"加强质检"，而是"在瓦楞线热板段增加在线边压检测点，每 30 分钟抽检一次，确保 ECT ≥ 4.5 kN/m"
- **不要与 D3 围堵措施重复**——D5 是永久纠正措施，不是应急措施
- **区分发生/O&E 根因处理**：
  - 发生根因 → 防止缺陷再次产生（如更换供方、校准设备参数）
  - 流出根因 → 防止缺陷再次漏检（如增加检验项目、提高抽检频率）
- **未知字段用"待定"**：owner/deadline/evidence_refs 不确定时填"待定"
- **必须拉取 RAG 建议**：如有历史同类案例的有效措施，优先引用

### D6 — 验证规则

- **一对一映射**：每条 D5 措施至少对应一条 D6 验证记录，`corrective_action_ref` 用 D5 的 `action` 文本精确匹配
- **验证标准必须量化**：
  - ❌ "检查边压强度是否合格"
  - ✅ "连续 3 个批次边压强度 ≥ 4.5 kN/m，且 CpK ≥ 1.33"
- **status 初始为 pending**，`actual_result` 初始为 null——由人工在执行验证后填写
- **不需要验证围堵措施**（D3）

### D7 — 预防措施规则

- **必须上升到系统层面**——不是"在这个班次加强抽检"，而是"在 ERP 系统中增加供应商批次原纸克重的必录字段，低于承诺值自动报警"
- **scope 必须选择枚举值**：流程改进 / 标准更新 / 培训 / 系统防呆 / 供应商管理 / 检测加严 / 其他
- **至少要覆盖检测加严和系统防呆两类**——如果只输出"加强培训"，说明推理深度不够
- **effectiveness_metric 必须可量化**："6 个月内同类客诉≤0 起"而非"客诉减少"

### D8 — 结案规则

- **summary** 应包含：问题简述 → 根因 → 措施 → 验证状态，200 字以内
- **key_learnings** 必须是可被其他案例复用的认知：
  - ✅ "原纸克重验收标准应写入采购合同技术附则，而非仅依赖供方口头承诺"
  - ❌ "本次问题已解决"
- **closure_status 判定条件**：
  - `可结案`：所有 D5 措施完成 + D6 验证通过
  - `需持续监控`：措施已部署但验证周期较长
  - `建议升级`：根因涉及系统性问题超出现有权限范围，或存在未关闭的 `cannot_conclude` 步骤

## 6. 输出映射

```
Prompt D 输出
├── D5_corrective[ ]    →  D5_corrective_actions.ai_draft[ ]
├── D6_verification[ ]  →  D6_verification.ai_draft[ ]
├── D7_preventive[ ]    →  D7_preventive_actions.ai_draft[ ]
└── D8_recognition      →  D8_recognition.ai_draft

所有 ai_draft 在 Step 4 的确认画布中展示，
用户逐张卡片审核/修改后写入对应的 confirmed 字段。
```

## 7. 禁止行为

- ❌ 不要在不知情时编造 owner 或 deadline——填"待定"
- ❌ 不要把 D3 围堵措施重复写进 D5——D5 是永久纠正措施，不是应急措施
- ❌ 不要让 D6_verification 的条目数少于 D5 的条目数
- ❌ 不要把 D7 写成 D5 的换一种说法——D7 要回答"即使本案解决了，如何防止类似案例在其他产品/产线上发生"
- ❌ 不要在 D6/D7 有"需持续监控"事项时将 closure_status 标为"可结案"
