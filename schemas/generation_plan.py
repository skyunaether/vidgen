from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SceneSpec(BaseModel):
    scene_id: int
    prompt: str
    duration_sec: float
    media_type: str = Field(default="video", description="video or image")
    transition: Optional[str] = Field(None, description="Transition after this scene")

class GenerationPlan(BaseModel):
    """Produced by ProjectManager or VidGen pre-planner, consumed by VidGen."""
    run_id: str
    scenes: List[SceneSpec]
    model_choices: Dict[str, str] = Field(default_factory=dict, description="Model IDs for text, images, video, audio")
    global_style: str = Field(..., description="Overall style prompt to prepend")
    music_prompt: Optional[str] = Field(None, description="Prompt for music generation")
