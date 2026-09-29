"""Command line interface: ``python -m mahva ...``"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ffmpeg as ff
from .engine import RenderOptions, Renderer
from .fonts import available_families
from .parser import parse_script, parse_script_file
from .schema import QUALITY_PRESETS, TRANSITIONS, VIDEO_PRESETS, Project
from .themes import theme_choices
from .tts import engine_status, voice_catalog


def _bar(frac: float, width: int = 28) -> str:
    frac = max(0.0, min(1.0, frac))
    filled = int(frac * width)
    return "█" * filled + "░" * (width - filled)


class _Console:
    def __init__(self, quiet: bool = False, json_only: bool = False):
        self.quiet = quiet
        self.json_only = json_only
        self._last = ""

    def log(self, message: str) -> None:
        if self.quiet or self.json_only:
            return
        print(message, flush=True)

    def progress(self, frac: float, step: str) -> None:
        if self.quiet or self.json_only:
            return
        line = f"\r{_bar(frac)} {frac * 100:5.1f}%  {step[:44]:<44}"
        if line != self._last:
            sys.stdout.write(line)
            sys.stdout.flush()
            self._last = line

    def done(self) -> None:
        if not self.quiet and not self.json_only:
            sys.stdout.write("\n")
            sys.stdout.flush()


def _apply_overrides(project: Project, args: argparse.Namespace) -> Project:
    if getattr(args, "size", None):
        w, h = args.size.lower().split("x")
        project.width, project.height = int(w), int(h)
    if getattr(args, "preset_size", None):
        w, h = VIDEO_PRESETS[args.preset_size]
        project.width, project.height = w, h
    if getattr(args, "fps", None):
        project.fps = args.fps
    if getattr(args, "theme", None):
        project.theme = args.theme
    if getattr(args, "font", None):
        project.font_family = args.font
    if getattr(args, "quality", None):
        project.quality = args.quality
    if getattr(args, "transitions_duration", None):
        project.transition_duration = args.transitions_duration
    if getattr(args, "transition", None):
        project.transition = args.transition
    if getattr(args, "voice", None):
        project.voice = args.voice
    if getattr(args, "engine", None):
        project.voice_engine = args.engine
    if getattr(args, "rate", None):
        project.rate = args.rate
    if getattr(args, "music", None):
        project.music = str(Path(args.music).expanduser().resolve())
    if getattr(args, "music_volume", None) is not None:
        project.music_volume = args.music_volume
    if getattr(args, "max_scene", None):
        project.max_scene = args.max_scene
    if getattr(args, "min_scene", None):
        project.min_scene = args.min_scene
    if getattr(args, "pad", None) is not None:
        project.scene_pad = args.pad
    if getattr(args, "rtl", False):
        project.rtl = True
    if getattr(args, "ltr", False):
        project.rtl = False
    if getattr(args, "lang", None):
        project.language = args.lang
    if getattr(args, "no_voice", False):
        project.voice_engine = "silent"
    return project


def _load_project(args: argparse.Namespace) -> Project:
    if getattr(args, "script", None):
        path = Path(args.script).expanduser().resolve()
        project = parse_script_file(path)
        project.out_name = project.out_name or f"{path.stem}.mp4"
    else:
        text = sys.stdin.read()
        project = parse_script(text, Path.cwd())
    return _apply_overrides(project, args)


def cmd_render(args: argparse.Namespace) -> int:
    console = _Console(args.quiet, args.json)
    project = _load_project(args)
    if not project.scenes:
        print("هیچ صحنه‌ای در متن پیدا نشد.", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser().resolve() if args.out else \
        Path(args.script).expanduser().resolve().with_suffix(".mp4")
    options = RenderOptions(
        out_path=out,
        work_dir=Path(args.work).expanduser().resolve() if args.work else None,
        preview=args.preview, force=args.force, keep_work=args.keep_work,
        music=None, voice_engine=None, voice=None, no_voice=args.no_voice,
        audio_bitrate=args.audio_bitrate, crf=args.crf, preset=args.encoder_preset,
        threads=args.threads, max_group=args.group,
    )
    renderer = Renderer(project, options, progress=console.progress, log=console.log)
    try:
        result = renderer.render()
    except ff.Cancelled as exc:
        console.done()
        print(f"لغو شد: {exc}", file=sys.stderr)
        return 130
    except KeyboardInterrupt:
        console.done()
        print("\nمتوقف شد.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001
        console.done()
        print(f"خطا: {exc}", file=sys.stderr)
        if args.traceback:
            raise
        return 1
    console.done()
    if args.json:
        print(json.dumps(json.loads((result.path.with_suffix('.json')).read_text(encoding="utf-8"))
                         if result.path.with_suffix(".json").exists() else result.plan,
                         ensure_ascii=False, indent=2))
    else:
        print(f"خروجی: {result.path}")
        print(f"مدت: {result.duration / 60:.2f} دقیقه · حجم: {result.size_bytes / 1e6:.1f} مگابایت"
              f" · زمان پردازش: {result.wall_seconds:.0f} ثانیه")
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    project = _load_project(args)
    if not project.scenes:
        print("هیچ صحنه‌ای پیدا نشد.", file=sys.stderr)
        return 2
    index = max(0, min(args.scene - 1, len(project.scenes) - 1))
    out = Path(args.out).expanduser().resolve()
    renderer = Renderer(project, RenderOptions(out_path=out, no_voice=True))
    path = renderer.preview_image(index, out)
    print(f"پیش‌نمایش: {path}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    project = _load_project(args)
    from .tts import estimate_duration
    total = 0.0
    print(f"عنوان: {project.title or '-'}")
    print(f"قاب: {project.width}×{project.height} · {project.fps}fps · تم: {project.theme} · فونت: {project.font_family}")
    print("-" * 72)
    for i, scene in enumerate(project.scenes, start=1):
        text = scene.spoken_text()
        seconds = scene.duration or (estimate_duration(text) + 2 * project.scene_pad)
        total += max(project.min_scene, seconds)
        kind = "تصویر" if scene.image else "متن"
        layout = scene.layout or "auto"
        print(f"{i:>3}. [{kind}/{layout}] {seconds:5.1f}s  {(scene.title or scene.subtitle or text)[:60]}")
        if scene.image:
            print(f"      تصویر: {scene.image}")
    print("-" * 72)
    print(f"تخمین کل (بدون کسر کراس‌فید): {total / 60:.2f} دقیقه · "
          f"{len(project.scenes)} صحنه · کراس‌فید {project.transition} {project.transition_duration}s")
    return 0


def cmd_voices(args: argparse.Namespace) -> int:
    print("موتورهای موجود روی این سیستم:")
    for engine, ok in engine_status().items():
        print(f"  {'✅' if ok else '—'} {engine}")
    print("\nصدای پیشنهادی (رایگان):")
    for item in voice_catalog(args.lang):
        print(f"  {item['engine']:<8} {item['voice']:<26} {item['label']}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    print("Mahva doctor")
    print(f"  ffmpeg : {ff.find_ffmpeg()}")
    print(f"  python : {sys.version.split()[0]}  ({sys.platform})")
    try:
        from PIL import features
        print(f"  pillow : raqm={features.check('raqm')} freetype={features.check('freetype2')}"
              "   (بدون raqm هم کار می‌کند: شکل‌دهی داخلی)")
    except Exception as exc:  # noqa: BLE001
        print(f"  pillow : خطا {exc}")
    print(f"  تم‌ها   : {', '.join(t['key'] for t in theme_choices())}")
    families = available_families()
    print(f"  فونت‌ها: {len(families)} خانواده — نمونه: {', '.join(families[:8])}")
    print("  موتور صدا:")
    for engine, ok in engine_status().items():
        print(f"    {'✅' if ok else '—'} {engine}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mahva", description="ساخت ویدیوی طولانی از متن و تصویر — بدون هزینهٔ API",
    )
    sub = parser.add_subparsers(dest="command")

    def add_common(p: argparse.ArgumentParser, render: bool = True) -> None:
        p.add_argument("script", help="فایل متن سِناوریو (Markdown ساده)")
        p.add_argument("--size", help="ابعاد دلخواه، مثل 1080x1920")
        p.add_argument("--preset-size", choices=sorted(VIDEO_PRESETS), help="قاب آماده")
        p.add_argument("--fps", type=int, help="فریم بر ثانیه (پیش‌فرض ۳۰)")
        p.add_argument("--theme", choices=[t["key"] for t in theme_choices()], help="تم رنگی")
        p.add_argument("--font", help="نام فونت (مثلاً Vazirmatn)")
        p.add_argument("--quality", choices=sorted(QUALITY_PRESETS))
        p.add_argument("--lang", help="زبان متن (fa, en, ar …)")
        p.add_argument("--rtl", action="store_true", help="راست‌به‌چپ")
        p.add_argument("--ltr", action="store_true", help="چپ‌به‌راست")
        p.add_argument("--transition", choices=TRANSITIONS, help="نوع کراس‌فید")
        p.add_argument("--transitions-duration", type=float, help="مدت کراس‌فید (ثانیه)")
        p.add_argument("--engine", help="موتور صدا: auto|edge|sapi|say|espeak|pico|piper|silent")
        p.add_argument("--voice", help="نام صدا (مثلاً fa-IR-DilaraNeural)")
        p.add_argument("--rate", help="سرعت گفتار (مثلاً +15%%)")
        p.add_argument("--music", help="فایل موسیقی پس‌زمینه")
        p.add_argument("--music-volume", type=float, help="بلندی موسیقی (۰ تا ۱)")
        p.add_argument("--pad", type=float, help="سکوت ابتدا/انتهای هر صحنه (ثانیه)")
        p.add_argument("--min-scene", type=float, help="کوتاه‌ترین مدت صحنه")
        p.add_argument("--max-scene", type=float, help="بلندترین مدت صحنه")
        p.add_argument("--no-voice", action="store_true", help="بدون صدا (فقط متن و تصویر)")
        p.add_argument("--quiet", action="store_true")

    p = sub.add_parser("render", help="ساخت ویدیو")
    add_common(p)
    p.add_argument("-o", "--out", help="مسیر فایل خروجی")
    p.add_argument("--work", help="پوشهٔ فایل‌های موقت")
    p.add_argument("--preview", action="store_true", help="رندر سریع کم‌کیفیت برای تست")
    p.add_argument("--force", action="store_true", help="نادیده گرفتن حافظهٔ موقت")
    p.add_argument("--keep-work", action="store_true", help="نگه داشتن فایل‌های میانی")
    p.add_argument("--crf", type=int, help="کیفیت x264 (کمتر = بهتر)")
    p.add_argument("--encoder-preset", help="preset انکودر x264")
    p.add_argument("--audio-bitrate", help="بیت‌ریت صدا (مثلاً 192k)")
    p.add_argument("--threads", type=int, help="تعداد هسته‌های مصرفی")
    p.add_argument("--group", type=int, default=10, help="تعداد کلیپ در هر دستهٔ کراس‌فید")
    p.add_argument("--json", action="store_true", help="چاپ گزارش JSON")
    p.add_argument("--traceback", action="store_true")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("preview", help="رندر یک کارت نمونه (PNG)")
    add_common(p)
    p.add_argument("-o", "--out", default="preview.png", help="مسیر تصویر خروجی")
    p.add_argument("--scene", type=int, default=1, help="شمارهٔ صحنه")
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("plan", help="نمایش زمان‌بندی و صحنه‌ها")
    add_common(p)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("voices", help="نمایش موتورها و صداهای موجود")
    p.add_argument("--lang", default="fa")
    p.set_defaults(func=cmd_voices)

    p = sub.add_parser("doctor", help="بررسی محیط (ffmpeg، فونت، صدا)")
    p.add_argument("--lang", default="fa")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("serve", help="اجرای رابط وب")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--work", help="پوشهٔ کار رابط وب")
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=cmd_serve)
    return parser


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .webapp import DEFAULT_WORK, create_app

    app = create_app(Path(args.work) if args.work else DEFAULT_WORK)
    print(f"رابط وب Mahva روی http://{args.host}:{args.port} بالا می‌آید…")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info", reload=args.reload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
