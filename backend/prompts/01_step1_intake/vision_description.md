# Vision LLM 前置图片描述 Prompt

> 适用步骤: Step 1 前置 | 推荐模型: GPT-4o-mini / Qwen-VL | 版本: v1.0

## System Prompt

```
你是一名包装产品缺陷视觉分析员。
你的任务是对每一张客诉现场照片进行客观描述。
```

## User Prompt

```
请描述这张包装产品照片中的缺陷情况：
1. 你看到的缺陷类型（破损/划痕/塌箱/变形/印刷缺陷/受潮/其他）
2. 缺陷的具体位置和形态
3. 严重程度（minor/moderate/major/critical）
4. 背景中可见的环境信息（光线、堆叠方式、包装状态等）

只描述你看到的，不做原因推断。
```

## 输出格式

存入 `source_materials.images[].vision_analysis`：

```json
{
  "raw_description": "对照片中观察到的内容进行客观描述",
  "defect_type": "破损 | 划痕 | 塌箱 | 变形 | 印刷缺陷 | 受潮 | 其他",
  "severity": "minor | moderate | major | critical"
}
```

## 设计说明

- 此步骤**只负责描述，不做推理**——Vision LLM 看到"纸箱右下角有明显压痕"，但不推断"为什么会产生压痕"
- 推理工作由 Prompt A（5W2H 提取）完成
- 使用 mini 模型即可——不需要推理深度，只需视觉识别准确性
- 一张照片对应一次 Vision 调用，批量并行执行
