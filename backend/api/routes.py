from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from models.schema import ProblemDescription5W2H
from services.llm_service import LLMService

router = APIRouter()
llm_service = LLMService(model_name="ollama/qwen2.5:14b-instruct-q4_K_M")

# --- Request / Response Models ---
class Step1Request(BaseModel):
    email: Dict[str, Any]
    images: List[Dict[str, Any]]
    tenant_context: Dict[str, Any]

class Step1Response(BaseModel):
    status: str
    data: ProblemDescription5W2H

@router.post("/step1/5w2h", response_model=Step1Response)
async def generate_5w2h(request: Step1Request):
    """
    处理客诉邮件和图片，生成 5W2H 结构化数据
    """
    try:
        result = llm_service.extract_5w2h(
            email_data=request.email,
            images=request.images,
            tenant_context=request.tenant_context
        )
        return Step1Response(status="success", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
