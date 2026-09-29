"""FastAPI web app: a Persian UI on top of the render engine.

Run it with::

    python -m mahva serve --port 8000
    # or
    uvicorn app:app --port 8000
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .engine import RenderOptions, Renderer
from .ffmpeg import Cancelled, find_ffmpeg
from .fonts import available_families
from .parser import parse_script
from .schema import QUALITY_PRESETS, TRANSITIONS, VIDEO_PRESETS, Project
from .textcard import render_preview
from .themes import theme_choices
from .tts import engine_status, voice_catalog

STATIC_DIR = Path(__file__).resolve().parent / "static"
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_WORK = Path(os.environ.get("MAHVA_HOME", ROOT_DIR / "out")) / "web"

MAX_UPLOAD_FILES = 80
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
MAX_SCRIPT_CHARS = 200_000
MAX_SCENES = 400
SAFE_NAME = re.compile(r"[^A-Za-z0-9_.\-\u0600-\u06FF ]+")

SAMPLE_SCRIPT = """# عنوان ویدیوی شما

اینجا یک پاراگراف مقدمه بنویسید؛ همین متن هم روی کارت نمایش داده می‌شود و هم خوانده می‌شود.

## بخش اول
@image my-photo.jpg

توضیح این بخش را بنویسید. هر تصویری که در پنل کنار آپلود کنید، با نامش اینجا قابل ارجاع است.

- نکتهٔ اول
- نکتهٔ دوم

## بخش دوم
@duration 10

