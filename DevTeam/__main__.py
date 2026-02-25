import argparse
import sys
import json
from pathlib import Path

from schemas import QCReport, ArtifactManifest, DevChangeProposal, ConfigDiff
from utils import GitManager, get_hf_client

SYSTEM_PROMPT = """You are a DevTeam Agent. 
A video generation run failed QC checks. 
Read the QC Report and propose configuration changes to fix the issues.
We are modifying the `plan.json` (GenerationPlan).
Output MUST be valid JSON in this format:
{
  "slug": "short-branch-slug",
  "rationale": "Why these changes fix the issue.",
  "expected_impact": "What should happen next run.",
  "diffs": [
    {"key": "path.to.key", "old_value": "old", "new_value": "new", "reason": "why"}
  ]
}
No markdown wrappers.
"""

def propose_changes(report: QCReport, plan_path: str) -> dict:
    client = get_hf_client()
    
    with open(plan_path, "r") as f:
        plan_txt = f.read()
        
    user_prompt = f"QC Report:\n{report.model_dump_json(indent=2)}\n\nCurrent Plan:\n{plan_txt}"
    
    res = client.chat_completion(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt
    )
    
    content = res.strip()
    if content.startswith("```json"): content = content[7:]
    if content.endswith("```"): content = content[:-3]
    return json.loads(content)

def apply_diffs(plan_path: str, diffs: list) -> list[ConfigDiff]:
    with open(plan_path, "r") as f:
        plan = json.load(f)
        
    applied = []
    # simplified patching, expecting top-level or model_choices keys
    for d in diffs:
        key = d["key"]
        old_v = str(plan.get(key, ""))
        plan[key] = d["new_value"]
        applied.append(ConfigDiff(key=key, old_value=old_v, new_value=str(d["new_value"]), reason=d["reason"]))
        
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
        
    return applied

def main():
    parser = argparse.ArgumentParser(description="DevTeam Agent")
    parser.add_argument("--qc", type=str, required=True, help="Path to qc_report.json")
    parser.add_argument("--manifest", type=str, required=True, help="Path to manifest.json")
    parser.add_argument("--plan", type=str, required=True, help="Path to plan.json to modify")
    parser.add_argument("--output", type=str, required=True, help="Path to output dev_proposal.json")
    args = parser.parse_args()
    
    print("DevTeam: Analyzing QC Report...")
    with open(args.qc, "r") as f:
        report = QCReport(**json.load(f))
    with open(args.manifest, "r") as f:
        manifest = ArtifactManifest(**json.load(f))
        
    if report.all_passed:
        print("DevTeam: All passed. No changes needed.")
        sys.exit(0)
        
    proposal_data = propose_changes(report, args.plan)
    slug = proposal_data.get("slug", "fix-qc")
    branch_name = f"devteam/{report.run_id}/{slug}"
    
    git = GitManager()
    
    # 1. Branch
    print(f"DevTeam: Creating branch {branch_name}")
    try:
        git.create_branch(branch_name, checkout=True)
    except Exception as e:
        print(f"Warning: Git branch failed: {e}")
        
    # 2. Modify config
    print("DevTeam: Applying config diffs...")
    applied_diffs = apply_diffs(args.plan, proposal_data.get("diffs", []))
    
    # 3. Commit
    commit_sha = ""
    try:
        msg = f"DevTeam: Fix QC issues (run {report.run_id})\n\n{proposal_data.get('rationale')}"
        commit_sha = git.commit(msg, [args.plan])
    except Exception as e:
        print(f"Warning: Git commit failed: {e}")
        
    proposal = DevChangeProposal(
        run_id=report.run_id,
        branch_name=branch_name,
        commit_shas=[commit_sha] if commit_sha else [],
        changed_files=[args.plan],
        config_diffs=applied_diffs,
        rationale=proposal_data.get("rationale", "Fix QC"),
        expected_impact=proposal_data.get("expected_impact", "Should pass next run"),
        rollback_instructions=f"git checkout main && git branch -D {branch_name}"
    )
    
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(proposal.model_dump_json(indent=2))
        
    print(f"DevTeam: Finished. Proposal saved to {args.output}")

if __name__ == "__main__":
    main()
