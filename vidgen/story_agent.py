"""Storyline Reviewer & Refiner AI agents.

Uses a two-agent loop:
  1. StoryReviewer  — scores the current storyline (1–10) with detailed feedback.
  2. StoryRefiner   — rewrites scenes to address the reviewer's suggestions.

The pipeline runs up to MAX_REFINE_ITERATIONS cycles, stopping early when the
reviewer awards a score >= APPROVAL_THRESHOLD (default 8).

Both agents use Llama-3.1-8B-Instruct via the HF Inference API (free tier).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Callable

from .config import Config
from .scriptgen import Scene

log = logging.getLogger(__name__)

REVIEWER_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
REFINER_MODEL  = "meta-llama/Llama-3.1-8B-Instruct"

APPROVAL_THRESHOLD = 8   # score >= this → approved
MAX_REFINE_ITERATIONS = 4


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StoryReview:
    score: int                  # 1–10
    opening_hook: str           # feedback on the first scene
    narrative_arc: str          # feedback on the overall arc
    emotional_journey: str      # feedback on emotional engagement
    visual_quality: str         # feedback on visual descriptions
    pacing: str                 # feedback on pacing
    suggestions: list[str]      # specific improvement suggestions
    approved: bool              # score >= APPROVAL_THRESHOLD

    @property
    def summary(self) -> str:
        lines = [
            f"Score: {self.score}/10  {'✅ APPROVED' if self.approved else '✏️  NEEDS REVISION'}",
            f"Opening hook    : {self.opening_hook}",
            f"Narrative arc   : {self.narrative_arc}",
            f"Emotional journey: {self.emotional_journey}",
            f"Visual quality  : {self.visual_quality}",
            f"Pacing          : {self.pacing}",
        ]
        if self.suggestions:
            lines.append("Suggestions:")
            for s in self.suggestions:
                lines.append(f"  • {s}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper — call HF chat completion
# ---------------------------------------------------------------------------

def _chat(
    system: str,
    user: str,
    model: str,
    token: str,
    max_tokens: int = 1200,
) -> str:
    from huggingface_hub import InferenceClient

    client = InferenceClient(token=token)
    resp = client.chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        model=model,
        max_tokens=max_tokens,
        temperature=0.4,
    )
    return resp.choices[0].message.content.strip()


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from a text response."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find JSON block in markdown code fence
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    # Find bare JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON found in response:\n{text[:500]}")


# ---------------------------------------------------------------------------
# Reviewer agent
# ---------------------------------------------------------------------------

_REVIEWER_SYSTEM = """You are an expert creative writing critic and video story consultant.
You review short-video storylines (YouTube Shorts / TikTok format, ~2 minutes).
You give honest, constructive, specific feedback.
Always respond with ONLY a valid JSON object — no markdown, no extra text."""

_REVIEWER_USER_TEMPLATE = """Review this storyline for a video about: "{prompt}"

SCENES:
{scenes_text}

Evaluate it on these criteria and respond with exactly this JSON structure:
{{
  "score": <integer 1-10>,
  "opening_hook": "<one sentence: is the first scene gripping enough?>",
  "narrative_arc": "<one sentence: does the story have a satisfying arc?>",
  "emotional_journey": "<one sentence: does it create emotional investment?>",
  "visual_quality": "<one sentence: are visual descriptions cinematic and specific?>",
  "pacing": "<one sentence: is the pacing appropriate for a 2-minute video?>",
  "suggestions": [
    "<specific actionable suggestion 1>",
    "<specific actionable suggestion 2>",
    "<specific actionable suggestion 3>"
  ]
}}

Score guide: 1-4 poor, 5-6 average, 7 good, 8 very good, 9 excellent, 10 perfect."""


def review_story(
    scenes: list[Scene],
    prompt: str,
    config: Config,
    progress_cb: Callable[[str], None] | None = None,
) -> StoryReview:
    """Ask the reviewer agent to score and critique the storyline."""
    scenes_text = "\n".join(
        f"Scene {s.index} [{s.media_type}, {s.duration}s]: {s.narration}\n  Visual: {s.visual}"
        for s in scenes
    )
    user_msg = _REVIEWER_USER_TEMPLATE.format(
        prompt=prompt,
        scenes_text=scenes_text,
    )

    if progress_cb:
        progress_cb("  🔍 Reviewer agent analysing storyline...")

    raw = _chat(_REVIEWER_SYSTEM, user_msg, REVIEWER_MODEL, config.hf_token)
    log.debug("Reviewer raw response:\n%s", raw)

    data = _extract_json(raw)

    review = StoryReview(
        score=int(data.get("score", 5)),
        opening_hook=data.get("opening_hook", ""),
        narrative_arc=data.get("narrative_arc", ""),
        emotional_journey=data.get("emotional_journey", ""),
        visual_quality=data.get("visual_quality", ""),
        pacing=data.get("pacing", ""),
        suggestions=data.get("suggestions", []),
        approved=int(data.get("score", 5)) >= APPROVAL_THRESHOLD,
    )
    return review


# ---------------------------------------------------------------------------
# Refiner agent
# ---------------------------------------------------------------------------

_REFINER_SYSTEM = """You are an expert screenwriter and video content creator.
You rewrite short-video storylines to make them more compelling, emotional, and cinematic.
Always respond with ONLY a valid JSON array of scenes — no markdown, no extra text."""

_REFINER_USER_TEMPLATE = """Rewrite this storyline for a video about: "{prompt}"