می‌توانید مدت هر بخش را دستی هم تعیین کنید.
"""


# --------------------------------------------------------------------- jobs
@dataclass
class Job:
    id: str
    script: str
    settings: dict[str, Any]
    work_dir: Path
    status: str = "queued"          # queued | running | done | error | cancelled
    progress: float = 0.0
    step: str = "در انتظار نوبت"
    logs: list[str] = field(default_factory=list)
    output: Path | None = None
    error: str | None = None
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None
    plan: dict | None = None
    cancel_flag: bool = False

    def log(self, message: str) -> None:
        self.logs.append(message)
        if len(self.logs) > 400:
            del self.logs[:100]

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "progress": round(self.progress, 4),
            "step": self.step,
            "logs": self.logs[-60:],
            "error": self.error,
            "plan": self.plan,
            "output": None if not self.output else {
                "name": self.output.name,
                "url": f"/api/jobs/{self.id}/video",
                "size": self.output.stat().st_size if self.output.exists() else 0,
            },
            "elapsed": round((self.finished or time.time()) - (self.started or self.created), 1),
        }


class JobManager:
    def __init__(self, work_root: Path):
        self.root = Path(work_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.queue: "queue.Queue[str]" = queue.Queue()
        self.lock = threading.Lock()
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()

    # ------------------------------------------------------------------ api
    def submit(self, script: str, settings: dict[str, Any],
               files: list[tuple[str, bytes]] | None = None) -> Job:
        job_id = uuid.uuid4().hex[:12]
        work = self.root / job_id
        uploads = work / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        for name, payload in (files or []):
            clean = SAFE_NAME.sub("_", Path(name).name).strip() or f"file-{uuid.uuid4().hex[:6]}"
            (uploads / clean).write_bytes(payload)
        job = Job(id=job_id, script=script, settings=settings, work_dir=work)
        with self.lock:
            self.jobs[job_id] = job
        self._cleanup_old()
        self.queue.put(job_id)
        return job

    def _cleanup_old(self, max_age_hours: float = 24.0, keep_last: int = 12) -> None:
        """Delete the working files of old jobs so the disk does not fill up."""
        now = time.time()
        ordered = sorted(self.jobs.values(), key=lambda j: j.created, reverse=True)
        for job in ordered[keep_last:]:
            if now - job.created < max_age_hours * 3600:
                continue
            if job.status == "running":
                continue
            self.jobs.pop(job.id, None)
            shutil.rmtree(job.work_dir, ignore_errors=True)

    def get(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="کار مورد نظر پیدا نشد")
        return job

    # --------------------------------------------------------------- worker
    def _loop(self) -> None:
        while True:
            job_id = self.queue.get()
            job = self.jobs.get(job_id)
            if job is None:
                continue
            try:
                self._run(job)
            except Cancelled as exc:
                job.status = "cancelled"
                job.step = "لغو شد"
                job.log(f"⏹️ {exc}")
            except Exception as exc:  # noqa: BLE001
                job.status = "error"
                job.error = str(exc)
                job.log(f"❌ {exc}")
            finally:
                job.finished = time.time()

    def _run(self, job: Job) -> None:
        job.status = "running"
        job.started = time.time()
        job.step = "آماده‌سازی"
        job.log(f"Mahva {__version__} · ffmpeg: {find_ffmpeg()}")
        s = job.settings
        uploads = job.work_dir / "uploads"

        project = parse_script(job.script, base_dir=uploads)
        if not project.scenes:
            raise ValueError("هیچ صحنه‌ای در متن پیدا نشد. با ## یک بخش بسازید.")
        if len(project.scenes) > MAX_SCENES:
            raise ValueError(f"تعداد صحنه‌ها ({len(project.scenes)}) از حد مجاز ({MAX_SCENES}) بیشتر است.")

        overlay = dict(s)
        overlay.update(s.get("overrides", {}))
        _apply_settings(project, overlay, job_dir=uploads)

        out_path = job.work_dir / (project.out_name or "video.mp4")
        options = RenderOptions(
            out_path=out_path,
            work_dir=job.work_dir / "work",
            preview=bool(s.get("preview")),
            force=bool(s.get("force")),
            keep_work=False,
            crf=s.get("crf"),
            preset=s.get("encoder_preset"),
            music=str(overlay.get("music_path") or "") or None,
            no_voice=bool(overlay.get("no_voice")),
            voice_engine=overlay.get("voice_engine"),
            voice=overlay.get("voice"),
            max_group=int(s.get("group", 10)),
        )
        renderer = Renderer(
            project, options,
            progress=lambda p, step: self._progress(job, p, step),
            log=job.log,
            cancel=lambda: job.cancel_flag,
        )
        result = renderer.render()
        job.output = result.path
        job.plan = result.plan
        job.progress = 1.0
        job.step = "تمام شد"
        job.status = "done"

    def _progress(self, job: Job, frac: float, step: str) -> None:
        job.progress = frac
        job.step = step


# ------------------------------------------------------------------- helpers
def _apply_settings(project: Project, s: dict[str, Any], job_dir: Path | None = None) -> None:
    if s.get("size"):
        project.width, project.height = int(s["size"][0]), int(s["size"][1])
    if s.get("fps"):
        project.fps = int(s["fps"])
    if s.get("theme"):
        project.theme = str(s["theme"])
    if s.get("font"):
        project.font_family = str(s["font"])
    if s.get("quality"):
        project.quality = str(s["quality"])
    if s.get("language"):
        project.language = str(s["language"])
    if s.get("rtl") is not None:
        project.rtl = bool(s["rtl"])
    if s.get("transition"):
        project.transition = str(s["transition"])
    if s.get("transition_duration") is not None:
        project.transition_duration = float(s["transition_duration"])
    if s.get("kenburns"):
        project.kenburns = str(s["kenburns"])
    if s.get("voice_engine"):
        project.voice_engine = str(s["voice_engine"])
    if s.get("voice"):
        project.voice = str(s["voice"])
    if s.get("rate"):
        project.rate = str(s["rate"])
    if s.get("music_path"):
        project.music = str(s["music_path"])
    if s.get("music_volume") is not None:
        project.music_volume = float(s["music_volume"])
    if s.get("voice_volume") is not None:
        project.voice_volume = float(s["voice_volume"])
    if s.get("scene_pad") is not None:
        project.scene_pad = float(s["scene_pad"])
    if s.get("min_scene") is not None:
        project.min_scene = float(s["min_scene"])
    if s.get("max_scene") is not None:
        project.max_scene = float(s["max_scene"])
    if s.get("no_voice"):
        project.voice_engine = "silent"
    project.out_name = str(s.get("out_name") or project.out_name or "video.mp4")


def _meta() -> dict[str, Any]:
    return {
        "version": __version__,
        "themes": theme_choices(),
        "presets": [{"key": k, "width": v[0], "height": v[1]} for k, v in VIDEO_PRESETS.items()],
        "transitions": TRANSITIONS,
        "qualities": list(QUALITY_PRESETS.keys()),
        "engines": engine_status(),
        "voices": {
            lang: voice_catalog(lang) for lang in ("fa", "en", "ar")
        },
        "fonts": available_families()[:60],
        "sample": SAMPLE_SCRIPT,
        "examples": _examples(),
        "limits": {
            "max_scenes": MAX_SCENES,
            "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
            "max_files": MAX_UPLOAD_FILES,
        },
    }


def _examples() -> list[dict[str, str]]:
    folder = ROOT_DIR / "examples"
    out: list[dict[str, str]] = []
    if folder.exists():
        for path in sorted(folder.glob("*.md")):
            out.append({"name": path.name, "label": path.stem})
    return out


# ----------------------------------------------------------------------- app
def create_app(work_root: Path | None = None) -> FastAPI:
    manager = JobManager(work_root or DEFAULT_WORK)
    app = FastAPI(title="Mahva", version=__version__)
    app.state.manager = manager

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        page = STATIC_DIR / "index.html"
        if not page.exists():
            return HTMLResponse("<h1>Mahva</h1><p>رابط وب پیدا نشد.</p>")
        return HTMLResponse(page.read_text(encoding="utf-8"))

    @app.get("/api/meta")
    def meta() -> dict[str, Any]:
        return _meta()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/examples")
    def examples() -> list[dict[str, str]]:
        return _examples()

    @app.get("/api/examples/{name}")
    def example(name: str) -> dict[str, str]:
        path = (ROOT_DIR / "examples" / Path(name).name)
        if not path.exists():
            raise HTTPException(404, "نمونه پیدا نشد")
        return {"name": path.name, "text": path.read_text(encoding="utf-8")}

    @app.post("/api/parse")
    def parse(payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("script") or "")
        if len(text) > MAX_SCRIPT_CHARS:
            raise HTTPException(413, "متن بیش از حد بلند است")
        project = parse_script(text, base_dir=Path.cwd())
        _apply_settings(project, payload.get("settings", {}))
        return {
            "title": project.title,
            "scenes": [
                {
                    "index": i,
                    "title": s.title,
                    "subtitle": s.subtitle,
                    "body": s.body,
                    "bullets": s.bullet_points,
                    "image": s.image,
                    "duration": s.duration,
                    "layout": s.layout,
                }
                for i, s in enumerate(project.scenes)
            ],
            "estimated_seconds": sum(
                max(project.min_scene,
                    s.duration or 0.0,
                    (len(s.spoken_text().split()) / max(1.0, project.words_per_second))
                    + 2 * project.scene_pad)
                for s in project.scenes
            ),
        }

    @app.post("/api/render")
    async def render(
        script: str = Form(...),
        settings: str = Form("{}"),
        images: list[UploadFile] = File(default=[]),
        music: UploadFile | None = File(default=None),
    ) -> dict[str, Any]:
        if len(script) > MAX_SCRIPT_CHARS:
            raise HTTPException(413, "متن بیش از حد بلند است")
        try:
            parsed_settings = json.loads(settings or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(400, f"تنظیمات نامعتبر: {exc}") from exc

        files: list[tuple[str, bytes]] = []
        for upload in images or []:
            payload = await upload.read()
            if len(payload) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, f"فایل {upload.filename} بزرگ‌تر از حد مجاز است")
            files.append((upload.filename or "image", payload))
            if len(files) > MAX_UPLOAD_FILES:
                raise HTTPException(413, "تعداد فایل‌ها زیاد است")
        if music is not None and music.filename:
            payload = await music.read()
            if len(payload) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "فایل موسیقی بزرگ‌تر از حد مجاز است")
            files.append((f"music__{music.filename}", payload))
            parsed_settings.setdefault("overrides", {})["music_name"] = f"music__{Path(music.filename).name}"

        job = manager.submit(script, parsed_settings, files)
        if music is not None and music.filename:
            music_path = job.work_dir / "uploads" / f"music__{SAFE_NAME.sub('_', Path(music.filename).name)}"
            job.settings.setdefault("overrides", {})["music_path"] = str(music_path)
        # images referenced from the script resolve inside the job's uploads dir
        job.settings.setdefault("overrides", {})["upload_dir"] = str(job.work_dir / "uploads")
        return {"job": job.public()}

    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str) -> dict[str, Any]:
        return manager.get(job_id).public()

    @app.post("/api/jobs/{job_id}/cancel")
    def job_cancel(job_id: str) -> dict[str, Any]:
        job = manager.get(job_id)
        job.cancel_flag = True
        job.step = "در حال لغو…"
        job.status = "cancelled" if job.status in ("queued",) else job.status
        return job.public()

    @app.get("/api/jobs/{job_id}/video")
    def job_video(job_id: str) -> FileResponse:
        job = manager.get(job_id)
        if not job.output or not job.output.exists():
            raise HTTPException(404, "ویدیو آماده نشده است")
        return FileResponse(job.output, media_type="video/mp4", filename=job.output.name)

    @app.get("/api/jobs/{job_id}/poster")
    def job_poster(job_id: str, scene: int = 1, scale: float = 0.35) -> FileResponse:
        job = manager.get(job_id)
        project = parse_script(job.script, base_dir=job.work_dir / "uploads")
        if not project.scenes:
            raise HTTPException(400, "صحنه‌ای وجود ندارد")
        index = max(0, min(scene - 1, len(project.scenes) - 1))
        for i, s in enumerate(project.scenes):
            if s.layout in ("", "auto"):
                s.layout = "overlay" if s.image else "plain"
        project.width = max(320, int(project.width * scale))
        project.height = max(180, int(project.height * scale))
        out = job.work_dir / f"poster_{index}_{int(time.time())}.png"
        render_preview(project, project.scenes[index], index, len(project.scenes), out)
        return FileResponse(out, media_type="image/png")

    return app


app = create_app()


def main() -> None:  # pragma: no cover - dev entry point
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="رابط وب Mahva")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--work", default=str(DEFAULT_WORK))
    args = parser.parse_args()
    global app
    app = create_app(Path(args.work))
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":  # pragma: no cover
    main()
