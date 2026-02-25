from pydantic import BaseModel, Field
from typing import List, Optional

class QCCheck(BaseModel):
    name: str
    passed: bool
    metric_value: Optional[str] = None
    evidence: str = Field(..., description="Evidence (e.g., ffprobe json excerpt, LLM explanation)")
    remediation: Optional[str] = Field(None, description="Suggested action if failed")

class QCReport(BaseModel):
    """Produced by QualityControl, evaluates run artifacts against requirements."""
    run_id: str
    checks: List[QCCheck]
    all_passed: bool
    summary: str
