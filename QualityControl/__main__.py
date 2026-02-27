import argparse
import sys
import json
import subprocess
import tempfile
import os
from pathlib import Path

from schemas import RequirementSpec, ArtifactManifest, QCReport, QCCheck
from utils import get_video_info, get_hf_client

def check_video_metrics(spec: RequirementSpec, manifest: ArtifactManifest) -> list[QCCheck]:
    checks = []
    
    if not manifest.final_video_path or not Path(manifest.final_video_path).exists():
        checks.append(QCCheck(
            name="Video Existence", passed=False,
            evidence="Final video path does not exist in manifest or on disk.",
            remediation="Ensure vidgen produces the final video."
        ))
        return checks
        
    try:
        info = get_video_info(manifest.final_video_path)
    except Exception as e:
        checks.append(QCCheck(
            name="Video Probing", passed=False,
            evidence=str(e),
            remediation="Check ffmpeg/ffprobe installation or video format."
        ))
        return checks
        
    # Resolution Check
    req_w, req_h = map(int, spec.target_resolution.split('x'))
    res_pass = (info.width == req_w) and (info.height == req_h)
    checks.append(QCCheck(
        name="Resolution", passed=res_pass,
        metric_value=f"{info.width}x{info.height}",
        evidence=f"Target: {spec.target_resolution}, Actual: {info.width}x{info.height}",
        remediation="Adjust resolution config in generation plan." if not res_pass else None
    ))
    
    # Duration Check (10% tol)
    dur_pass = abs(info.duration_sec - spec.duration_target_sec) <= (spec.duration_target_sec * 0.1)
    checks.append(QCCheck(
        name="Duration", passed=bool(dur_pass),
        metric_value=f"{info.duration_sec:.2f}s",
        evidence=f"Target: {spec.duration_target_sec}s, Actual: {info.duration_sec:.2f}s",
        remediation="Adjust scene duration configs." if not dur_pass else None
    ))
    
    # FPS Check
    fps_pass = abs(info.fps - spec.fps) < 1.0
    checks.append(QCCheck(
        name="FPS", passed=bool(fps_pass),
        metric_value=f"{info.fps:.2f}",
        evidence=f"Target: {spec.fps}, Actual: {info.fps:.2f}",
        remediation="Ensure rendering sets the correct frame rate." if not fps_pass else None
    ))
    
    return checks

def extract_media_for_qc(video_path: str) -> tuple[list[str], str]:
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "audio.wav")
    
    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-q:a", "0", "-map", "a", audio_path], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                   
    if not os.path.exists(audio_path):
        audio_path = None
        
    frames = []
    try:
        info = get_video_info(video_path)
        dur = info.duration_sec
        timestamps = [dur * 0.25, dur * 0.5, dur * 0.75]
        for i, t in enumerate(timestamps):
            frame_path = os.path.join(temp_dir, f"frame_{i}.jpg")
            subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", video_path, "-frames:v", "1", "-q:v", "2", frame_path], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(frame_path):
                frames.append(frame_path)
    except Exception as e:
        print(f"Error extracting frames: {e}")
            
    return frames, audio_path

def evaluate_qualitative(spec: RequirementSpec, manifest: ArtifactManifest) -> QCCheck:
    client = get_hf_client()
    sys_prompt = "You are a multimodal Quality Control Agent. Critically assess if the video content (frames) and audio (transcription) align with the specified style and mood."
    
    frames, audio_path = [], None
    transcription = "No audio detected."
    
    if manifest.final_video_path and Path(manifest.final_video_path).exists():
        try:
            frames, audio_path = extract_media_for_qc(manifest.final_video_path)
            if audio_path:
                try:
                    transcription = client.transcribe_audio(audio_path)
                except Exception as ex:
                    transcription = f"[Audio Transcription Failed: {ex}]"
        except Exception as e:
            print(f"Warning: Failed to extract media for multimodal QC: {e}")
            
    user_prompt = f"Requirements:\nStyle/Mood: {spec.style_mood}\nAudio/Music: {spec.audio_requirements}\n\nThe video has been transcribed as follows:\n[Audio Transcription]: {transcription}\n\nBased on the visual frames provided and the transcription above, does the video align with the overall project requirements? Output PASSED or FAILED and a short explanation."
    
    try:
        if frames:
            # Use Vision model for multimodal check
            try:
                res = client.vision_completion(
                    model="meta-llama/Llama-3.2-11B-Vision-Instruct", 
                    system_prompt=sys_prompt, 
                    user_prompt=user_prompt,
                    image_paths=frames
                )
            except Exception as ve:
                print(f"Vision model failed ({ve}). Falling back to text reasoning model.")
                res = client.chat_completion(
                    model="meta-llama/Llama-3.3-70B-Instruct", 
                    system_prompt=sys_prompt, 
                    user_prompt=user_prompt
                )
        else:
            # Fallback to text reasoning model if no frames extracted
            res = client.chat_completion(
                model="meta-llama/Llama-3.3-70B-Instruct", 
                system_prompt=sys_prompt, 
                user_prompt=user_prompt
            )
    except Exception as e:
        res = f"FAILED. API Error during evaluation: {e}"

    # Cleanup temp files
    for f in frames:
        try: os.remove(f)
        except: pass
    if audio_path:
        try: os.remove(audio_path)
        except: pass

    res_upper = res.upper()
    passed = "FAILED" not in res_upper
    return QCCheck(
        name="Aesthetic Qualitative Assessment",
        passed=passed,
        evidence=res,
        remediation="Modify text prompts or global style in config." if not passed else None
    )

def main():
    parser = argparse.ArgumentParser(description="QualityControl Agent")
    parser.add_argument("--req", type=str, required=True, help="Path to requirement.json")
    parser.add_argument("--manifest", type=str, required=True, help="Path to manifest.json")
    parser.add_argument("--output", type=str, required=True, help="Path to output qc_report.json")
    args = parser.parse_args()
    
    print("QualityControl: Running checks...")
    with open(args.req, "r") as f:
        spec = RequirementSpec(**json.load(f))
    with open(args.manifest, "r") as f:
        manifest = ArtifactManifest(**json.load(f))
        
    checks = check_video_metrics(spec, manifest)
    if checks[0].name != "Video Existence" or checks[0].passed:
        # qualitative
        qual_check = evaluate_qualitative(spec, manifest)
        checks.append(qual_check)
        
    all_passed = all(c.passed for c in checks)
    
    report = QCReport(
        run_id=manifest.run_id,
        checks=checks,
        all_passed=all_passed,
        summary="All checks passed." if all_passed else "Some checks failed. Remediation needed."
    )
    
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
        
    print(f"QualityControl: Finished. All Passed: {all_passed}. Saved to {args.output}")

if __name__ == "__main__":
    main()
