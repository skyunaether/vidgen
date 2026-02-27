import subprocess
import json
from dataclasses import dataclass
from typing import Optional

@dataclass
class FFprobeInfo:
    width: int
    height: int
    duration_sec: float
    fps: float
    codec: str
    has_audio: bool
    raw_json: str

def get_video_info(video_path: str) -> FFprobeInfo:
    """Uses ffprobe to extract video information."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name,duration",
        "-of", "json",
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        if not data.get("streams"):
            raise ValueError("No video stream found.")
            
        stream = data["streams"][0]
        width = int(stream.get("width", 0))
        height = int(stream.get("height", 0))
        
        duration = stream.get("duration")
        if duration is None:
            # Fallback to container duration
            cmd_container = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path
            ]
            res_c = subprocess.run(cmd_container, capture_output=True, text=True)
            data_c = json.loads(res_c.stdout)
            duration = data_c.get("format", {}).get("duration", 0)
            
        duration = float(duration)
        
        r_fps = stream.get("r_frame_rate", "0/1")
        num, den = map(int, r_fps.split('/'))
        fps = num / den if den != 0 else 0
        
        codec = stream.get("codec_name", "")
        
        # Check audio
        cmd_audio = [
            "ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "json", video_path
        ]
        res_a = subprocess.run(cmd_audio, capture_output=True, text=True)
        data_a = json.loads(res_a.stdout)
        has_audio = len(data_a.get("streams", [])) > 0
        
        return FFprobeInfo(
            width=width,
            height=height,
            duration_sec=duration,
            fps=fps,
            codec=codec,
            has_audio=has_audio,
            raw_json=result.stdout
        )
    except Exception as e:
        raise RuntimeError(f"Failed to probe video {video_path}: {e}")
