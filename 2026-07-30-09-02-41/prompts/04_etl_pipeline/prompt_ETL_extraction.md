# LLM-as-ETL — 历史报告结构化提取

> Phase: Phase 2 | 推荐模型: DeepSeek-V3 | 备选: Qwen3-235B
> 版本: v1.0 | 成本: ~¥1.50 / 100 份报告（6 段 × DeepSeek-V3）

## 1. 定位

LLM-as-ETL 不是工作流 Prompt，而是 **Phase 2 的批量数据处理管线**。它负责将历史 8D 报告（Word/PDF/手写扫描 OCR）转换为与系统 Schema 一致的 JSON 结构，入库为私有知识库的向量数据。

核心理念：**用便宜大模型替代传统正则/NER，按 JSON Schema 自动抓取关键字段，出错时自动重试修正。**

## 2. 管线架构

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
│                  │    全局上下文注入 System Prompt
└────────┬────────┘
         ▼
┌─────────────────┐
│ ③ JSON Schema   │  jsonschema 库校验
│    自动校验      │  不合格 → 错误信息喂回 LLM 重试（最多 3 次）
└────────┬────────┘
         ▼
┌─────────────────┐
│ ④ 拼合 + 入库   │  6 段 JSON 合并为完整 8D 对象
│                  │  metadata 用文件名推断生成
│                  │  向量化 → Milvus/Qdrant 入库
└─────────────────┘
```

## 3. System Prompt

### 通用部分（所有章节共用前缀）

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
> 这是因为历史 8D 报告中，D4 常出现"因上述第 2 项缺陷导致..."等跨章节指代。若只传 D4 文本给 LLM，这些指代会丢失上下文。

### D1 章节提取（团队信息）

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

### D2 章节提取（问题描述）

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

### D3 章节提取（围堵措施）

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

### D4 章节提取（根因分析）

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

### D5~D8 章节提取

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

## 4. 校验与重试流程

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

> **⚠️ D5~D8 段 Schema 宽容设计**：D7_preventive_actions 和 D8_recognition 在 JSON Schema 中定义为 `{"oneOf": [<完整结构>, {"type": "null"}]}`。历史报告中这两个章节缺失极为常见，null 是合法输出，jsonschema 校验器不应因此触发重试。

## 5. 模型选择与成本

| 模型 | 单段调用成本 | 单份报告（6 段） | 适用场景 |
|------|------------|----------------|---------|
| DeepSeek-V3 | ~¥0.002/段 | ~¥0.012 | **推荐首选**——中文好、便宜、支持长上下文 |
| Qwen3-235B | ~¥0.003/段 | ~¥0.018 | 备选，复杂报告提取精度更高 |
| GPT-4o-mini | ~¥0.005/段 | ~¥0.03 | 不推荐——中文包装术语理解不如国产模型 |

D1~D8 拆为 6 段（D5~D8 合并一段，因为历史报告中这四个章节经常混在一起写），每段约 500~2000 tokens 输入。

**批量处理估算：**
- 100 份历史报告 × 6 段 × ¥0.002 = **¥1.20**（用 DeepSeek-V3）
- 加 10% 重试损耗 → **约 ¥1.50 / 100 份报告**

## 6. 预处理规则

### 章节边界识别

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

### 脏数据处理

- 页眉页脚 → 正则移除（形如 "第X页/共Y页" / "文档编号:XXX" / 日期行）
- 表格 → 尽量保留行列关系，用 Markdown table 格式传给 LLM
- 手写扫描 OCR → 标注 `[OCR_UNCERTAIN: 识别内容]`，提示模型该段可能不准确

## 7. 增量更新支持

已入库的历史报告可能后续修订。ETL 管线应支持 **upsert** 模式：

- 用 `report_id` 或 `文件名 + 修订版本号` 做唯一键
- 发现已存在时，用新版本覆盖旧向量数据
- audit_log 中记录每次入库操作的 file_name + hash + timestamp
