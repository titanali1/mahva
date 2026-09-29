# مهوا (Mahva) 🎬

**ساخت ویدیوی طولانی از متن و تصویر — بدون هیچ هزینهٔ API.**

مهوا متن فارسی شما را به یک ویدیوی کامل تبدیل می‌کند: هر بخش متن روی یک کارت زیبا
(یا روی عکس خودتان) می‌نشیند، صدای گوینده روی آن خوانده می‌شود، ترنزیشن و حرکت آرام
دوربین (Ken Burns) اضافه می‌شود و در نهایت یک فایل MP4 آمادهٔ انتشار — یوتیوب،
اینستاگرام، ریلز یا شورتس — تحویل می‌گیرید.

تمام پردازش **روی کامپیوتر خودتان** انجام می‌شود؛ هیچ متنی، تصویری یا صدایی به سرور
بیرونی فرستاده نمی‌شود و برای ساخت ویدیو هیچ کلید API یا اشتراکی لازم نیست.

```
متن  →  کارت‌های تصویری  →  صداگذاری  →  حرکت و ترنزیشن  →  MP4
```

---

## ✨ ویژگی‌ها

| | |
|---|---|
| 🆓 **بدون هزینهٔ API** | نه Runway، نه Kling، نه کلید ابری. همه‌چیز محلی است. |
| ⏱️ **ویدیوی طولانی** | ساختار دسته‌ای (batch) کراس‌فید؛ ساعت‌ها ویدیو با صدها صحنه هم قابل رندر است. |
| 🖼️ **متن + تصویر** | تصاویر خودتان با زوم/پن آرام، یا کارت‌های متنی با پس‌زمینهٔ گرادیانی. |
| 🗣️ **صداگذاری فارسی** | edge-tts (صدای نورال رایگان)، eSpeak، piper، SAPI ویندوز، `say` مک — یا بدون صدا. |
| 🔤 **فارسی درست** | شکل‌دهی و راست‌به‌چپ با `arabic-reshaper` + `python-bidi` — بدون نیاز به libraqm. |
| 🎛️ **۶ تم رنگی** | نیمه‌شب، غروب، جنگل، کهربا، کاغذی و مرکب + رنگ تأکیدی اختصاصی هر صحنه. |
| 🌐 **رابط وب** | ویرایشگر متن، آپلود تصویر با drag & drop، پیش‌نمایش زندهٔ صحنه‌ها، نوار پیشرفت و پلیر. |
| 🔁 **حافظهٔ موقت هوشمند** | فقط صحنه‌های تغییرکرده دوباره رندر می‌شوند؛ ویرایش یک بخش، رندر را از نو شروع نمی‌کند. |

---

## 🚀 نصب

```bash
git clone https://github.com/titanali1/mahva.git
cd mahva
pip install -r requirements.txt      # یا: pip install -e ".[web,voice]"
python -m mahva doctor               # بررسی ffmpeg، فونت و موتور صدا
```

> راهنمای گام‌به‌گام (ویندوز/مک/لینوکس، داکر، عیب‌یابی):
> [`docs/setup-fa.md`](docs/setup-fa.md)

> **ffmpeg لازم نیست نصب کنید.** مهوا نسخهٔ آمادهٔ ffmpeg را از طریق بستهٔ
> `imageio-ffmpeg` همراه خود می‌آورد (اگر روی سیستم ffmpeg داشته باشید، از همان
> استفاده می‌کند). فونت **وزیرمتن** هم در `assets/fonts` همراه پروژه است.

---

## 🕹️ استفاده

راهنمای کامل نصب و راه‌اندازی: **[`docs/setup-fa.md`](docs/setup-fa.md)**

### ۱) رابط وب (پیشنهادی)

```bash
python -m mahva serve --port 8000
# سپس در مرورگر:  http://localhost:8000
```

ویرایشگر متن، آپلود تصاویر، انتخاب تم/صدا/قاب، پیش‌نمایش کارت‌ها و پلیر ویدیو —
همه در یک صفحه.

### ۲) خط فرمان

```bash
# رندر کامل با صداگذاری و قاب افقی
python -m mahva render examples/demo-fa.md -o out/demo.mp4

# ریلز عمودی ۹:۱۶ با صدای دلارا
python -m mahva render story.md --preset-size portrait --voice fa-IR-DilaraNeural

# فقط پیش‌نمایش یک کارت (PNG) بدون رندر ویدیو
python -m mahva preview story.md -o card.png --scene 2

# زمان‌بندی و تخمین مدت، پیش از رندر
python -m mahva plan story.md

# ویدیوی بلند با موسیقی پس‌زمینه و تم غروب
python -m mahva render story.md --music music.mp3 --music-volume 0.06 --theme sunset --quality high
```

### ۳) در کد پایتون

