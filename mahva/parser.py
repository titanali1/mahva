"""Parse a plain-text script into a :class:`Project`.

Script format
-------------
::

    @theme sunset
    @resolution 1920x1080
    @fps 30

    # عنوان کل ویدیو

    ## صحنهٔ اول
    @image images/one.jpg
    @duration 8

    این متن روی صحنه نوشته و همزمان خوانده می‌شود.

    ## صحنهٔ دوم
    ...

Project level directives (``@key value``) may appear at the top of the file and
before the first ``##`` heading.  Anything else is scene content.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .schema import VIDEO_PRESETS, Project, Scene

HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
DIRECTIVE_RE = re.compile(r"^@\s*([A-Za-z_\-]+)\s*[:=]?\s*(.*)$")
BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.*)$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\!\?؟…؛])\s+|\n+")

_RESOLUTION_RE = re.compile(r"^(\d+)\s*[x×*]\s*(\d+)$")

PROJECT_ALIASES = {
    "resolution": "resolution",
    "size": "resolution",
    "aspect": "aspect",
    "fps": "fps",
    "theme": "theme",
    "font": "font_family",
    "font_family": "font_family",
    "family": "font_family",
    "rtl": "rtl",
    "ltr": "ltr",
    "language": "language",
    "lang": "language",
    "transition": "transition",
    "crossfade": "transition_duration",
    "transition_duration": "transition_duration",
    "kenburns": "kenburns",
    "voice": "voice",
    "voice_engine": "voice_engine",
    "engine": "voice_engine",
    "rate": "rate",
    "speed": "rate",
    "pitch": "pitch",
    "volume": "volume",
    "voice_volume": "voice_volume",
    "music": "music",
    "music_volume": "music_volume",
    "pad": "scene_pad",
    "scene_pad": "scene_pad",
    "min_scene": "min_scene",
    "max_scene": "max_scene",
    "chunk": "chunk_chars",
    "quality": "quality",
    "watermark": "watermark",
    "out": "out_name",
    "output": "out_name",
    "titles": "intro_title",
    "intro": "intro_title",
    "subtitle_band": "subtitle_band",
    "words_per_second": "words_per_second",
    "dash": "ignored",
}

SCENE_ALIASES = {
    "image": "image",
    "img": "image",
    "picture": "image",
    "photo": "image",
    "duration": "duration",
    "time": "duration",
    "layout": "layout",
    "style": "layout",
    "narration": "narration",
    "voice_text": "narration",
    "tts": "narration",
    "voice_file": "voice_file",
    "audio": "voice_file",
    "accent": "accent",
    "color": "accent",
    "theme": "theme",
    "transition": "transition",
    "kenburns": "kenburns",
    "title": "title",
    "subtitle": "subtitle",
    "body": "body",
}


def _to_bool(value: str, default: bool = True) -> bool:
    v = value.strip().lower()
    if v in ("", "1", "true", "yes", "on", "بله", "روشن"):
        return True
    if v in ("0", "false", "no", "off", "خیر", "خاموش"):
        return False
    return default


def _to_float(value: str, default: float) -> float:
    try:
        return float(str(value).strip().replace("s", ""))
    except (TypeError, ValueError):
        return default


def _to_int(value: str, default: int) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _parse_duration(value: str) -> float | None:
    """Accept ``12``, ``12s`` or ``mm:ss``."""
    v = str(value).strip().lower().replace("s", "").replace("ثانیه", "").strip()
    if ":" in v:
        parts = v.split(":")
        try:
            total = 0.0
            for p in parts:
                total = total * 60 + float(p)
            return total
        except ValueError:
            return None
    try:
        return float(v)
    except ValueError:
        return None


def _apply_project_directive(project: Project, key: str, value: str, base_dir: Path) -> bool:
    field = PROJECT_ALIASES.get(key.lower())
    if not field or field == "ignored":
        return False
    if field == "resolution" or field == "aspect":
        m = _RESOLUTION_RE.match(value.strip())
        if m:
            project.width, project.height = int(m.group(1)), int(m.group(2))
        elif value.strip() in VIDEO_PRESETS:
            project.width, project.height = VIDEO_PRESETS[value.strip()]
        else:
            for name, (w, h) in VIDEO_PRESETS.items():
                if value.strip().startswith(name):
                    project.width, project.height = w, h
                    break
        return True
    if field == "rtl":
        project.rtl = _to_bool(value)
        return True
    if field == "ltr":
        project.rtl = not _to_bool(value, default=True)
        return True
    if field == "intro_title":
        return True
    if field in ("music", "watermark"):
        setattr(project, field, str(_resolve_path(value, base_dir)) if value.strip() else None)
        return True
    if field == "image":
        return False
    if field in ("width",):
        project.width = _to_int(value, project.width)
        return True
    if field == "height":
        project.height = _to_int(value, project.height)
        return True
    if field in ("fps", "chunk_chars"):
        setattr(project, field, _to_int(value, getattr(project, field)))
        return True
    if field in ("scene_pad", "min_scene", "max_scene", "transition_duration",
                 "voice_volume", "music_volume", "words_per_second"):
        setattr(project, field, _to_float(value, getattr(project, field)))
        return True
    if field in ("subtitle_band",):
        project.subtitle_band = _to_bool(value)
        return True
    if field == "transition":
        project.transition = value.strip().lower()
        return True
    setattr(project, field, value.strip() or getattr(project, field))
    return True


def _resolve_path(value: str, base_dir: Path) -> str:
    raw = value.strip().strip('"').strip("'")
    if not raw:
        return raw
    p = Path(os.path.expanduser(raw))
    if p.is_absolute():
        return str(p)
    # relative paths are tried against the script folder first, then the cwd
    for candidate in (base_dir / p, Path.cwd() / p):
        if candidate.exists():
            return str(candidate.resolve())
    # ...and finally by file name anywhere under the script folder, so scripts
    # keep working after their images were moved or re-uploaded
    try:
        for found in base_dir.rglob(p.name):
            if found.is_file():
                return str(found.resolve())
    except OSError:
        pass
    return str((base_dir / p).resolve())


def _apply_scene_directive(scene: Scene, key: str, value: str, base_dir: Path) -> bool:
    field = SCENE_ALIASES.get(key.lower())
    if not field:
        return False
    if field == "duration":
        d = _parse_duration(value)
        if d is not None:
            scene.duration = max(0.5, d)
        return True
    if field == "image":
        scene.image = _resolve_path(value, base_dir) if value.strip() else None
        return True
    if field == "voice_file":
        scene.voice_file = _resolve_path(value, base_dir) if value.strip() else None
        return True
    if field == "narration":
        scene.narration = _merge_value(scene.narration, value)
        return True
    if field == "title":
        scene.title = _merge_value(scene.title, value)
        return True
    if field == "subtitle":
        scene.subtitle = _merge_value(scene.subtitle, value)
        return True
    if field == "body":
        scene.body = _merge_value(scene.body, value)
        return True
    if field == "accent":
        scene.accent = value.strip() or None
        return True
    if field == "theme":
        scene.theme = value.strip() or None
        return True
    if field == "transition":
        scene.transition = value.strip().lower() or None
        return True
    if field == "kenburns":
        scene.kenburns = (value.strip().lower() or "auto")
        return True
    if field == "layout":
        scene.layout = (value.strip().lower() or "auto")
        return True
    return False


def _merge_value(existing: str | None, value: str) -> str:
    value = value.strip()
    if not value:
        return existing or ""
    if not existing:
        return value
    return existing.rstrip() + " " + value


def _append_paragraph(scene: Scene, text: str, target: str = "body") -> None:
    text = text.strip()
    if not text:
        return
    if target == "body" and not scene.body and not scene.subtitle:
        # First free paragraph of a scene becomes the lead sentence (subtitle).
        scene.subtitle = text
        return
    current = getattr(scene, target, "")
    setattr(scene, target, (current.rstrip() + "\n\n" + text).strip() if current else text)


def _split_long_scene(scene: Scene, limit: int) -> list[Scene]:
    """Split an over-long scene into several readable scenes."""
    pieces: list[Scene] = []
    body = scene.body or scene.subtitle
    if not body or len(body) <= limit:
        return [scene]

    # keep the lead sentence(s) on the first card, then chunk the rest
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(body) if s.strip()]
    chunks: list[list[str]] = []
    current: list[str] = []
    size = 0
    for sentence in sentences:
        if size + len(sentence) > limit and current:
            chunks.append(current)
            current, size = [], 0
        current.append(sentence)
        size += len(sentence) + 1
    if current:
        chunks.append(current)

    if len(chunks) <= 1:
        return [scene]

    for i, chunk in enumerate(chunks):
        clone = Scene(
            title=scene.title if i == 0 else (scene.title + " (ادامه)" if scene.title else ""),
            subtitle=" ".join(chunk) if i == 0 else "",
            body="" if i == 0 else " ".join(chunk),
            image=scene.image if i == 0 else None,
            duration=scene.duration if i == 0 else None,
            narration=None,
            layout=scene.layout,
            accent=scene.accent,
            theme=scene.theme,
            transition=scene.transition,
            kenburns=scene.kenburns,
        )
        if scene.narration:
            clone.narration = " ".join(chunk)
        pieces.append(clone)
    return pieces


def parse_script(text: str, base_dir: str | os.PathLike[str] = ".", *, project: Project | None = None,
                 chunk: bool = True) -> Project:
    """Turn script text into a project (auto-splitting long scenes)."""
    base = Path(base_dir).resolve()
    project = project or Project()
    scenes: list[Scene] = []
    current: Scene | None = None
    doc_title_seen = False

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        if current.display_text() or current.image or current.voice_file or current.duration:
            scenes.append(current)
        current = None

    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("@") and not stripped.startswith("@@"):
            m = DIRECTIVE_RE.match(stripped)
            if m:
                key, value = m.group(1), m.group(2)
                if current is not None and _apply_scene_directive(current, key, value, base):
                    continue
                if _apply_project_directive(project, key, value, base):
                    continue
                # unknown directive inside a scene -> keep it as visible text? ignore
                continue

        heading = HEADING_RE.match(stripped)
        if heading:
            level, content = len(heading.group(1)), heading.group(2).strip()
            if level == 1 and not doc_title_seen and not scenes:
                project.title = content
                doc_title_seen = True
                continue
            flush()
            current = Scene(title=content, source_index=len(scenes))
            continue

        if stripped in ("---", "***", "___"):
            flush()
            current = Scene(source_index=len(scenes))
            continue

        if not stripped:
            if current is not None:
                current.body = (current.body + "\n\n") if current.body else current.body
            continue

        if current is None:
            current = Scene(source_index=len(scenes))

        bullet = BULLET_RE.match(line)
        if bullet:
            current.bullet_points.append(bullet.group(1).strip())
            continue

        _append_paragraph(current, stripped)

    flush()

    if not project.title and scenes:
        project.title = scenes[0].title or ""

    expanded: list[Scene] = []
    for scene in scenes:
        scene.body = " ".join(scene.body.split())
        scene.subtitle = " ".join(scene.subtitle.split())
        for part in (_split_long_scene(scene, project.chunk_chars) if chunk else [scene]):
            part.source_index = len(expanded)
            expanded.append(part)
    project.scenes = expanded
    return project


def parse_script_file(path: str | os.PathLike[str], **kwargs) -> Project:
    p = Path(path).expanduser().resolve()
    text = p.read_text(encoding="utf-8")
    return parse_script(text, base_dir=p.parent, **kwargs)