CURRENT SCENES (JSON):
{scenes_json}

REVIEWER FEEDBACK (score {score}/10):
- Opening hook    : {opening_hook}
- Narrative arc   : {narrative_arc}
- Emotional journey: {emotional_journey}
- Visual quality  : {visual_quality}
- Pacing          : {pacing}

SUGGESTIONS TO ADDRESS:
{suggestions_text}

RULES:
- Keep exactly {n_scenes} scenes in the same order
- Keep the same media_type and duration for each scene (do NOT change them)
- Improve narration to be more evocative and emotionally resonant
- Improve visual descriptions to be more cinematic and specific
- Maintain the narrative arc about: {prompt}
- Each narration should be 1-2 short punchy sentences (max 15 words)

Respond with ONLY a JSON array:
[
  {{"index": 0, "narration": "...", "visual": "...", "duration": <number>, "media_type": "..."}},
  ...
]"""


def refine_story(
    scenes: list[Scene],
    review: StoryReview,
    prompt: str,
    config: Config,
    progress_cb: Callable[[str], None] | None = None,
) -> list[Scene]:
    """Ask the refiner agent to rewrite the story based on review feedback."""
    scenes_json = json.dumps(
        [{"index": s.index, "narration": s.narration, "visual": s.visual,
          "duration": s.duration, "media_type": s.media_type}
         for s in scenes],
        indent=2,
    )
    suggestions_text = "\n".join(f"  • {s}" for s in review.suggestions) or "  • Improve overall quality"

    user_msg = _REFINER_USER_TEMPLATE.format(
        prompt=prompt,
        scenes_json=scenes_json,
        score=review.score,
        opening_hook=review.opening_hook,
        narrative_arc=review.narrative_arc,
        emotional_journey=review.emotional_journey,
        visual_quality=review.visual_quality,
        pacing=review.pacing,
        suggestions_text=suggestions_text,
        n_scenes=len(scenes),
    )

    if progress_cb:
        progress_cb("  ✍️  Refiner agent rewriting storyline...")

    raw = _chat(_REFINER_SYSTEM, user_msg, REFINER_MODEL, config.hf_token, max_tokens=1800)
    log.debug("Refiner raw response:\n%s", raw)

    # Extract JSON array
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON array in response
        arr_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if arr_match:
            try:
                data = json.loads(arr_match.group(0))
            except json.JSONDecodeError:
                log.warning("Refiner JSON parse failed, keeping original scenes")
                return scenes
        else:
            log.warning("No JSON array in refiner response, keeping original scenes")
            return scenes

    if not isinstance(data, list) or len(data) == 0:
        log.warning("Refiner returned empty/invalid list, keeping original scenes")
        return scenes

    # Rebuild Scene objects, preserving original media_type/duration if missing
    refined: list[Scene] = []
    original_by_index = {s.index: s for s in scenes}

    for item in data:
        idx = int(item.get("index", len(refined)))
        orig = original_by_index.get(idx)
        refined.append(Scene(
            index=idx,
            narration=item.get("narration", orig.narration if orig else ""),
            visual=item.get("visual", orig.visual if orig else ""),
            duration=float(item.get("duration", orig.duration if orig else 10.0)),
            media_type=item.get("media_type", orig.media_type if orig else "image"),
        ))

    # Ensure we have same number of scenes as original
    if len(refined) != len(scenes):
        log.warning("Refiner changed scene count (%d→%d), keeping original", len(scenes), len(refined))
        return scenes

    return refined


# ---------------------------------------------------------------------------
# Main review–refine loop
# ---------------------------------------------------------------------------

def review_and_refine(
    scenes: list[Scene],
    prompt: str,
    config: Config,
    progress_cb: Callable[[str], None] | None = None,
    max_iterations: int = MAX_REFINE_ITERATIONS,
) -> tuple[list[Scene], StoryReview]:
    """Run the reviewer–refiner loop until approved or max iterations reached.

    Returns the best scenes found and the final review.
    """
    cb = progress_cb or (lambda msg: None)

    best_scenes = scenes
    best_review: StoryReview | None = None

    for iteration in range(1, max_iterations + 1):
        cb(f"\n  --- Iteration {iteration}/{max_iterations} ---")

        # Reviewer
        try:
            review = review_story(best_scenes, prompt, config, cb)
        except Exception as e:
            cb(f"  ⚠ Reviewer failed: {e} — stopping review loop")
            log.warning("Reviewer failed: %s", e)
            break

        cb(review.summary)

        # Track best
        if best_review is None or review.score > best_review.score:
            best_review = review

        if review.approved:
            cb(f"\n  ✅ Story approved with score {review.score}/10!")
            best_scenes = best_scenes  # already best
            break

        if iteration == max_iterations:
            cb(f"\n  ⚠ Max iterations reached. Best score: {best_review.score}/10")
            break

        # Refiner
        try:
            refined = refine_story(best_scenes, review, prompt, config, cb)
            best_scenes = refined
        except Exception as e:
            cb(f"  ⚠ Refiner failed: {e} — stopping refinement")
            log.warning("Refiner failed: %s", e)
            break

    return best_scenes, best_review or StoryReview(
        score=0, opening_hook="", narrative_arc="", emotional_journey="",
        visual_quality="", pacing="", suggestions=[], approved=False,
    )
