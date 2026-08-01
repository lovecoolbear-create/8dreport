# 核心 LLM 引擎实现计划 (Phase 1)

本项目即将进入第一阶段开发，构建基于 FastAPI 和 LiteLLM 的微服务后端。在正式编写代码前，请确认以下目录结构与技术细节。

## 目录结构设计

我们将在项目根目录 `/Users/blair/8Dreport` 下新建 `backend` 文件夹，避免与原有设计文档混淆。

```text
/Users/blair/8Dreport
├── 2026-07-30-09-02-41/       # 现有的文档与 Prompt 资料
└── backend/                   # 新建的后端服务
    ├── requirements.txt       # Python 依赖清单
    ├── main.py                # FastAPI 启动入口
    ├── models/                # 数据模型层 (Pydantic)
    │   ├── __init__.py
    │   └── schema.py          # 映射 8D_Report_Schema_v2.json
    ├── services/              # 业务逻辑与 LLM 交互层
    │   ├── __init__.py
    │   └── llm_service.py     # 封装 LiteLLM 与 Jinja2
    └── api/                   # API 路由层
        ├── __init__.py
        └── routes.py          # 暴露给前端的 RESTful 接口
```

## 关键技术细节

1. **依赖管理**：
   引入 `fastapi`, `uvicorn`, `pydantic`, `litellm`, `jinja2` 等核心包。
2. **LLM 封装 (LiteLLM)**：
   `llm_service.py` 将负责读取 `2026-07-30-09-02-41/prompts` 下的 Markdown 文件并进行 Jinja2 渲染，随后通过 LiteLLM 向大模型发起请求。初期我们可以默认使用 OpenAI API 格式（你可以在环境变量中灵活配置模型名和 Key）。
3. **Pydantic 验证**：
   我们会将 `8D_Report_Schema_v2.json` 转换为严谨的 Python 类，结合 LLM 的 `response_format` 特性，确保输出 100% 符合 JSON 格式。

## User Review Required

- **模型选用**：初期进行测试时，你希望默认使用哪家的大模型（例如 OpenAI 的 `gpt-4o-mini`，还是 DeepSeek、Claude）？这决定了我们需要你在本地环境配置哪个 API Key。
- **Prompt 复用**：后端的 Jinja2 渲染需要读取现有的 Markdown prompt，我计划直接让后端去读取 `../2026-07-30-09-02-41/prompts` 目录，或者将该目录整体移动/复制到 `backend/` 下。建议直接复制一份到 `backend/prompts` 方便独立部署。你同意这个处理方式吗？

如果上述计划没有问题，请点击 Proceed，我将开始编写代码，并在完成后将所有的变更 Push 到 GitHub 上！
