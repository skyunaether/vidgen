from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class ConfigDiff(BaseModel):
    key: str
    old_value: str
    new_value: str
    reason: str

class DevChangeProposal(BaseModel):
    """Produced by DevTeam, records git changes and config adjustments."""
    run_id: str
    branch_name: str
    commit_shas: List[str]
    changed_files: List[str]
    config_diffs: List[ConfigDiff]
    rationale: str = Field(..., description="Link to QC report items that triggered this change")
    expected_impact: str
    rollback_instructions: str
