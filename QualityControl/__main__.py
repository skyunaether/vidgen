import argparse
import sys
import json
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

def evaluate_qualitative(spec: RequirementSpec, manifest: ArtifactManifest) -> QCCheck:
    # Here we would use HF Vision if possible. For now, we simulate a prompt check
    client = get_hf_client()
    sys_prompt = "You are a Quality Control Agent. Critically assess if the video generation plan details align with the style."
    user_prompt = f"Requirements: {spec.style_mood}\nAssess if the video aligns. Output PASSED or FAILED and a short explanation."
    
    res = client.chat_completion(model="meta-llama/Meta-Llama-3-8B-Instruct", system_prompt=sys_prompt, user_prompt=user_prompt)
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
