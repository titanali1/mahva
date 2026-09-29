"""Unit tests for Mahva (parser, shaping, planning, rendering)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mahva import parser, shaping, textcard  # noqa: E402
from mahva.engine import RenderOptions, Renderer  # noqa: E402
from mahva.fonts import resolve_font_path  # noqa: E402
from mahva.schema import Project  # noqa: E402
from mahva.tts import Speaker  # noqa: E402

SCRIPT = """
# ویدیوی آزمایشی

مقدمهٔ کوتاه.

## صحنهٔ یک
@duration 4
@image pics/a.jpg

متن صحنهٔ اول که یک جمله است.

- نکتهٔ نخست
- نکتهٔ دوم

## صحنهٔ دو
@layout split
@kenburns out
متن صحنهٔ دوم.
"""


def test_parse_project_metadata(tmp_path: Path) -> None:
    (tmp_path / "pics").mkdir()
    (tmp_path / "pics" / "a.jpg").write_bytes(b"\xff\xd8\xff")
    text = "@theme sunset\n@fps 25\n@resolution 1080x1920\n@voice fa-IR-DilaraNeural\n" + SCRIPT
    project = parser.parse_script(text, base_dir=tmp_path)
    assert project.title == "ویدیوی آزمایشی"
    assert project.theme == "sunset"
    assert project.fps == 25
    assert (project.width, project.height) == (1080, 1920)
    assert project.voice == "fa-IR-DilaraNeural"
    assert len(project.scenes) == 3
    first = project.scenes[1]
    assert first.title == "صحنهٔ یک"
    assert first.duration == 4
    assert first.image == str((tmp_path / "pics" / "a.jpg").resolve())
    assert first.bullet_points == ["نکتهٔ نخست", "نکتهٔ دوم"]
    assert first.subtitle == "متن صحنهٔ اول که یک جمله است."
    assert project.scenes[2].layout == "split"
    assert project.scenes[2].kenburns == "out"


def test_scene_directive_scope(tmp_path: Path) -> None:
    text = "@theme forest\n\n## الف\n@duration 2\nمتن\n\n## ب\nمتن\n"
    project = parser.parse_script(text, base_dir=tmp_path)
    assert project.theme == "forest"
    assert project.scenes[0].duration == 2
    assert project.scenes[1].duration is None


def test_long_scene_is_split(tmp_path: Path) -> None:
    sentence = "این یک جملهٔ آزمایشی است که تکرار می‌شود. "
    text = "## بخش\n" + sentence * 12
    project = parser.parse_script(text, base_dir=tmp_path)
    assert len(project.scenes) > 1
    assert all(len(s.display_text()) <= 600 for s in project.scenes)


def test_shaping_is_visual() -> None:
    shaped = shaping.shape("سلام")
    assert shaped != "سلام"                     # presentation forms applied
    assert "ﻡ" in shaped or "م" in shaped
    assert shaping.is_rtl_text("سلام دنیا")
    assert not shaping.is_rtl_text("hello world")


def test_font_resolution() -> None:
    path, index = resolve_font_path("Vazirmatn", "bold", "fa")
    assert Path(path).exists()
    assert index == 0


def test_estimate_and_speak_silent(tmp_path: Path) -> None:
    speaker = Speaker(engine="silent")
    assert not speaker.enabled
    assert speaker.synthesize("سلام", tmp_path / "a") is None


def test_card_render(tmp_path: Path) -> None:
    project = parser.parse_script(SCRIPT, base_dir=tmp_path)
    project.width, project.height = 480, 270
    for i, scene in enumerate(project.scenes):
        scene.layout_resolved = "plain"
    out = textcard.render_preview(project, project.scenes[0], 0, 3, tmp_path / "card.png")
    assert out.exists() and out.stat().st_size > 2000
    from PIL import Image
    assert Image.open(out).size == (480, 270)


@pytest.mark.slow
def test_end_to_end_render(tmp_path: Path) -> None:
    script_path = tmp_path / "s.md"
    script_path.write_text(SCRIPT, encoding="utf-8")
    (tmp_path / "pics").mkdir()
    from PIL import Image
    Image.new("RGB", (320, 200), (30, 60, 120)).save(tmp_path / "pics" / "a.jpg")

    project = parser.parse_script_file(script_path)
    project.width, project.height, project.fps = 320, 180, 12
    project.quality = "fast"
    out = tmp_path / "out.mp4"
    renderer = Renderer(project, RenderOptions(out_path=out, no_voice=True, work_dir=tmp_path / "work"))
    result = renderer.render()
    assert out.exists() and out.stat().st_size > 10_000
    assert result.duration == pytest.approx(sum(s.planned_duration for s in project.scenes)
                                            - project.transition_duration * 2, abs=0.2)
    assert result.plan["scenes"][0]["duration"] > 0
