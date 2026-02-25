from pydantic import BaseModel, Field
from typing import List, Optional

class ArtifactManifest(BaseModel):
    """Produced by VidGen, tracks all generated artifacts."""
    run_id: str
    run_folder: str
    final_video_path: Optional[str] = None
    image_paths: List[str] = Field(default_factory=list)
    video_clip_paths: List[str] = Field(default_factory=list)
    audio_paths: List[str] = Field(default_factory=list)
    logs_path: Optional[str] = None
    config_snapshot_path: Optional[str] = None
    prompt_history_path: Optional[str] = None
