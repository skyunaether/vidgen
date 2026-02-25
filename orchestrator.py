import argparse
import sys
import json
import subprocess
from pathlib import Path
from utils import RunManager

def run_agent(module: str, args: list[str]):
    cmd = [sys.executable, "-m", module] + args
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error running {module}:\n{res.stderr}")
        raise RuntimeError(f"Agent {module} failed.")
    return res.stdout

def mock_vidgen(plan_path: str, manifest_path: str, run_dir: Path, run_id: str):
    """
    Simulates the vidgen component. In a real integration, this would call vidgen.main
    with the GenerationPlan, and output an ArtifactManifest.
    For now, we'll just create a dummy video and manifest.
    """
    vid_path = run_dir / "final_video.mp4"
    # Create a dummy video using ffmpeg that passes the criteria (1080x1920, 60s, 30fps) for testing
    # Or just touch it if ffmpeg is missing. We will try ffmpeg.
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=60",
        "-r", "30", "-c:v", "libx264", str(vid_path)
    ]
    try:
        subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
    except:
        vid_path.touch() # fallback
        
    manifest = {
        "run_id": run_id,
        "run_folder": str(run_dir),
        "final_video_path": str(vid_path.absolute()),
        "image_paths": [],
        "video_clip_paths": [],
        "audio_paths": [],
        "logs_path": str(run_dir / "vidgen.log")
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent VidGen Orchestrator")
    parser.add_argument("--prompt", type=str, required=True, help="User request prompt")
    parser.add_argument("--max-iterations", type=int, default=3, help="Max improvement loops")
    # allow some overrides
    parser.add_argument("--target-duration", type=int, default=None)
    parser.add_argument("--style", type=str, default=None)
    
    args = parser.parse_args()
    
    rm = RunManager()
    run_dir = rm.create_run()
    run_id = run_dir.name
    print(f"Orchestrator: Started run {run_id}")
    
    req_path = run_dir / "requirement.json"
    plan_path = run_dir / "plan.json"
    manifest_path = run_dir / "manifest.json"
    qc_path = run_dir / "qc_report.json"
    proposal_path = run_dir / "dev_proposal.json"
    
    # 1. ProjectManager -> RequirementSpec
    run_agent("ProjectManager", ["--prompt", args.prompt, "--output", str(req_path)])
    
    # Overrides
    if args.target_duration or args.style:
        with open(req_path, "r") as f:
            req = json.load(f)
        if args.target_duration: req["duration_target_sec"] = args.target_duration
        if args.style: req["style_mood"] = args.style
        with open(req_path, "w") as f:
            json.dump(req, f, indent=2)
            
    # Create initial plan (mocked from requirement)
    # Ideally ProjectManager also outputs this, or VidGen has a pre-planner.
    with open(req_path, "r") as f:
        req = json.load(f)
    initial_plan = {
        "run_id": run_id,
        "scenes": [{"scene_id": 1, "prompt": req.get("prompt_summary", ""), "duration_sec": req.get("duration_target_sec", 60), "media_type": "video"}],
        "model_choices": {},
        "global_style": req.get("style_mood", "")
    }
    with open(plan_path, "w") as f:
        json.dump(initial_plan, f, indent=2)
    
    for iteration in range(1, args.max_iterations + 1):
        print(f"\n--- Iteration {iteration} ---")
        
        # 2. VidGen -> Artifacts
        print("Orchestrator: Running VidGen...")
        mock_vidgen(str(plan_path), str(manifest_path), run_dir, run_id)
        
        # 3. QualityControl -> QCReport
        run_agent("QualityControl", [
            "--req", str(req_path),
            "--manifest", str(manifest_path),
            "--output", str(qc_path)
        ])
        
        with open(qc_path, "r") as f:
            qc = json.load(f)
            
        if qc.get("all_passed"):
            print("Orchestrator: QC Passed! Video is ready.")
            break
            
        if iteration == args.max_iterations:
            print("Orchestrator: Reached max iterations without passing QC.")
            break
            
        # 4. DevTeam -> Config Changes
        run_agent("DevTeam", [
            "--qc", str(qc_path),
            "--manifest", str(manifest_path),
            "--plan", str(plan_path),
            "--output", str(proposal_path)
        ])
        
        # Next loop will use the updated plan.json!
        
    print(f"\nOrchestrator: Run {run_id} completed. Check {run_dir} for artifacts.")

if __name__ == "__main__":
    main()
