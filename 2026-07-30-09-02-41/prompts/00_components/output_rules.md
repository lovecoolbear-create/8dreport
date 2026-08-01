# 通用 JSON 输出与置信度规则

> 适用 Prompt: A, B, C, D, ETL | 版本: v1.0 | 日期: 2026-07-30

## 置信度标注规则

| 级别 | 含义 | 在 Prompt A 中的触发条件 | 在 Prompt B 中的触发条件 |
|------|------|------------------------|------------------------|
| **confirmed** | 有直接证据 | 邮件/照片明确显示 | 补充资料中有明确的检测数据支持 |
| **inferred** | 多条证据组合推理 | 间接证据链支持 | 多条间接证据 + RAG 行业知识支持 |
| **speculative** | 纯推测 | 无证据，基于行业经验推断 | 无直接检测数据，基于行业经验和案例推断 |

## 证据绑定规则

每个字段的 evidence 数组不能为空（至少 1 条）。如果某个字段完全没有证据支撑：

```json
{
  "preliminary_hypothesis": "该批次纸板可能在仓储阶段受潮，但缺乏直接证据",
  "confidence": "speculative",
  "evidence": []
}
```

证据统一格式：
```json
{
  "source_id": "引用 source_materials 中的 id",
  "source_type": "email | image | supplementary_doc | rag_public | rag_private",
  "source_name": "人类可读来源名称",
  "excerpt": "证据原文摘录",
  "relevance": "为什么这条证据支持本字段",
  "similarity_score": 0.92  // 仅 RAG 来源需要
}
```

## JSON 输出格式规则

1. 所有 Prompt 输出必须为**单一 JSON 对象**（可含嵌套数组/对象），可兼容 `response_format: { type: "json_object" }` 模式
2. 不要在 JSON 之外添加任何 Markdown 标题、解释或额外文本
3. 不要输出两个独立的 JSON 块
4. 如果某个字段在原文中找不到对应信息，填 null 或空字符串，严禁猜测
5. 保留原文的专业术语和措辞，不要改写或"润色"

## speculative 联动规则

当任意字段的 confidence 为 speculative 时：
1. 自动触发 supplementary_request（补充资料请求）
2. 前端渲染时高亮标注 + 触发补充资料弹窗
3. 在 Prompt B 中，Level 1/2 speculative 时阻断后续 why_chain（cannot_conclude=true）；Level 3+ speculative 时允许假设分支继续推演（continue_assumption=true，每步标注 "[基于推测前提]"）

## 禁止行为（通用）

- ❌ 不要编造不存在的证据（如 "根据 ISO 22000 标准第 5.3 条..." 除非确实在资料中出现了）
- ❌ 不要在没有证据的情况下给出确定结论
- ❌ 不要把包装行业无法识别的缺陷类型强塞给现有分类
- ❌ 不要在不知情时编造数值或人名——填"待定"
