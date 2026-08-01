import json
import asyncio
from services.llm_service import LLMService

async def test_step1():
    print("🚀 开始测试: 本地大模型 Qwen 2.5 (14B) 提取 5W2H")
    
    # 初始化我们的 LLM 服务 (默认已经配置为了 ollama/qwen2.5:14b-instruct-q4_K_M)
    service = LLMService()
    
    # 模拟一份客诉邮件数据
    mock_email = {
        "from": "客户A <qc@customera.com>",
        "to": "售后部",
        "date": "2026-07-28T14:30:00",
        "subject": "关于近期到货瓦楞纸箱严重塌箱的投诉",
        "body_text": "你们好，我们2026年7月28日收到的批次为20260728-003的瓦楞纸箱在仓库堆码时发生了严重的塌箱现象。大概有5000个箱子受影响。我们自己拿去测了一下边压强度，发现完全不达标。请尽快给出8D报告！"
    }
    
    # 模拟前置的 Vision LLM (视觉模型) 解析出来的图片结果
    mock_images = [
        {
            "file_name": "photo1.jpg",
            "vision_analysis": {
                "raw_description": "照片显示托盘底层纸箱明显压溃，箱体变形，且有吸湿变软的痕迹。",
                "defect_type": "塌箱/变形",
                "severity": "major"
            }
        }
    ]
    
    mock_tenant = {
        "company_name": "客户A",
        "product_categories": "纸箱"
    }
    
    print("⏳ 正在请求本地大模型，请稍候...\n")
    try:
        # 调用大模型
        result = service.extract_5w2h(mock_email, mock_images, mock_tenant)
        
        # 打印返回的 Pydantic 模型 (自动转换为 JSON)
        print("✅ 成功提取结构化 5W2H 结果:")
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        print("请确保在本地打开了 Ollama 并且该模型正在运行。")

if __name__ == "__main__":
    asyncio.run(test_step1())
