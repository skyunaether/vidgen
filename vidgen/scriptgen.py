"""Scene breakdown generator (template-based, no LLM dependency yet)."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field

TARGET_DURATION = 120  # ~2 minutes total

# ---------------------------------------------------------------------------
# Voice presets — friendly names for Edge TTS voices
# ---------------------------------------------------------------------------

# Maps lowercase preset name → (edge_tts_voice_id, rate, pitch)
VOICE_PRESETS: dict[str, tuple[str, str, str]] = {
    "documentary": ("en-US-GuyNeural",     "-8%",  "-5Hz"),
    "dramatic":    ("en-US-DavisNeural",   "-5%",  "-3Hz"),
    "female":      ("en-US-AriaNeural",    "-5%",  "+0Hz"),
    "british":     ("en-GB-RyanNeural",    "-5%",  "-3Hz"),
    "friendly":    ("en-US-JennyNeural",   "+0%",  "+0Hz"),
    "soft":        ("en-US-AriaNeural",    "-10%", "-2Hz"),
    "australian":  ("en-AU-WilliamNeural", "-5%",  "-3Hz"),
    "tony":        ("en-US-TonyNeural",    "-5%",  "-3Hz"),
}


@dataclass
class StorySettings:
    """Per-story audio settings parsed from the markdown preamble.

    Attributes:
        music_style:  Freeform description used to select music generation
                      parameters (e.g. "epic orchestral", "peaceful chinese").
        voice:        Edge TTS voice ID (e.g. "en-US-GuyNeural") or a preset
                      name from VOICE_PRESETS (e.g. "documentary", "female").
        voice_rate:   Speaking rate adjustment (e.g. "-8%", "+5%").
        voice_pitch:  Pitch adjustment (e.g. "-5Hz", "+2Hz").
    """
    music_style: str = "chinese traditional"
    voice:       str = "en-US-GuyNeural"
    voice_rate:  str = "-8%"
    voice_pitch: str = "-5Hz"


@dataclass
class Scene:
    index: int
    narration: str
    visual: str
    duration: float  # seconds
    media_type: str  # "image" or "video"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Template library – maps keywords to scene structures
# ---------------------------------------------------------------------------

_TEMPLATES: list[dict] = [
    {
        "keywords": [],  # default / catch-all
        "scenes": [
            {"narration": "Introducing: {topic}", "visual": "A stunning cinematic wide shot establishing {topic}, dramatic lighting, 8k", "duration": 8, "media_type": "image"},
            {"narration": "Let's explore what makes {topic} fascinating.", "visual": "Close-up detail shot of {topic}, macro photography, vivid colors", "duration": 10, "media_type": "image"},
            {"narration": "The origins of {topic} go back further than most realize.", "visual": "Historical artistic rendering of {topic}, oil painting style, warm tones", "duration": 12, "media_type": "image"},
            {"narration": "Here's something most people don't know about {topic}.", "visual": "Surprising perspective of {topic}, dramatic angle, cinematic", "duration": 10, "media_type": "video"},
            {"narration": "The impact of {topic} is truly remarkable.", "visual": "Infographic-style visualization showing the scale of {topic}, modern design", "duration": 12, "media_type": "image"},
            {"narration": "Experts have weighed in on {topic}.", "visual": "Professional portrait in a modern office discussing {topic}, soft lighting", "duration": 10, "media_type": "image"},
            {"narration": "In the real world, {topic} looks like this.", "visual": "Photorealistic scene showing {topic} in everyday life, natural lighting", "duration": 12, "media_type": "video"},
            {"narration": "The future of {topic} is being shaped right now.", "visual": "Futuristic concept art inspired by {topic}, sci-fi aesthetic, neon accents", "duration": 12, "media_type": "image"},
            {"narration": "What can we learn from {topic}?", "visual": "Thoughtful person contemplating {topic}, golden hour, bokeh background", "duration": 10, "media_type": "image"},
            {"narration": "One thing is certain: {topic} will continue to surprise us.", "visual": "Epic cinematic finale shot of {topic}, sunset, lens flare, 8k quality", "duration": 10, "media_type": "image"},
            {"narration": "Thanks for watching! Like and subscribe for more.", "visual": "Stylish end card with subscribe button, gradient background, modern typography", "duration": 8, "media_type": "image"},
        ],
    },
    {
        "keywords": ["nature", "animal", "wildlife", "ocean", "forest", "mountain"],
        "scenes": [
            {"narration": "Welcome to the world of {topic}.", "visual": "Breathtaking aerial drone shot of {topic}, golden hour, 8k nature photography", "duration": 8, "media_type": "image"},
            {"narration": "{topic} is one of nature's greatest wonders.", "visual": "Majestic wide landscape featuring {topic}, National Geographic style", "duration": 12, "media_type": "image"},
            {"narration": "Watch closely — every detail matters.", "visual": "Extreme macro close-up of {topic}, water droplets, vivid detail", "duration": 10, "media_type": "video"},
            {"narration": "The ecosystem around {topic} is delicate and beautiful.", "visual": "Wide shot of the ecosystem around {topic}, lush vegetation, morning mist", "duration": 12, "media_type": "image"},
            {"narration": "Life thrives here in unexpected ways.", "visual": "Wildlife interacting with {topic}, action shot, sharp focus", "duration": 10, "media_type": "video"},
            {"narration": "Seasons transform the landscape completely.", "visual": "Split-season comparison of {topic}, autumn vs spring, vivid colors", "duration": 12, "media_type": "image"},
            {"narration": "Conservation efforts are critical for {topic}.", "visual": "Scientists studying {topic} in the field, documentary style", "duration": 10, "media_type": "image"},
            {"narration": "But threats remain.", "visual": "Dramatic moody shot showing environmental threat to {topic}, dark tones", "duration": 10, "media_type": "image"},
            {"narration": "There is hope for the future of {topic}.", "visual": "Hopeful sunrise over restored habitat of {topic}, warm golden light", "duration": 12, "media_type": "image"},
            {"narration": "Nature never ceases to amaze.", "visual": "Epic cinematic finale of {topic} in pristine nature, sunset, 8k", "duration": 10, "media_type": "image"},
            {"narration": "Thanks for watching! Subscribe for more nature content.", "visual": "Nature-themed end card, green tones, subscribe button overlay", "duration": 8, "media_type": "image"},
        ],
    },
    {
        "keywords": ["fly", "flying", "wing", "wings", "soar", "soaring", "flight", "sky", "airborne"],
        "scenes": [
            {"narration": "Some dreams are too powerful to stay on the ground.", "visual": "A lone man standing on a cliff at dawn, staring at birds soaring freely above, cinematic wide shot, golden hour light", "duration": 8, "media_type": "image"},
            {"narration": "For years, he had watched the birds and wondered — why not me?", "visual": "Close-up of man's eyes reflecting flying birds, bokeh sky background, emotional portrait, soft morning light", "duration": 10, "media_type": "image"},
            {"narration": "He studied every feather, every curve of a wing.", "visual": "Man sketching detailed wing blueprints by candlelight, scattered feathers and books, warm amber glow, top-down shot", "duration": 12, "media_type": "image"},
            {"narration": "Deep in his workshop, the wings began to take shape.", "visual": "Craftsman assembling giant feathered wings in a wooden workshop, tools and feathers everywhere, dramatic workshop lighting", "duration": 10, "media_type": "video"},
            {"narration": "The day of the first test had finally come.", "visual": "Man strapping on enormous handcrafted wings on a hilltop, wind blowing his hair, overcast dramatic sky, full body shot", "duration": 12, "media_type": "image"},
            {"narration": "He ran — and leapt — and for one breathless moment, he was flying.", "visual": "Man with large feathered wings outstretched soaring above green hills, dynamic motion, dramatic clouds, epic cinematic angle", "duration": 12, "media_type": "video"},
            {"narration": "The earth fell away beneath him. He was free.", "visual": "Aerial view looking down from flying man's perspective, patchwork fields and winding rivers below, awe-inspiring wide shot", "duration": 10, "media_type": "image"},
            {"narration": "Higher and higher — where no human had gone before.", "visual": "Man silhouetted against blazing sunset clouds, wings spread wide, flying above a sea of clouds, ultra-wide cinematic", "duration": 12, "media_type": "image"},
            {"narration": "From up here, the world looked impossibly beautiful.", "visual": "Breathtaking panoramic view from above the clouds, mountain peaks piercing through, golden light, 8k landscape photography", "duration": 10, "media_type": "image"},
            {"narration": "He had proved what they all said was impossible.", "visual": "Man landing gracefully on a cliff edge, wings folded, arms outstretched triumphantly, sunrise behind him, silhouette shot", "duration": 10, "media_type": "image"},
            {"narration": "If you dare to dream it — you can fly.", "visual": "Inspirational closing shot: man soaring across a full moon, wings glowing, stars scattered across the night sky, fantasy art style", "duration": 8, "media_type": "image"},
        ],
    },
    {
        "keywords": ["tech", "ai", "robot", "computer", "software", "code", "digital"],
        "scenes": [
            {"narration": "The future is here: {topic}.", "visual": "Futuristic tech visualization of {topic}, holographic display, dark background, neon blue", "duration": 8, "media_type": "image"},
            {"narration": "How did we get here?", "visual": "Retro computing history montage evolving to {topic}, timeline style", "duration": 12, "media_type": "image"},
            {"narration": "{topic} is changing everything.", "visual": "Person interacting with {topic} technology, sleek modern interface, cinematic", "duration": 10, "media_type": "video"},
            {"narration": "Under the hood, it's more complex than you think.", "visual": "Abstract data visualization of {topic} internals, flowing particles, dark theme", "duration": 12, "media_type": "image"},
            {"narration": "Real-world applications are already impressive.", "visual": "Split screen showing multiple applications of {topic}, clean modern layout", "duration": 12, "media_type": "image"},
            {"narration": "But there are concerns too.", "visual": "Dramatic noir-style shot representing ethical concerns about {topic}", "duration": 10, "media_type": "image"},
            {"narration": "Industry leaders are betting big on {topic}.", "visual": "Modern tech conference stage with {topic} presentation, packed audience", "duration": 10, "media_type": "image"},
            {"narration": "What does the next decade look like?", "visual": "Concept art of {topic} in 2035, ultra-futuristic, cyberpunk aesthetic", "duration": 12, "media_type": "video"},
            {"narration": "{topic} will define our generation.", "visual": "Inspiring shot of diverse team working on {topic}, warm collaborative atmosphere", "duration": 10, "media_type": "image"},
            {"narration": "Stay curious. The best is yet to come.", "visual": "Cinematic tech-themed finale, {topic} logo reveal, particle effects", "duration": 10, "media_type": "image"},
            {"narration": "Like and subscribe for more tech content!", "visual": "Tech-styled end card, dark theme, subscribe animation, circuit pattern", "duration": 8, "media_type": "image"},
        ],
    },
]


def _extract_topic(prompt: str) -> str:
    """Extract the main topic from a user prompt."""
    # Strip common prefixes
    cleaned = re.sub(
        r"^(make|create|generate|build|produce)\s+(a\s+)?([\w\s]*?\s+)?(video|short|clip|content)\s+(about|on|for|of)\s+",
        "",
        prompt.strip(),
        flags=re.IGNORECASE,
    )
    return cleaned.strip() or prompt.strip()


def _pick_template(prompt: str) -> list[dict]:
    """Pick best matching template based on keyword overlap."""
    lower = prompt.lower()
    best_score = 0
    best = _TEMPLATES[0]["scenes"]  # default

    for tmpl in _TEMPLATES[1:]:  # skip default
        score = sum(1 for kw in tmpl["keywords"] if kw in lower)
        if score > best_score:
            best_score = score
            best = tmpl["scenes"]

    return best


def generate_script(prompt: str) -> list[Scene]:
    """Generate a scene breakdown from a user prompt.

    Returns a list of Scene objects targeting ~2 minutes total.
    """
    topic = _extract_topic(prompt)
    template_scenes = _pick_template(prompt)

    scenes: list[Scene] = []
    total_duration = 0.0

    for i, tmpl in enumerate(template_scenes):
        dur = tmpl["duration"]
        if total_duration + dur > TARGET_DURATION + 5:
            break
        scenes.append(
            Scene(
                index=i,
                narration=tmpl["narration"].format(topic=topic),
                visual=tmpl["visual"].format(topic=topic),
                duration=dur,
                media_type=tmpl["media_type"],
            )
        )
        total_duration += dur

    # Adjust durations to hit target if needed
    if scenes and total_duration < TARGET_DURATION - 10:
        factor = TARGET_DURATION / total_duration
        for s in scenes:
            s.duration = round(s.duration * factor, 1)

    return scenes


def script_to_json(scenes: list[Scene]) -> str:
    return json.dumps([s.to_dict() for s in scenes], indent=2)


def parse_markdown_story(text: str) -> tuple[str, list[Scene], StorySettings]:
    """Parse a markdown story file into a ``(title, scenes, settings)`` triple.

    Expected format::

        # Video Title

        Music: peaceful chinese traditional
        Voice: documentary

        ## Scene 1 (8s, image)
        Narration: Some dreams are too powerful to stay on the ground.
        Visual: A lone man standing on a cliff at dawn, cinematic golden hour

        ## Scene 2 (10s)
        Narration: For years he watched the birds.
        Visual: Close-up of man's eyes reflecting flying birds
        Duration: 10
        Type: image

    Rules:
    - The first ``# Heading`` becomes the video title.
    - **Preamble settings** (lines before the first ``##``) may contain:

      - ``Music: <style>``  — freeform music style description, e.g.
        ``"epic orchestral"``, ``"peaceful chinese"``, ``"ambient"``.
      - ``Voice: <name>``  — a preset name (``documentary``, ``dramatic``,
        ``female``, ``british``, ``friendly``, ``soft``, ``australian``,
        ``tony``) *or* a raw Edge TTS voice ID (e.g. ``en-US-GuyNeural``).
      - ``Voice-Rate: <rate>``  — speaking rate override, e.g. ``-10%``.
      - ``Voice-Pitch: <pitch>`` — pitch override, e.g. ``-3Hz``.

    - Each ``## Heading`` starts a new scene.  Duration and media type can be
      embedded in the heading like ``(8s, video)`` *or* set with ``Duration:``
      and ``Type:`` fields inside the section.  Inline values override heading.
    - ``Narration:`` and ``Visual:`` are required per scene.
    - Lines outside ``##`` sections (e.g. notes, comments) are ignored.
    - If no ``##`` headings are found, the file is parsed as pipe-separated
      lines via :func:`parse_user_story` as a fallback.

    Returns:
        ``(title, scenes, settings)`` — title is the first ``#`` heading
        (or ``""``), settings hold parsed music/voice preferences.

    Raises ``ValueError`` if no valid scenes are found.
    """
    # Extract title from first # heading
    title = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            break

    # Split on ## headings
    section_re = re.compile(r"^##\s+", re.MULTILINE)
    parts = section_re.split(text)

    if len(parts) <= 1:
        # No ## headings — fall back to pipe-separated format
        return title, parse_user_story(text), StorySettings()

    # -----------------------------------------------------------------------
    # Parse settings from the preamble (parts[0] = text before first ##)
    # -----------------------------------------------------------------------
    settings = StorySettings()
    _rate_override: str | None = None
    _pitch_override: str | None = None

    # Strip HTML comments (<!-- ... -->) so template doc blocks don't interfere
    preamble = re.sub(r"<!--.*?-->", "", parts[0], flags=re.DOTALL)

    for raw in preamble.splitlines():
        line = re.sub(r"^[-*]\s+", "", raw.strip())  # strip list markers
        line = re.sub(r"\*+", "", line)               # strip bold markers
        lower = line.lower()

        if lower.startswith("music:"):
            settings.music_style = line[len("music:"):].strip()

        elif lower.startswith("voice-rate:"):
            _rate_override = line[len("voice-rate:"):].strip()

        elif lower.startswith("voice-pitch:"):
            _pitch_override = line[len("voice-pitch:"):].strip()

        elif lower.startswith("voice:"):
            val = line[len("voice:"):].strip()
            preset = VOICE_PRESETS.get(val.lower())
            if preset:
                settings.voice, settings.voice_rate, settings.voice_pitch = preset
            else:
                settings.voice = val  # treat as raw Edge TTS voice ID

    # Apply rate/pitch overrides (after Voice: so they always win)
    if _rate_override:
        settings.voice_rate = _rate_override
    if _pitch_override:
        settings.voice_pitch = _pitch_override

    scenes: list[Scene] = []

    for section in parts[1:]:  # parts[0] is the preamble before first ##
        section_lines = section.splitlines()
        heading = section_lines[0].strip() if section_lines else ""

        # Parse (duration, type) hints from heading, e.g. "Scene 2 (10s, video)"
        duration = 10.0
        media_type = "image"
        heading_meta = re.search(r"\(([^)]+)\)", heading)
        if heading_meta:
            for chunk in heading_meta.group(1).split(","):
                chunk = chunk.strip().lower()
                if chunk in ("image", "video"):
                    media_type = chunk
                elif chunk.endswith("s"):
                    try:
                        duration = float(chunk[:-1])
                    except ValueError:
                        pass
                else:
                    try:
                        duration = float(chunk)
                    except ValueError:
                        pass

        narration = ""
        visual = ""

        for line in section_lines[1:]:
            # Strip list markers and bold markdown syntax
            clean = re.sub(r"^[-*]\s+", "", line.strip())
            clean = re.sub(r"\*+", "", clean)
            lower = clean.lower()

            if lower.startswith("narration:"):
                narration = clean[len("narration:"):].strip()
            elif lower.startswith("visual:"):
                visual = clean[len("visual:"):].strip()
            elif lower.startswith("duration:"):
                try:
                    duration = float(
                        re.sub(r"[^0-9.]", "", clean[len("duration:"):].strip())
                    )
                except ValueError:
                    pass
            elif lower.startswith("type:"):
                t = clean[len("type:"):].strip().lower()
                if t in ("image", "video"):
                    media_type = t

        if narration and visual:
            scenes.append(
                Scene(
                    index=len(scenes),
                    narration=narration,
                    visual=visual,
                    duration=max(3.0, duration),
                    media_type=media_type,
                )
            )

    if not scenes:
        raise ValueError(
            "No valid scenes found in the markdown file.\n"
            "Each scene needs a '## Heading' with 'Narration:' and 'Visual:' fields."
        )

    return title, scenes, settings


def parse_user_story(text: str) -> list[Scene]:
    """Parse a user-provided story text into Scene objects.

    Format — one scene per line, pipe-separated fields::

        narration text | visual description [| duration_seconds] [| image/video]

    Rules:
    - Lines starting with ``#`` and blank lines are ignored.
    - Duration defaults to 10 s when omitted.
    - Media type defaults to ``image`` when omitted; use ``video`` to animate.
    - Field order for the optional extras doesn't matter — a plain number is
      treated as duration, and ``image``/``video`` as the media type.

    Raises ``ValueError`` if no valid scenes are found.
    """
    scenes: list[Scene] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            continue  # Need at least narration and visual

        narration = parts[0]
        visual = parts[1]
        duration = 10.0
        media_type = "image"

        for extra in parts[2:]:
            extra_low = extra.lower()
            if extra_low in ("image", "video"):
                media_type = extra_low
            else:
                try:
                    duration = float(extra)
                except ValueError:
                    pass  # Ignore unrecognised extras

        scenes.append(
            Scene(
                index=len(scenes),
                narration=narration,
                visual=visual,
                duration=max(3.0, duration),
                media_type=media_type,
            )
        )

    if not scenes:
        raise ValueError(
            "No valid scenes found.\n"
            "Use format:  narration | visual description [| seconds] [| image/video]"
        )

    return scenes