```python
from mahva import parse_script, render_project

project = parse_script(open("story.md", encoding="utf-8").read())
result = render_project(project)          # out/video.mp4
print(result.duration, result.size_bytes)
```

---

## 📝 قالب متن سِناوریو

فقط چند قاعده ساده؛ بقیه‌اش متن آزاد است:

```markdown
# عنوان کل ویدیو          ← به‌عنوان عنوان و زیرنویس پایین کارت‌ها هم استفاده می‌شود

@theme midnight           ← تم رنگی کل پروژه
@resolution landscape     ← قاب: landscape | portrait | square | 1080x1920 | …
@fps 30

متن اینجا مقدمهٔ ویدیو است و روی کارت اول می‌نشیند.

## عنوان صحنهٔ اول
@image photos/one.jpg     ← تصویر همین صحنه
@duration 12              ← مدت دلخواه (ثانیه)؛ اگر ندهید از روی صدا/متن محاسبه می‌شود

این متن هم روی کارت نوشته می‌شود و هم خوانده می‌شود.

- نکتهٔ اول
- نکتهٔ دوم

## صحنهٔ دوم
@layout split             ← چیدمان: auto | title | overlay | split | plain
@kenburns out
@transition circleopen
متن صحنهٔ دوم…
```

**دستورهای مفید:** `@voice`، `@rate +15%`، `@transition`، `@kenburns`، `@music`،
`@music_volume`، `@no_voice`، `@watermark`، `@chunk`، `@min_scene`، `@max_scene`،
`@pad`.

فهرست کامل در [`docs/script-format.md`](docs/script-format.md) آمده است.

---

## 🗣️ صداگذاری رایگان

مهوا موتور صدا را خودش انتخاب می‌کند (`auto`):

| موتور | نیازمندی | کیفیت |
|---|---|---|
| `edge` | اینترنت (edge-tts، بدون کلید) | نورال، بسیار خوب — صداهای `fa-IR-DilaraNeural` و `fa-IR-FaridNeural` |
| `espeak` | نصب `espeak-ng` | ماشینی ولی آفلاین و همیشه در دسترس |
| `piper` | نصب `piper` + فایل مدل | نورال آفلاین |
| `sapi` | ویندوز | صدای پیش‌فرض ویندوز |
| `say` | مک | صدای پیش‌فرض مک |
| `silent` | — | بدون صدا؛ مدت هر صحنه از تعداد کلمات تخمین زده می‌شود |

اگر صدای ابری در دسترس نباشد، مهوا خودکار به حالت بدون صدا برمی‌گردد و ویدیو را
کامل می‌سازد (هیچ‌وقت وسط کار نمی‌ماند).

برای هر صحنه می‌توانید فایل صدای آماده بدهید: `@voice_file path/to/voice.mp3`.

---

## 📚 کتابخانهٔ پایتون

```python
from mahva import Project, Scene, RenderOptions, Renderer

project = Project(title="آموزش سریع", width=1920, height=1080, theme="forest")
project.scenes = [
    Scene(title="مقدمه", subtitle="چرا این موضوع مهم است؟", image="a.jpg"),
    Scene(title="نتیجه", body="جمع‌بندی…", bullet_points=["اول", "دوم"], duration=8),
]
renderer = Renderer(project, RenderOptions(out_path="out/lesson.mp4"))
renderer.render()
```

---

## 🐳 داکر

```bash
docker build -t mahva .
docker run --rm -p 8000:8000 -v "$PWD/out:/app/out" mahva     # رابط وب روی http://localhost:8000
```

## 🧪 تست

```bash
pip install pytest
python -m pytest -q            # ۸ تست، شامل یک رندر واقعی سرتاسری
```

---

## 🤝 مشارکت

Issue و Pull Request خوش‌آمد است. اگر ایده‌ای برای قالب‌های جدید کارت، موتورهای صدا
یا بهینه‌سازی سرعت رندر دارید، خوشحال می‌شوم بشنوم.

## 📄 مجوز

MIT — استفادهٔ تجاری و شخصی آزاد است.
فونت وزیرمتن تحت مجوز SIL OFL 1.1 همراه پروژه توزیع می‌شود.

---

## English TL;DR

**Mahva** turns a Persian (or any RTL/LTR) script into a long narrated video —
completely free and fully local. No paid AI APIs: `ffmpeg` (bundled via
`imageio-ffmpeg`) for video, `Pillow` for the Persian text cards, free TTS for
the voice-over.

```bash
pip install -r requirements.txt
python -m mahva serve --port 8000          # web UI
python -m mahva render examples/demo-fa.md -o out/demo.mp4   # CLI
```

Long videos are assembled in batches with cross-fades, so hundreds of scenes
render without blowing up ffmpeg's filter graph. Each scene gets a Ken-Burns
photo move or an animated gradient card, word-accurate narration timing, and an
optional music bed. Licensed MIT.
