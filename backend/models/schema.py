from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# --- Evidence & Commons ---
class Evidence(BaseModel):
    source_id: str
    source_type: str
    source_name: str
    excerpt: str
    page_or_location: Optional[str] = None
    relevance: str

class SupplementaryChecklistItem(BaseModel):
    item: str
    reason: str
    triggered_by: str
    status: Literal["pending"] = "pending"

# --- Step 1: 5W2H Models ---
class WhatField(BaseModel):
    defect_name: str
    defect_category: str
    detailed_description: str
    evidence: List[Evidence]

class WhoField(BaseModel):
    reporter: str
    customer_company: str
    affected_department: Optional[str] = None
    evidence: List[Evidence]

class WhenField(BaseModel):
    complaint_date: str
    problem_discovery_date: Optional[str] = None
    production_date_or_batch: Optional[str] = None
    evidence: List[Evidence]

class WhereField(BaseModel):
    discovery_location: str
    production_location: Optional[str] = None
    evidence: List[Evidence]

class WhyInitialField(BaseModel):
    preliminary_hypothesis: str
    confidence: Literal["confirmed", "inferred", "speculative"]
    evidence: List[Evidence]

class HowField(BaseModel):
    detection_method: str
    quantity_affected: Optional[str] = None
    defect_rate: Optional[str] = None
    evidence: List[Evidence]

class HowMuchField(BaseModel):
    estimated_impact: Optional[str] = None
    severity_level: Literal["minor", "moderate", "major", "critical"]
    evidence: List[Evidence]

class ProblemDescription5W2H(BaseModel):
    """
    Schema for D2 Problem Description (Step 1)
    """
    what: WhatField
    who: WhoField
    when: WhenField
    where: WhereField
    why_initial: WhyInitialField
    how: HowField
    how_much: HowMuchField
    supplementary_checklist: List[SupplementaryChecklistItem]
