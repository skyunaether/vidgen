import argparse
import sys
import json
from pathlib import Path

from schemas import RequirementSpec
from utils import get_hf_client

SYSTEM_PROMPT = """You are a video production Project Manager. 
Your job is to read user intent and convert it into a well-structured JSON corresponding to the required schema.
You MUST output ONLY valid JSON without Markdown wrappers or extra commentary.

The schema requires:
- prompt_summary: short description
- target_resolution: e.g. "1080x1920"
- duration_target_sec: e.g. 60
- fps: e.g. 30
- aspect_ratio: e.g. "9:16"
- style_mood: detailed aesthetic description
- pacing: (e.g. "Fast", "Medium", "Slow")
- narrative_beats: list of bullet points for the story
- forbidden_content: what to avoid
- cta_overlay_rules: rules for text overlays
- audio_requirements: music/voice needs
- delivery_targets: platforms
- acceptance_criteria: must_have and nice_to_have (lists)
"""

def generate_spec(prompt: str) -> RequirementSpec:
    client = get_hf_client()
    # We use a code model or an instruction tuned model for JSON structured output
    resp = client.chat_completion(
        model="meta-llama/Meta-Llama-3-8B-Instruct", # Example model, or mixtral
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"Create a video specification based on this user request:\n\n{prompt}"
    )
    
    # Clean possible markdown formatting
    content = resp.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
        
    try:
        data = json.loads(content)
        spec = RequirementSpec(**data)
        return spec
    except Exception as e:
        print(f"Error parsing LLM output: {e}\nRaw output:\n{content}")
        raise

def main():
    parser = argparse.ArgumentParser(description="ProjectManager Agent")
    parser.add_argument("--prompt", type=str, required=True, help="User request prompt")
    parser.add_argument("--output", type=str, required=True, help="Path to output requirement.json")
    
    args = parser.parse_args()
    
    print("ProjectManager: Generating requirement spec...")
    spec = generate_spec(args.prompt)
    
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(spec.model_dump_json(indent=2))
        
    print(f"ProjectManager: Finished. Saved to {args.output}")

if __name__ == "__main__":
    main()
