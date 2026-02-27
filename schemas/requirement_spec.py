from pydantic import BaseModel, Field
from typing import List, Optional, Any

class AcceptanceCriteria(BaseModel):
    must_have: Any = Field(default_factory=list, description="Measurable pass/fail criteria")
    nice_to_have: Any = Field(default_factory=list, description="Desirable but not strictly required")

class RequirementSpec(BaseModel):
    """Produced by ProjectManager, structures the user intent."""
    prompt_summary: str = Field(..., description="A short summary of what the video is about")
    target_resolution: str = Field(default="1080x1920", description="Video format resolution (e.g. 1080x1920)")
    duration_target_sec: int = Field(default=60, description="Target duration in seconds")
    fps: int = Field(default=30, description="Target frames per second")
    aspect_ratio: str = Field(default="9:16", description="Aspect ratio")
    style_mood: str = Field(..., description="Visual style and aesthetic mood for the video")
    pacing: str = Field(default="Medium", description="Pacing and transition speed")
    narrative_beats: Any = Field(default_factory=list, description="Key story beats to hit")
    forbidden_content: Any = Field(default_factory=list, description="Things to strictly avoid")
    cta_overlay_rules: Optional[Any] = Field(None, description="Rules for text overlays or CTA at the end")
    audio_requirements: Any = Field(default="Background music matching the mood, balanced volume", description="Audio specs (music presence, ducking rules)")
    delivery_targets: List[str] = Field(default_factory=lambda: ["YouTube Shorts", "TikTok", "Instagram Reels"], description="Target platforms")
    acceptance_criteria: AcceptanceCriteria
