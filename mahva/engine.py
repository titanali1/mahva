"""The render engine: turns a parsed project into a finished MP4.

Pipeline
--------
1. plan      – figure out how long every scene lasts (from the voice-over audio)
2. cards     – render background + text overlays with Pillow
3. clips     – one Ken-Burns + text-fade clip per scene (ffmpeg)
4. voice     – place the narration on the timeline, mix in the music bed
5. assemble  – cross-fade the clips together (batched, so 200 scenes still work)
6. mux       – copy video + audio into the final file
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image

from . import ffmpeg as ff
from .schema import Project, Scene, make_plan_snapshot
from .textcard import CardRenderer, _hex_to_rgb, render_preview
from .themes import Theme, get_theme
from .tts import Speaker, estimate_duration

ProgressCb = Callable[[float, str], None]
LogCb = Callable[[str], None]


@dataclass
class RenderOptions:
    out_path: Path = Path("out/video.mp4")
    work_dir: Path | None = None
    crf: int | None = None
    preset: str | None = None
    audio_bitrate: str | None = None
    preview: bool = False           # fast, low-res, no TTS
    force: bool = False             # ignore the clip cache
    keep_work: bool = False
    threads: int | None = None
    music: str | None = None
    voice_engine: str | None = None
    voice: str | None = None
    no_voice: bool = False
    max_group: int = 10             # clips per xfade batch


@dataclass
class RenderResult:
    path: Path
    duration: float
    size_bytes: int
    scenes: int
    plan: dict = field(default_factory=dict)
    wall_seconds: float = 0.0


class Renderer:
    def __init__(self, project: Project, options: RenderOptions | None = None,
                 progress: ProgressCb | None = None, log: LogCb | None = None,
                 cancel: Callable[[], bool] | None = None):
        self.project = project
        self.opt = options or RenderOptions()
        self.progress = progress or (lambda _p, _s: None)
        self.log = log or (lambda _m: None)
        self.cancel = cancel or (lambda: False)

        if self.opt.preview:
            self.project.width = _even(max(320, int(self.project.width * 0.45)))
            self.project.height = _even(max(320, int(self.project.height * 0.45)))
            self.project.fps = min(24, self.project.fps)
            self.opt.no_voice = True

        self.ff = ff.FFmpeg(threads=self.opt.threads or max(1, (os.cpu_count() or 2) - 1))
        self.work = Path(self.opt.work_dir or Path(self.opt.out_path).parent / "work").resolve()
        self.work.mkdir(parents=True, exist_ok=True)
        self.cards_dir = self.work / "cards"
        self.clips_dir = self.work / "clips"
        self.voice_dir = self.work / "voice"
        for d in (self.cards_dir, self.clips_dir, self.voice_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.renderer = CardRenderer(project)

        quality_crf = {"fast": 25, "balanced": 21, "high": 18}.get(self.project.quality, 21)
        quality_preset = {"fast": "veryfast", "balanced": "medium", "high": "slow"}.get(
            self.project.quality, "medium")
        self.crf = self.opt.crf or (30 if self.opt.preview else quality_crf)
        self.preset = self.opt.preset or ("ultrafast" if self.opt.preview else quality_preset)
        self.audio_bitrate = self.opt.audio_bitrate or {"fast": "128k", "balanced": "160k",
                                                        "high": "192k"}.get(self.project.quality, "160k")

        engine = self.opt.voice_engine or self.project.voice_engine
        self.speaker = Speaker(
            engine="silent" if self.opt.no_voice else engine,
            voice=self.opt.voice or self.project.voice,
            rate=self.project.rate, pitch=self.project.pitch, volume=self.project.volume,
            language=self.project.language, log=self.log,
        )

        self.manifest_path = self.work / "manifest.json"
        self.manifest: dict = _load_json(self.manifest_path) or {"clips": {}}

    # ------------------------------------------------------------------ plan
    def plan(self) -> None:
        self.log(f"موتور صدا: {self.speaker.describe()}")
        total = len(self.project.scenes)
        for i, scene in enumerate(self.project.scenes):
            self._check_cancel()
            if scene.image and not Path(scene.image).exists():
                self.log(f"⚠️ تصویر صحنهٔ {i + 1} پیدا نشد ({scene.image}) — با پس‌زمینهٔ ساده ادامه می‌دهم.")
                scene.image = None
            self._resolve_layout(scene, i, total)
            narration = scene.spoken_text()
            duration = 0.0
            if scene.voice_file and Path(scene.voice_file).exists():
                scene.narration_file = str(Path(scene.voice_file).resolve())
                scene.narration_duration = self.ff.probe_duration(scene.narration_file)
            elif narration and self.speaker.enabled:
                out = self.voice_dir / f"scene_{i:04d}"
                speech = self.speaker.synthesize(narration, out, key=f"scene-{i}-{_digest(narration)}")
                if speech is not None:
                    scene.narration_file = str(speech.path)
                    scene.narration_duration = speech.duration
                else:
                    scene.narration_duration = estimate_duration(narration, self.project.words_per_second)
            else:
                scene.narration_duration = estimate_duration(narration, self.project.words_per_second) if narration else 0.0

            pad = self.project.scene_pad
            duration = max(
                self.project.min_scene,
                scene.narration_duration + 2 * pad,
                scene.duration or 0.0,
            )
            if scene.duration and scene.narration_duration + 2 * pad > scene.duration:
                self.log(f"صحنهٔ {i + 1}: صدا بلندتر از مدت تعیین‌شده بود؛ مدت صحنه افزایش یافت.")
            duration = min(duration, max(self.project.max_scene, scene.narration_duration + 2 * pad))
            scene.planned_duration = round(duration, 3)
            self.progress(0.05 + 0.10 * (i + 1) / max(1, total), f"زمان‌بندی صحنهٔ {i + 1}")
            if narration and scene.narration_duration:
                wps = len(narration.split()) / max(0.5, scene.narration_duration)
                _ = wps  # kept for future heuristics

    def _resolve_layout(self, scene: Scene, index: int, total: int) -> None:
        layout = (scene.layout or "auto").lower()
        if layout in ("auto", ""):
            if scene.image:
                layout = "overlay"
            elif index == 0 and (self.project.title.strip() or scene.title) and total > 1:
                layout = "title"          # opening card = big title
            else:
                layout = "plain"
        scene.layout_resolved = layout

    # ----------------------------------------------------------------- cards
    def _card_paths(self, scene: Scene, index: int, total: int) -> tuple[Path | None, Path]:
        theme = get_theme(scene.theme or self.project.theme)
        overlay_path = self.cards_dir / f"overlay_{index:04d}.png"
        bg_path = self.cards_dir / f"bg_{index:04d}.png"

        layout = scene.layout_resolved
        needs_bg_image = not scene.image
        if not bg_path.exists() or self.opt.force or self.opt.preview:
            if needs_bg_image:
                self.renderer.background(theme, seed=index + 1).save(bg_path)
        elif needs_bg_image:
            pass

        if not overlay_path.exists() or self.opt.force or self.opt.preview:
            text_layer = self.renderer.text_overlay(
                scene, index, total, layout=layout, image_path=scene.image,
            )
            text_layer.save(overlay_path)

        return (None if scene.image else bg_path), overlay_path

    # ---------------------------------------------------------------- clips
    def _scene_filtergraph(self, scene: Scene, index: int, dur: float, overlay: Path,
                           bg: Path | None) -> tuple[ff.Graph, str]:
        g = ff.Graph()
        W, H, fps = self.project.width, self.project.height, self.project.fps
        frames = max(1, int(round(dur * fps)))
        layout = scene.layout_resolved
        ken = self._kenburns_mode(scene, index)

        img_index = None
        bg_index = None
        if scene.image:
            img_index = g.add_input(["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", scene.image])
        if bg is not None:
            bg_index = g.add_input(["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(bg)])
        ov_index = g.add_input(["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(overlay)])

        if scene.image and layout == "split" and bg_index is not None:
            top_h = _even(H * 0.56)
            # gradient base (full frame) with the photo on the upper part
            base = g.chain(bg_index, f"scale={W}:{H}", "setsar=1", "format=rgba",
                           out=g.new_label("base"))
            photo = g.chain(img_index, *self._kenburns_filters(W, top_h, fps, dur, ken),
                            out=g.new_label("ph"))
            stage = g.new_label("v")
            g.add(f"[{base}][{photo}]overlay=0:0:format=auto:shortest=0[{stage}]")
        elif scene.image:
            stage = g.chain(img_index, *self._kenburns_filters(W, H, fps, dur, ken),
                            out=g.new_label("v"))
        else:
            stage = g.chain(bg_index, f"scale={W}:{H}", "setsar=1", "format=rgba",
                            out=g.new_label("v"))

        text = g.chain(ov_index, "format=rgba", f"fade=t=in:st=0.35:d=0.75:alpha=1",
                       out=g.new_label("t"))
        slide = int(round(H * 0.018))
        comp = g.new_label("v")
        g.add(f"[{stage}][{text}]overlay=x=0:y='if(lt(t,1.15),{slide}*(1-t/1.15),0)'"
              f":format=auto:shortest=0[{comp}]")

        chain = [f"fps={fps}", "setsar=1", "format=yuv420p"]
        if index == 0:
            chain.insert(0, "fade=t=in:st=0:d=0.7")
        if index == len(self.project.scenes) - 1:
            chain.append(f"fade=t=out:st={max(0.0, dur - 0.8):.3f}:d=0.8")
        out = g.chain(comp, *chain, out="vout")
        return g, out

    def _kenburns_mode(self, scene: Scene, index: int) -> str:
        mode = (scene.kenburns or "auto").lower()
        if mode in ("auto", ""):
            mode = (self.project.kenburns or "auto").lower()
        if mode in ("auto", ""):
            mode = ["in", "out", "pan-right", "pan-left"][index % 4]
        return mode

    def _kenburns_filters(self, cw: int, ch: int, fps: int, dur: float, mode: str) -> list[str]:
        if mode == "none":
            return [f"scale={cw}:{ch}:force_original_aspect_ratio=increase",
                    f"crop={cw}:{ch}", "setsar=1"]
        sup = 1.26
        sw, sh = _even(cw * sup), _even(ch * sup)
        frames = max(1.0, dur * fps)
        if mode == "out":
            z = f"max(1.26-0.26*on/{frames:.0f},1.0)"
            x = "iw/2-(iw/zoom/2)"
            y = "ih/2-(ih/zoom/2)"
        elif mode == "pan-right":
            z = "1.22"
            x = f"(iw-iw/zoom)*on/{frames:.0f}"
            y = "ih/2-(ih/zoom/2)"
        elif mode == "pan-left":
            z = "1.22"
            x = f"(iw-iw/zoom)*(1-on/{frames:.0f})"
            y = "ih/2-(ih/zoom/2)"
        else:  # in
            z = f"min(1.0+0.26*on/{frames:.0f},1.26)"
            x = "iw/2-(iw/zoom/2)"
            y = "ih/2-(ih/zoom/2)"
        return [
            f"scale={sw}:{sh}:force_original_aspect_ratio=increase",
            f"crop={sw}:{sh}",
            f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={cw}x{ch}:fps={fps}",
            "setsar=1",
        ]

    def _clip_signature(self, scene: Scene, index: int, dur: float, overlay: Path, bg: Path | None) -> str:
        image_stat = ""
        for p in (scene.image, str(overlay), str(bg) if bg else None):
            if p and Path(p).exists():
                st = Path(p).stat()
                image_stat += f"{Path(p).name}:{int(st.st_mtime)}:{st.st_size}|"
        payload = {
            "dur": round(dur, 3), "index": index, "layout": scene.layout_resolved,
            "ken": self._kenburns_mode(scene, index), "w": self.project.width,
            "h": self.project.height, "fps": self.project.fps, "crf": self.crf,
            "preset": self.preset, "assets": image_stat,
            "theme": scene.theme or self.project.theme, "accent": scene.accent,
            "fonts": self.project.font_family,
        }
        return hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    def build_clips(self) -> list[tuple[Path, float]]:
        total = len(self.project.scenes)
        clips: list[tuple[Path, float]] = []
        for i, scene in enumerate(self.project.scenes):
            self._check_cancel()
            dur = scene.planned_duration
            bg, overlay = self._card_paths(scene, i, total)
            clip = self.clips_dir / f"scene_{i:04d}.mp4"
            signature = self._clip_signature(scene, i, dur, overlay, bg)
            cached = self.manifest.get("clips", {}).get(str(i), {})
            self.log(f"صحنهٔ {i + 1}/{total}: {dur:.1f} ثانیه"
                     + (f" · تصویر: {Path(scene.image).name}" if scene.image else "")
                     + (f" · صدا: {'دارد' if scene.narration_file else 'ندارد'}"))
            if clip.exists() and cached.get("sig") == signature and not self.opt.force:
                self.log(f"  ↳ از حافظهٔ موقت استفاده شد ({clip.name})")
            else:
                self._render_clip(scene, i, dur, overlay, bg, clip)
                self.manifest.setdefault("clips", {})[str(i)] = {"sig": signature}
                _save_json(self.manifest_path, self.manifest)
            clips.append((clip, dur))
            self.progress(0.15 + 0.45 * (i + 1) / max(1, total), f"رندر صحنهٔ {i + 1} از {total}")
        return clips

    def _render_clip(self, scene: Scene, index: int, dur: float, overlay: Path, bg: Path | None,
                     clip: Path) -> None:
        g, vout = self._scene_filtergraph(scene, index, dur, overlay, bg)
        frames = max(1, int(round(dur * self.project.fps)))
        args = [*g.args(), "-map", f"[{vout}]", "-an",
                "-c:v", "libx264", "-preset", "veryfast" if not self.opt.preview else "ultrafast",
                "-crf", "18" if not self.opt.preview else "28",
                "-pix_fmt", "yuv420p", "-threads", str(max(1, min(4, self.ff.threads))),
                "-frames:v", str(frames), "-r", str(self.project.fps), str(clip)]
        self.ff.run(args, total=dur, step=f"صحنه {index + 1}", on_progress=None,
                    log=self.log, cancel=self.cancel)

    # ---------------------------------------------------------------- audio
    def build_audio(self, clips: list[tuple[Path, float]]) -> Path | None:
        self._check_cancel()
        T = self.project.final_duration
        if T <= 0:
            return None
        offsets = self.scene_offsets()
        g = ff.Graph()
        voice_labels: list[str] = []

        for i, scene in enumerate(self.project.scenes):
            if not scene.narration_file:
                continue
            idx = g.add_input(["-i", scene.narration_file])
            delay_ms = int(round((offsets[i] + self.project.scene_pad * 0.6) * 1000))
            label = g.new_label("a")
            g.add(f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                  f"volume={self.project.voice_volume:.3f},"
                  f"adelay=delays={delay_ms}:all=1[{label}]")
            voice_labels.append(label)

        music_path = self.opt.music or self.project.music
        has_music = bool(music_path and Path(music_path).exists())
        if has_music:
            music_idx = g.add_input(["-stream_loop", "-1", "-i", str(music_path)])
        else:
            music_idx = None

        if voice_labels:
            voice = g.new_label("a")
            if len(voice_labels) == 1:
                g.add(f"[{voice_labels[0]}]apad=whole_dur={T:.3f}[{voice}]")
            else:
                joined = "".join(f"[{lbl}]" for lbl in voice_labels)
                g.add(f"{joined}amix=inputs={len(voice_labels)}:normalize=0:duration=longest,"
                      f"apad=whole_dur={T:.3f}[{voice}]")
        else:
            voice = g.new_label("a")
            g.add(f"anullsrc=r=48000:cl=stereo,atrim=duration={T:.3f}[{voice}]")

        final = g.new_label("a")
        if music_idx is not None:
            mus = g.new_label("a")
            fade = max(0.5, self.project.music_fade)
            g.add(f"[{music_idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                  f"volume={self.project.music_volume:.3f},"
                  f"afade=t=in:st=0:d={fade:.2f},"
                  f"afade=t=out:st={max(0.0, T - fade):.2f}:d={fade:.2f},atrim=0:{T:.3f}[{mus}]")
            g.add(f"[{voice}][{mus}]amix=inputs=2:duration=first:normalize=0,"
                  f"apad=whole_dur={T:.3f},atrim=end={T:.3f}[{final}]")
        else:
            g.add(f"[{voice}]atrim=end={T:.3f}[{final}]")

        out = self.work / "audio.m4a"
        args = [*g.args(), "-map", f"[{final}]", "-c:a", "aac", "-b:a", self.audio_bitrate,
                "-ar", "48000", "-ac", "2", "-t", f"{T:.3f}", str(out)]
        self.ff.run(args, total=T, step="صداگذاری", on_progress=self._wrap_progress(0.60, 0.78),
                    log=self.log, cancel=self.cancel)
        self.log(f"نریشن ساخته شد ({T:.1f} ثانیه" + ("، با موسیقی پس‌زمینه" if has_music else "") + ")")
        return out

    def scene_offsets(self) -> list[float]:
        xf = self._effective_xfade()
        offsets: list[float] = []
        current = 0.0
        for i, scene in enumerate(self.project.scenes):
            offsets.append(current)
            current += scene.planned_duration - (xf if i < len(self.project.scenes) - 1 else 0)
        return offsets

    def _effective_xfade(self) -> float:
        if len(self.project.scenes) < 2:
            return 0.0
        shortest = min(s.planned_duration for s in self.project.scenes)
        return max(0.0, min(self.project.transition_duration, shortest * 0.4, 2.0))

    # ------------------------------------------------------------- assemble
    def assemble(self, clips: list[tuple[Path, float]], audio: Path | None) -> Path:
        self._check_cancel()
        xf = self._effective_xfade()
        if len(clips) == 1:
            video_only = clips[0][0]
        else:
            video_only = self._xfade_tree(clips, xf, level=0)

        out = Path(self.opt.out_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        args = ["-i", str(video_only)]
        if audio is not None:
            args += ["-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:a", "copy"]
        else:
            args += ["-map", "0:v:0", "-an"]
        if self.project.title:
            args += ["-metadata", f"title={self.project.title}"]
        args += ["-c:v", "copy", "-movflags", "+faststart",
                 "-t", f"{self.project.final_duration:.3f}", str(out)]
        self.ff.run(args, step="مونتاژ نهایی", log=self.log, cancel=self.cancel)
        self.progress(0.99, "نوشتن فایل نهایی")
        return out

    def _xfade_tree(self, clips: list[tuple[Path, float]], xf: float, level: int) -> Path:
        if len(clips) <= self.opt.max_group or level > 3:
            out = self.work / f"video_l{level}.mp4"
            if level == 0:
                out = self.work / "video.mp4"
            return self._xfade_pass(clips, xf, out, level)

        groups: list[list[tuple[Path, float]]] = []
        step = max(2, math.ceil(len(clips) / math.ceil(len(clips) / self.opt.max_group)))
        for start in range(0, len(clips), step):
            groups.append(clips[start:start + step])

        merged: list[tuple[Path, float]] = []
        for gi, group in enumerate(groups):
            if len(group) == 1:
                merged.append(group[0])
                continue
            out = self.work / f"group_{level}_{gi:03d}.mp4"
            duration = sum(d for _p, d in group) - xf * (len(group) - 1)
            self._xfade_pass(group, xf, out, level, transition_offset=gi)
            merged.append((out, duration))
        return self._xfade_tree(merged, xf, level + 1)

    def _xfade_pass(self, clips: list[tuple[Path, float]], xf: float, out: Path, level: int,
                    transition_offset: int = 0) -> Path:
        frames = len(clips)
        g = ff.Graph()
        for path, _dur in clips:
            g.add_input(["-i", str(path)])
        labels: list[str] = []
        for i in range(frames):
            label = g.new_label("x")
            g.add(f"[{i}:v]settb=AVTB,fps={self.project.fps},format=yuv420p,setsar=1[{label}]")
            labels.append(label)

        current = labels[0]
        offset = clips[0][1] - xf
        for i in range(1, frames):
            scene = self.project.scenes[min(i + transition_offset, len(self.project.scenes) - 1)]
            transition = (scene.transition or self.project.transition or "fade").lower()
            new = g.new_label("x")
            g.add(ff.xfade_pair(current, labels[i], transition, xf, max(0.0, offset), new))
            current = new
            offset += clips[i][1] - xf

        codec = ["-c:v", "libx264", "-preset", "veryfast" if not self.opt.preview else "ultrafast",
                 "-crf", "18" if not self.opt.preview else "27", "-pix_fmt", "yuv420p",
                 "-threads", str(max(1, min(6, self.ff.threads)))]
        args = [*g.args(), "-map", f"[{current}]", "-an", *codec, str(out)]
        total = sum(d for _p, d in clips) - xf * (frames - 1)
        self.ff.run(args, total=total, step=f"ترکیب {frames} کلیپ",
                    on_progress=self._wrap_progress(0.80, 0.97), log=self.log, cancel=self.cancel)
        return out

    # ------------------------------------------------------------------ run
    def render(self) -> RenderResult:
        started = time.time()
        self.log(f"شروع رندر · {self.project.width}×{self.project.height} · {self.project.fps}fps · "
                 f"{len(self.project.scenes)} صحنه")
        self._check_cancel()
        self.plan()
        clips = self.build_clips()
        audio = self.build_audio(clips)
        out = self.assemble(clips, audio)
        duration = self.project.final_duration
        result = RenderResult(
            path=out, duration=duration,
            size_bytes=out.stat().st_size if out.exists() else 0,
            scenes=len(self.project.scenes), plan=make_plan_snapshot(self.project),
            wall_seconds=round(time.time() - started, 1),
        )
        self._write_report(result)
        if not self.opt.keep_work:
            self._cleanup()
        self.progress(1.0, "تمام شد")
        self.log(f"✅ ویدیو آماده شد: {out.name} · {duration / 60:.1f} دقیقه · "
                 f"{result.size_bytes / 1e6:.1f} مگابایت · {result.wall_seconds} ثانیه پردازش")
        return result

    def preview_image(self, index: int = 0, path: Path | None = None) -> Path:
        self._resolve_layout(self.project.scenes[index], index, len(self.project.scenes))
        return render_preview(self.project, self.project.scenes[index], index,
                              len(self.project.scenes), path or (self.work / "preview.png"))

    # -------------------------------------------------------------- helpers
    def _write_report(self, result: RenderResult) -> None:
        report = {
            "output": str(result.path),
            "duration_seconds": round(result.duration, 2),
            "size_bytes": result.size_bytes,
            "scenes": result.scenes,
            "wall_seconds": result.wall_seconds,
            "plan": result.plan,
            "settings": {
                "width": self.project.width, "height": self.project.height,
                "fps": self.project.fps, "theme": self.project.theme,
                "font": self.project.font_family, "voice": self.speaker.describe(),
                "music": str(self.opt.music or self.project.music or ""),
            },
        }
        _save_json(self.work / "report.json", report)
        try:
            _save_json(Path(self.opt.out_path).with_suffix(".json"), report)
        except Exception:
            pass

    def _cleanup(self) -> None:
        for d in (self.cards_dir, self.voice_dir):
            shutil.rmtree(d, ignore_errors=True)

    def _check_cancel(self) -> None:
        if self.cancel():
            raise ff.Cancelled("رندر لغو شد")

    def _wrap_progress(self, lo: float, hi: float) -> ProgressCb:
        return lambda frac, step: self.progress(lo + (hi - lo) * max(0.0, min(1.0, frac)), step)


def _even(value: float) -> int:
    v = int(round(value))
    return v if v % 2 == 0 else v + 1


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def render_project(project: Project, options: RenderOptions | None = None, **kwargs) -> RenderResult:
    return Renderer(project, options, **kwargs).render()
