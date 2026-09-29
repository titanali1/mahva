"""Free, offline-friendly voice-over backends.

Engines are auto-detected in this order:

* ``edge``    – Microsoft Edge read-aloud voices (needs internet, no API key)
* ``sapi``    – Windows SAPI5 (built into Windows)
* ``say``     – macOS ``say``
* ``espeak``  – eSpeak NG (Linux, supports Persian ``fa``)
* ``pico``    – SVOX pico2wave
* ``piper``   – Rhasspy Piper neural TTS (fully local, needs a model file)
* ``silent``  – no audio; scene length is estimated from the word count

Nothing here ever calls a paid API.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .ffmpeg import probe_duration

LogFn = Callable[[str], None]

# A few well-known free neural voices (edge-tts).  Users can type any name.
EDGE_VOICES: dict[str, list[tuple[str, str]]] = {
    "fa": [("fa-IR-DilaraNeural", "دلارا (زن)"), ("fa-IR-FaridNeural", "فرید (مرد)")],
    "en": [("en-US-AriaNeural", "Aria (US, female)"), ("en-US-GuyNeural", "Guy (US, male)"),
           ("en-GB-SoniaNeural", "Sonia (UK, female)")],
    "ar": [("ar-EG-SalmaNeural", "سلمى (مصر)"), ("ar-SA-ZariyahNeural", "زارية (سعودي)")],
    "tr": [("tr-TR-EmelNeural", "Emel")],
    "de": [("de-DE-KatjaNeural", "Katja"), ("de-DE-ConradNeural", "Conrad")],
    "fr": [("fr-FR-DeniseNeural", "Denise"), ("fr-FR-HenriNeural", "Henri")],
}


@dataclass
class VoiceInfo:
    engine: str
    voice: str | None
    detail: str = ""


@dataclass
class Speech:
    path: Path
    duration: float
    engine: str


def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def detect_engine(preferred: str = "auto") -> str:
    """Pick the best available voice engine for this machine."""
    if preferred and preferred != "auto":
        return preferred
    env = os.environ.get("MAHVA_VOICE_ENGINE")
    if env:
        return env
    if _has("piper") and os.environ.get("MAHVA_PIPER_MODEL"):
        return "piper"
    if _has("espeak-ng") or _has("espeak"):
        return "espeak"
    if _has("pico2wave"):
        return "pico"
    if sys.platform == "win32":
        return "sapi"
    if sys.platform == "darwin" and _has("say"):
        return "say"
    if _module_available("edge_tts"):
        return "edge"
    if _has("say"):
        return "say"
    return "silent"


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def engine_status() -> dict[str, bool]:
    return {
        "edge": _module_available("edge_tts"),
        "sapi": sys.platform == "win32",
        "say": sys.platform == "darwin" and _has("say"),
        "espeak": _has("espeak-ng") or _has("espeak"),
        "pico": _has("pico2wave"),
        "piper": _has("piper"),
        "silent": True,
    }


class Speaker:
    """Renders narration text to audio files."""

    def __init__(self, engine: str = "auto", voice: str | None = None, rate: str = "+0%",
                 pitch: str = "+0Hz", volume: str = "+0%", language: str = "fa",
                 log: LogFn | None = None):
        self.engine = detect_engine(engine)
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        self.language = language
        self.log = log or (lambda _m: None)
        self._cache: dict[str, Speech] = {}
        self._online_checked = False

    # ------------------------------------------------------------------ api
    @property
    def enabled(self) -> bool:
        return self.engine != "silent"

    def describe(self) -> str:
        if self.engine == "silent":
            return "بدون صدا (مدت هر صحنه از روی تعداد کلمات تخمین زده می‌شود)"
        return f"{self.engine} · {self.voice or 'صدای پیش‌فرض'}"

    def check_online(self, host: str = "speech.platform.bing.com", port: int = 443,
                     timeout: float = 3.0) -> bool:
        """Quick connectivity probe so cloud voices fail fast instead of hanging."""
        import socket
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def synthesize(self, text: str, out_path: str | Path, *, key: str | None = None) -> Speech | None:
        text = " ".join((text or "").split())
        if not text:
            return None
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cache_key = key or f"{hash(text)}-{self.engine}-{self.voice}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached.path.exists():
                return cached
        if not self.enabled:
            return None

        suffix = {"edge": ".mp3", "say": ".aiff", "sapi": ".wav", "espeak": ".wav",
                  "pico": ".wav", "piper": ".wav"}.get(self.engine, ".wav")
        if self.engine == "edge" and not self._online_checked:
            self._online_checked = True
            if not self.check_online():
                self.log("⚠️ اتصال اینترنت برای صدای ابری (edge-tts) برقرار نشد → "
                         "ویدیو بدون صدا ساخته می‌شود. برای صدای آفلاین می‌توانید "
                         "espeak-ng یا piper نصب کنید.")
                self.engine = "silent"
                return None
        target = out.with_suffix(suffix)
        for attempt in range(3):
            try:
                self._dispatch(text, target)
                if target.exists() and target.stat().st_size > 512:
                    duration = probe_duration(target)
                    speech = Speech(target, duration, self.engine)
                    self._cache[cache_key] = speech
                    return speech
            except Exception as exc:  # noqa: BLE001
                self.log(f"TTS ({self.engine}) تلاش {attempt + 1} ناموفق: {exc}")
                if attempt == 1:
                    import time as _t
                    _t.sleep(1.5)
                if attempt == 2:
                    if self.engine != "silent":
                        self.log("به حالت بدون صدا سوییچ می‌کنم.")
                    self.engine = "silent"
                    return None
        return None

    # -------------------------------------------------------------- engines
    def _dispatch(self, text: str, target: Path) -> None:
        if self.engine == "edge":
            self._edge(text, target)
        elif self.engine == "sapi":
            self._sapi(text, target)
        elif self.engine == "say":
            self._say(text, target)
        elif self.engine == "espeak":
            self._espeak(text, target)
        elif self.engine == "pico":
            self._pico(text, target)
        elif self.engine == "piper":
            self._piper(text, target)
        else:
            raise RuntimeError("engine disabled")

    def _edge(self, text: str, target: Path) -> None:
        import edge_tts

        voice = self.voice or (EDGE_VOICES.get(self.language, EDGE_VOICES["fa"])[0][0])

        async def _run() -> None:
            kwargs: dict[str, str] = {"rate": self.rate, "volume": self.volume}
            if self.pitch and self.pitch not in ("+0Hz", "0Hz"):
                kwargs["pitch"] = self.pitch
            communicate = edge_tts.Communicate(text, voice, **kwargs)
            await communicate.save(str(target))

        asyncio.run(_run())

    def _sapi(self, text: str, target: Path) -> None:
        import win32com.client  # type: ignore
        from win32com.client import constants  # type: ignore

        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Open(str(target), 3, False)  # SSFMCreateForWrite
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        if self.voice:
            for token in voice.GetVoices():
                if self.voice.lower() in token.GetDescription().lower():
                    voice.Voice = token
                    break
        stream.Format.Type = 22  # SAFT22kHz16BitMono
        voice.AudioOutputStream = stream
        rate = _sapi_rate(self.rate)
        voice.Rate = rate
        voice.Speak(text)
        stream.Close()

    def _say(self, text: str, target: Path) -> None:
        cmd = ["say", "-o", str(target), "--data-format=LEF32@22050"]
        if self.voice:
            cmd += ["-v", self.voice]
        rate = _rate_to_wpm(self.rate)
        if rate:
            cmd += ["-r", str(rate)]
        cmd.append(text)
        _run(cmd)

    def _espeak(self, text: str, target: Path) -> None:
        exe = "espeak-ng" if _has("espeak-ng") else "espeak"
        lang = {"fa": "fa", "ar": "ar", "en": "en", "tr": "tr", "de": "de", "fr": "fr"}.get(
            self.language, "fa")
        cmd = [exe, "-v", lang, "-s", str(_rate_to_wpm(self.rate) or 160), "-w", str(target), text]
        _run(cmd)

    def _pico(self, text: str, target: Path) -> None:
        lang = {"fa": "fa-IR", "ar": "ar", "en": "en-US", "de": "de-DE", "fr": "fr-FR"}.get(
            self.language, "fa-IR")
        _run(["pico2wave", "-l", lang, "-w", str(target), text])

    def _piper(self, text: str, target: Path) -> None:
        model = os.environ.get("MAHVA_PIPER_MODEL")
        if not model:
            raise RuntimeError("متغیر MAHVA_PIPER_MODEL تنظیم نشده است")
        cmd = ["piper", "--model", model, "--output_file", str(target)]
        proc = subprocess.run(cmd, input=text, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-300:])


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {proc.stderr[-300:]}")


def _rate_to_wpm(rate: str) -> int | None:
    """Convert ``+15%`` (edge syntax) into words per minute."""
    try:
        pct = float((rate or "+0%").strip().rstrip("%").replace("+", ""))
    except ValueError:
        return None
    return int(round(170 * (1 + pct / 100.0)))


def _sapi_rate(rate: str) -> int:
    """SAPI rate is -10..10."""
    try:
        pct = float((rate or "+0%").strip().rstrip("%").replace("+", ""))
    except ValueError:
        return 0
    return max(-10, min(10, int(round(pct / 10.0))))


def estimate_duration(text: str, words_per_second: float = 2.45) -> float:
    words = max(1, len([w for w in (text or "").split() if w.strip()]))
    return max(1.5, words / max(0.5, words_per_second))


def voice_catalog(language: str = "fa") -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for voice, label in EDGE_VOICES.get(language, []):
        out.append({"engine": "edge", "voice": voice, "label": label})
    if language == "fa":
        out.append({"engine": "espeak", "voice": "fa", "label": "eSpeak فارسی (آفلاین)"})
    return out
