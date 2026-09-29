"""Data model for a Mahva project.

A project is a list of *scenes*.  Every scene becomes one clip of the final
video; its duration is driven by the narration audio (or by the estimated
reading speed when voice-over is disabled).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

VIDEO_PRESETS: dict[str, tuple[int, int]] = {
    "landscape": (1920, 1080),   # YouTube, long-form
    "portrait": (1080, 1920),    # Reels / Shorts / TikTok
    "square": (1080, 1080),      # feed posts
    "portrait-4-5": (1080, 1350),
    "hd": (1280, 720),
    "uhd": (3840, 2160),
}

QUALITY_PRESETS: dict[str, dict[str, Any]] = {
    "fast": {"crf": 25, "preset": "veryfast", "audio_bitrate": "128k"},
    "balanced": {"crf": 21, "preset": "medium", "audio_bitrate": "160k"},
    "high": {"crf": 18, "preset": "slow", "audio_bitrate": "192k"},
}

TRANSITIONS = [
    "fade", "fadeblack", "fadewhite", "slideleft", "slideright", "slideup",
    "slidedown", "wipeleft", "wiperight", "smoothleft", "circleopen",
    "circleclose", "dissolve", "hblur", "radial",
]


@dataclass
class Scene:
    """One clip of the video."""

    title: str = ""
    subtitle: str = ""
    body: str = ""
    bullet_points: list[str] = field(default_factory=list)
    image: str | None = None          # local path (resolved against the project dir)
    duration: float | None = None     # explicit duration in seconds (overrides voice)
    narration: str | None = None      # text to speak; defaults to title+subtitle+body
    voice_file: str | None = None     # pre-rendered narration audio (skips TTS)
    layout: str = "auto"              # auto | title | overlay | split | plain
    accent: str | None = None         # hex color override, e.g. "#ff8800"
    theme: str | None = None          # per-scene theme override
    transition: str | None = None     # per-scene transition override
    kenburns: str = "auto"            # auto | none | in | out | pan-right | pan-left
    source_index: int = 0

    # filled in by the planner -------------------------------------------------
    narration_file: str | None = None  # rendered voice audio (mp3/wav)
    narration_duration: float = 0.0
    planned_duration: float = 0.0
    layout_resolved: str = "plain"

    @property
    def heading(self) -> str:
        return self.title.strip()

    def spoken_text(self) -> str:
        if self.narration and self.narration.strip():
            return self.narration.strip()
        parts = [self.title.strip(), self.subtitle.strip(), self.body.strip()]
        if self.bullet_points:
            parts.append("، ".join(b.strip() for b in self.bullet_points if b.strip()))
        return " ".join(p for p in parts if p).strip()

    def display_text(self) -> str:
        return " ".join(
            p for p in (self.title.strip(), self.subtitle.strip(), self.body.strip()) if p
        ).strip()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Project:
    title: str = ""
    scenes: list[Scene] = field(default_factory=list)

    # video -------------------------------------------------------------------
    width: int = 1920
    height: int = 1080
    fps: int = 30

    # look --------------------------------------------------------------------
    theme: str = "midnight"
    font_family: str = "Vazirmatn"
    rtl: bool = True
    language: str = "fa"
    transition: str = "fade"
    transition_duration: float = 0.6
    kenburns: str = "auto"
    watermark: str | None = None
    subtitle_band: bool = False

    # voice -------------------------------------------------------------------
    voice_engine: str = "auto"        # auto | edge | sapi | say | espeak | pico | silent
    voice: str | None = None          # e.g. fa-IR-DilaraNeural / en-US-AriaNeural
    rate: str = "+0%"
    pitch: str = "+0Hz"
    volume: str = "+0%"
    voice_volume: float = 1.0
    scene_pad: float = 0.65           # silence around narration inside a scene
    min_scene: float = 3.0
    max_scene: float = 120.0
    words_per_second: float = 2.45    # used when there is no audio track
    chunk_chars: int = 420            # auto-split long scenes

    # audio bed ---------------------------------------------------------------
    music: str | None = None
    music_volume: float = 0.07
    music_fade: float = 2.5

    # output ------------------------------------------------------------------
    quality: str = "balanced"
    out_name: str = "video.mp4"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["scenes"] = [s.to_dict() for s in self.scenes]
        return d

    @property
    def total_planned_duration(self) -> float:
        return sum(s.planned_duration for s in self.scenes)

    @property
    def final_duration(self) -> float:
        xf = self.transition_duration
        n = len(self.scenes)
        if n <= 1:
            return self.total_planned_duration
        return max(0.0, self.total_planned_duration - xf * (n - 1))


def make_plan_snapshot(project: Project) -> dict[str, Any]:
    return {
        "title": project.title,
        "scenes": [
            {
                "index": i,
                "title": s.title,
                "image": s.image,
                "layout": s.layout_resolved,
                "duration": round(s.planned_duration, 2),
                "narration_duration": round(s.narration_duration, 2),
                "has_voice": bool(s.narration_file),
            }
            for i, s in enumerate(project.scenes)
        ],
        "duration": round(project.final_duration, 2),
        "width": project.width,
        "height": project.height,
        "fps": project.fps,
    }
