# راه‌اندازی مهوا — گام به گام

این راهنما برای کسی نوشته شده که می‌خواهد از صفر مهوا را روی کامپیوتر خودش بالا بیاورد.
ترتیب کار: **پایتون → نصب بسته‌ها → بررسی محیط → اجرا**.

---

## ۱. پیش‌نیازها

| نیاز | توضیح |
|---|---|
| **Python 3.9 یا بالاتر** | [python.org/downloads](https://www.python.org/downloads/) — در ویندوز گزینهٔ *Add Python to PATH* را تیک بزنید |
| **ffmpeg** | **لازم نیست نصب کنید.** مهوا نسخهٔ آماده را با بستهٔ `imageio-ffmpeg` می‌آورد. اگر روی سیستم ffmpeg داشته باشید، از همان استفاده می‌کند |
| **فونت فارسی** | **لازم نیست نصب کنید.** فونت وزیرمتن همراه پروژه است (`assets/fonts`) |
| **اینترنت** | فقط برای صدای نورال گوینده لازم است؛ بدون اینترنت ویدیو بی‌صدا و بی‌مشکل ساخته می‌شود |

> ویندوز: اگر `python` کار نکرد، از `py` استفاده کنید. مک/لینوکس: از `python3` و `pip3`.

---

## ۲. گرفتن کد و نصب

```bash
git clone https://github.com/titanali1/mahva.git
cd mahva
pip install -r requirements.txt
```

اگر `pip` اجازهٔ نصب نداد یا با خطای محیط مواجه شدید، در یک محیط مجازی نصب کنید (تمیزتر):

```bash
python -m venv .venv
source .venv/bin/activate        # ویندوز: .venv\Scripts\activate
pip install -r requirements.txt
```

یا نصب به‌شکل بستهٔ پایتون (دستور `mahva` را سراسری می‌سازد):

```bash
pip install -e ".[web,voice]"
```

---

## ۳. بررسی محیط

```bash
python -m mahva doctor
```

خروجی نمونه:

```
Mahva doctor
  ffmpeg : .../imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2
  python : 3.11.2  (linux)
  pillow : raqm=False freetype=True   (بدون raqm هم کار می‌کند: شکل‌دهی داخلی)
  تم‌ها   : midnight, sunset, forest, amber, paper, ink
  فونت‌ها: 4 خانواده — نمونه: dejavusans, … , vazirmatn
  موتور صدا:
    ✅ edge      ← صدای نورال فارسی، نیاز به اینترنت
    — espeak     ← آفلاین (اگر espeak-ng نصب باشد)
    ✅ silent    ← همیشه در دسترس
```

اگر `ffmpeg` خطا داد: یا `imageio-ffmpeg` را نصب کنید (`pip install imageio-ffmpeg`)
یا ffmpeg سیستم را نصب کنید (`sudo apt install ffmpeg` / `brew install ffmpeg`).

---

## ۴. اجرا

### الف) رابط وب (پیشنهادی)

```bash
python -m mahva serve --port 8000
# سپس در مرورگر: http://localhost:8000
```

گزینه‌ها:

```bash
python -m mahva serve --port 8080 --host 127.0.0.1     # فقط روی همین کامپیوتر
python -m mahva serve --work ./my-project              # محل ذخیرهٔ پروژه‌ها و فایل‌های موقت
python -m mahva serve --reload                         # برای توسعه (کد با هر تغییر ری‌استارت می‌شود)
```

در رابط وب: متن را بنویسید → تصاویر را با drag & drop رها کنید → روی هر فایل کلیک کنید تا
`@image نام-فایل.jpg` در متن درج شود → تنظیمات را انتخاب کنید → **ساخت ویدیو**.

معادل بدون دستور `mahva`:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

### ب) خط فرمان

```bash
python -m mahva render examples/demo-fa.md -o out/demo.mp4          # رندر کامل
python -m mahva render examples/article-fa.md --preset-size portrait # ریلز عمودی
python -m mahva preview examples/demo-fa.md -o card.png --scene 2    # پیش‌نمایش یک کارت
python -m mahva plan examples/demo-fa.md                             # زمان‌بندی و تخمین مدت
python -m mahva voices                                               # فهرست صداهای موجود
```

### ج) در کد پایتون

```python
from mahva import parse_script, render_project

project = parse_script(open("story.md", encoding="utf-8").read())
result = render_project(project)     # out/video.mp4
print(result.duration, result.path)
```

---

## ۵. داکر (اختیاری)

اگر نمی‌خواهید چیزی روی سیستم نصب کنید:

```bash
docker build -t mahva .
docker run --rm -p 8000:8000 -v "$PWD/out:/app/out" mahva
# سپس http://localhost:8000
```

برای رندر از خط فرمان:

```bash
docker run --rm -v "$PWD:/data" mahva \
  python -m mahva render /data/examples/demo-fa.md -o /data/out/demo.mp4
```

---

## ۶. صداگذاری (اختیاری)

مهوا خودش بهترین موتور موجود را انتخاب می‌کند. برای انتخاب دستی:

| هدف | کار |
|---|---|
| صدای نورال فارسی (بهترین کیفیت، اینترنت) | `pip install edge-tts` — صداهای `fa-IR-DilaraNeural` (زن) و `fa-IR-FaridNeural` (مرد) |
| صدای آفلاین لینوکس | `sudo apt install espeak-ng` |
| صدای نورال کاملاً آفلاین | [Piper](https://github.com/rhasspy/piper) را نصب و `MAHVA_PIPER_MODEL=/path/model.onnx` را تنظیم کنید |
| صدای ویندوز | بدون نصب اضافه: موتور `sapi` |
| صدای مک | بدون نصب اضافه: موتور `say` |
| بدون صدا | `--no-voice` یا `@voice_engine silent` |

```bash
python -m mahva render story.md --engine edge --voice fa-IR-DilaraNeural --rate +10%
python -m mahva render story.md --no-voice                     # بی‌صدا، سریع‌تر
python -m mahva render story.md --music bgm.mp3 --music-volume 0.06
```

---

## ۷. عیب‌یابی

| مشکل | راه‌حل |
|---|---|
| `ffmpeg پیدا نشد` | `pip install imageio-ffmpeg` یا نصب ffmpeg سیستم |
| متن فارسی به‌صورت مربع/جدا نمایش داده می‌شود | `fonts.py` باید Vazirmatn را در `assets/fonts` ببیند؛ `python -m mahva doctor` را چک کنید. برای فونت دلخواه: `--font "نام فونت"` |
| ویدیو صدا ندارد | اینترنت را چک کنید (`python -m mahva voices`)؛ یا `espeak-ng` نصب کنید؛ خروجی گزارش با خطای TTS را نشان می‌دهد |
| رندر خیلی کند است | `--quality fast --preset-size hd` یا `--preview` برای تست؛ رزولوشن نصف، سرعت چند برابر |
| `pip: command not found` | از `python -m pip install -r requirements.txt` استفاده کنید |
| خطای `Address already in use` | پورت دیگری بدهید: `--port 8010` |
| کار نیمه‌کاره ماند | فقط دوباره `render` را اجرا کنید؛ از حافظهٔ موقت ادامه می‌دهد (برای شروع از صفر: `--force`) |

---

## ۸. اجرای تست‌ها

```bash
pip install pytest
python -m pytest -q
```

هشت تست اجرا می‌شود؛ آخرین تست یک ویدیوی کوچک را واقعاً با ffmpeg رندر می‌کند تا کل
زنجیره (کارت → کلیپ → کراس‌فید → MP4) بررسی شود.
