# AI 8D Report Platform (智能 8D 报告平台)

这是一个高度工程化的企业级 AI 客诉解决与 8D 报告生成平台。基于 Python FastAPI, LiteLLM 以及 Pydantic 构建。

## 🚀 极速启动与配置指南 (Windows / Mac 通用)

无论你是 Windows 还是 Mac，为了避免复杂的 Python 环境变量和依赖安装问题，我们**强烈建议使用 Docker 部署**。使用 Docker 可以实现真正的“拿来即用”。

### 前置准备 (只需一次)
1. 在电脑上下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。
2. （如果使用本地大模型）下载安装 [Ollama](https://ollama.com/) 并在终端运行 `ollama run qwen2.5:14b`（或你喜欢的模型）。

---

### 第 1 步：大模型配置 (即插即用)

你可以自由决定使用**本地私有大模型**（零成本、高隐私）还是**云端付费大模型**（免配置、高性能）。

打开项目根目录下的 `docker-compose.yml` 文件，找到 `environment` 配置区：

#### 选项 A：使用本地模型 (如 Ollama) - 默认已配置
不需要修改代码，`OLLAMA_API_BASE=http://host.docker.internal:11434` 已经帮你把 Docker 容器与宿主机上的 Ollama 桥接好了。

#### 选项 B：使用云端模型 (如 OpenAI, DeepSeek, Claude)
只需在 `docker-compose.yml` 中取消对应 API 密钥的注释，并填入你的 Key：
```yaml
environment:
  # 取消注释并填入：
  - OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxx
  - DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxx
```
*(💡 提示：LiteLLM 框架会自动识别你的 API Key，你可以在未来前端界面或后端 `llm_service.py` 中随意一键切换模型名称，无需重写任何逻辑。)*

---

### 第 2 步：一键启动项目

打开终端 (Windows 可使用 PowerShell 或 CMD)，进入项目根目录：

```bash
# 启动所有服务 (初次运行会自动下载环境)
docker-compose up --build
```

出现 `Application startup complete` 后，代表服务已经启动！

### 第 3 步：访问 API 控制台
打开浏览器，访问：
👉 **http://localhost:8000/docs**

你将看到 FastAPI 自动生成的交互式接口面板，你可以直接在网页上测试 `Step 1 (5W2H)` 等接口功能！

---

## 📂 核心文档与架构设计
如果你希望了解项目的顶层设计与阶段演进规划，请参阅：
- 设计要求与 UI 布局：`2026-07-30-09-02-41/PDR_AI_8D_Report_Platform_V2.html`
- 架构蓝图与落地历史：`docs/phases/` 目录下的设计与总结文档。
