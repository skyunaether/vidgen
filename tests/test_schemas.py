import pytest
from pydantic import ValidationError
from schemas import RequirementSpec, AcceptanceCriteria, GenerationPlan

def test_requirement_spec_valid():
    data = {
        "prompt_summary": "A test video",
        "style_mood": "dark",
        "acceptance_criteria": {
            "must_have": ["video is 60s"],
            "nice_to_have": []
        }
    }
    spec = RequirementSpec(**data)
    assert spec.duration_target_sec == 60 # default fallback
    assert spec.fps == 30
    assert spec.prompt_summary == "A test video"

def test_requirement_spec_invalid():
    with pytest.raises(ValidationError):
        # missing prompt_summary
        RequirementSpec(style_mood="dark", acceptance_criteria={"must_have": []})

def test_generation_plan():
    plan = GenerationPlan(
        run_id="test1",
        scenes=[{"scene_id":1, "prompt":"scene 1", "duration_sec": 5.0}],
        global_style="cinematic"
    )
    assert len(plan.scenes) == 1
    assert plan.scenes[0].media_type == "video"
