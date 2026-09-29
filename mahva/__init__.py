"""Mahva — build long videos from text + images with zero API cost.

Quick start::

    from mahva import parse_script, render_project
    project = parse_script(open("script.txt").read())
    result = render_project(project)
    print(result.path)
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = [
    "Project", "Scene", "parse_script", "parse_script_file",
    "RenderOptions", "RenderResult", "Renderer", "render_project",
    "CardRenderer", "render_preview", "Speaker", "estimate_duration",
    "VIDEO_PRESETS", "THEMES",
]

from .engine import RenderOptions, RenderResult, Renderer, render_project
from .parser import parse_script, parse_script_file
from .schema import VIDEO_PRESETS, Project, Scene
from .textcard import CardRenderer, render_preview
from .themes import THEMES
from .tts import Speaker, estimate_duration
