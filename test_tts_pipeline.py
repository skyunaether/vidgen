import asyncio
import os
import subprocess
from pathlib import Path

async def _edge_tts_to_mp3_async(text: str, output_path: Path):
    import edge_tts
    # testing without pitch/rate modifications which sometimes break the neural voices
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await communicate.save(str(output_path))

def _mp3_duration(mp3_path: Path) -> float:
    cmd = [
        "ffmpeg", "-version" # just checking if ffmpeg is accessible
    ]
    subprocess.run(cmd, capture_output=True, timeout=15)
    
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=15)
    print(f"ffprobe return code: {result.returncode}")
    print(f"ffprobe output: {result.stdout}")
    print(f"ffprobe str output: {result.stdout.strip().decode('utf-8')}")
    if result.returncode == 0:
        try:
            return float(result.stdout.strip())
        except ValueError as e:
            print(f"ValueError parsing float: {e}")
            pass
    return 0.0

async def main():
    test_file = Path("test_tts_output.mp3")
    print("1. Generating MP3...")
    await _edge_tts_to_mp3_async("This is a test to see why the audio is silent.", test_file)
    print(f"2. File created: {test_file.exists()}, size: {test_file.stat().st_size if test_file.exists() else 0} bytes")
    
    print("3. Checking duration...")
    dur = _mp3_duration(test_file)
    print(f"Duration: {dur}")
    
    if test_file.exists():
        test_file.unlink()

if __name__ == "__main__":
    asyncio.run(main())
