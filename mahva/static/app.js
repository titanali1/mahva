/* Mahva web UI — vanilla JS, no build step. */
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const FA_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];
  const fa = (value) => String(value).replace(/\d/g, (d) => FA_DIGITS[+d]);
  const seconds = (value) => {
    const total = Math.max(0, Math.round(value));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return m ? `${fa(m)}:${fa(String(s).padStart(2, "0"))}` : `${fa(s)} ثانیه`;
  };

  let META = null;
  let currentJob = null;
  let pollTimer = null;
  let images = [];           // {file, name}
  let musicFile = null;

  /* ------------------------------------------------------------------ meta */
  async function loadMeta() {
    META = await (await fetch("/api/meta")).json();
    const presetSel = $("#preset-size");
    presetSel.innerHTML = META.presets
      .map((p) => `<option value="${p.key}">${fa(p.width)}×${fa(p.height)} — ${p.key}</option>`)
      .join("");
    presetSel.value = "landscape";

    $("#theme").innerHTML = META.themes.map((t) => `<option value="${t.key}">${t.label}</option>`).join("");
    $("#transition").innerHTML = META.transitions.map((t) => `<option value="${t}">${t}</option>`).join("");
    $("#font").innerHTML = META.fonts.map((f) => `<option value="${f}">${f}</option>`).join("");
    if (META.fonts.includes("vazirmatn")) $("#font").value = "vazirmatn";
    $("#quality").value = "balanced";

    const engines = Object.entries(META.engines).filter(([k, v]) => v).map(([k]) => k);
    const auto = engines.includes("edge") ? "auto" : (engines.find((e) => e !== "silent") || "silent");
    $("#voice-engine").innerHTML = [
      `<option value="auto">خودکار (${auto})</option>`,
      ...engines.map((e) => `<option value="${e}">${e}</option>`),
    ].join("");

    updateVoices("fa");
    $("#example-select").innerHTML += META.examples
      .map((e) => `<option value="${e.name}">${e.label}</option>`)
      .join("");

    const chips = [];
    chips.push(`<span class="chip ok">ffmpeg آماده</span>`);
    chips.push(`<span class="chip ok">${fa(META.fonts.length)} فونت</span>`);
    const voiceOk = engines.filter((e) => e !== "silent");
    chips.push(voiceOk.length
      ? `<span class="chip ok">صدا: ${voiceOk.join(" / ")}</span>`
      : `<span class="chip off">بدون موتور صدا — ویدیو بی‌صدا ساخته می‌شود</span>`);
    $("#status-chips").innerHTML = chips.join("");

    $("#script").value = localStorage.getItem("mahva.script") || META.sample;
  }

  function updateVoices(lang) {
    const list = (META.voices[lang] || []).filter((v) => v.engine === "edge");
    $("#voice").innerHTML = [
      `<option value="">پیش‌فرض</option>`,
      ...list.map((v) => `<option value="${v.voice}">${v.label}</option>`),
    ].join("");
  }

  /* ---------------------------------------------------------------- editor */
  function insertAtCursor(text) {
    const area = $("#script");
    const start = area.selectionStart;
    const end = area.selectionEnd;
    area.value = area.value.slice(0, start) + text + area.value.slice(end);
    area.selectionStart = area.selectionEnd = start + text.length;
    area.focus();
    onScriptChanged();
  }

  let statsDebounce = null;
  function onScriptChanged() {
    localStorage.setItem("mahva.script", $("#script").value);
    clearTimeout(statsDebounce);
    statsDebounce = setTimeout(refreshStats, 550);
  }

  async function refreshStats() {
    try {
      const res = await fetch("/api/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script: $("#script").value, settings: readSettings() }),
      });
      const data = await res.json();
      const withImages = data.scenes.filter((s) => s.image).length;
      $("#stats").innerHTML = `
        <div class="stat">صحنه‌ها: <b>${fa(data.scenes.length)}</b></div>
        <div class="stat">تصویردار: <b>${fa(withImages)}</b></div>
        <div class="stat">برآورد مدت: <b>${seconds(data.estimated_seconds)}</b></div>
        <div class="stat">عنوان: <b>${data.title || "—"}</b></div>`;
    } catch (err) {
      $("#stats").innerHTML = `<div class="stat">خطا در خواندن متن</div>`;
    }
  }

  /* --------------------------------------------------------------- uploads */
  function addImages(files) {
    for (const file of files) {
      if (!file.type.startsWith("image/")) continue;
      images.push({ file, name: file.name });
    }
    renderFiles();
  }

  function renderFiles() {
    $("#file-list").innerHTML = images
      .map((img, i) => `
        <li>
          <img src="${URL.createObjectURL(img.file)}" alt="">
          <span>${img.name}</span>
          <button data-copy="${i}" title="درج در متن">＋</button>
          <button data-remove="${i}" title="حذف">✕</button>
        </li>`)
      .join("");
    $("#file-list").querySelectorAll("[data-copy]").forEach((btn) => {
      btn.onclick = () => insertAtCursor(`@image ${images[+btn.dataset.copy].name}\n`);
    });
    $("#file-list").querySelectorAll("[data-remove]").forEach((btn) => {
      btn.onclick = () => { images.splice(+btn.dataset.remove, 1); renderFiles(); };
    });
  }

  /* -------------------------------------------------------------- settings */
  function readSettings() {
    const preset = META.presets.find((p) => p.key === $("#preset-size").value) || META.presets[0];
    return {
      size: [preset.width, preset.height],
      fps: +$("#fps").value,
      theme: $("#theme").value,
      font: $("#font").value,
      quality: $("#quality").value,
      transition: $("#transition").value,
      transition_duration: +$("#transition-duration").value,
      kenburns: $("#kenburns").value,
      language: $("#language").value,
      voice_engine: $("#voice-engine").value,
      voice: $("#voice").value || null,
      rate: $("#rate").value,
      voice_volume: +$("#voice-volume").value,
      music_volume: +$("#music-volume").value,
      scene_pad: +$("#scene-pad").value,
      min_scene: +$("#min-scene").value,
      max_scene: +$("#max-scene").value,
      out_name: $("#out-name").value || "video.mp4",
      no_voice: $("#no-voice").checked,
    };
  }

  /* -------------------------------------------------------------- previews */
  async function refreshPreviews(jobId, count = 6) {
    $("#previews").innerHTML = Array.from({ length: count }, () => `<div class="preview-card skeleton"></div>`).join("");
    for (let i = 0; i < count; i++) {
      const card = $("#previews").children[i];
      try {
        const res = await fetch(`/api/jobs/${jobId}/poster?scene=${i + 1}&scale=0.3`);
        if (!res.ok) throw new Error("no scene");
        const blob = await res.blob();
        card.classList.remove("skeleton");
        card.innerHTML = `<img src="${URL.createObjectURL(blob)}" alt=""><div class="cap">صحنهٔ ${fa(i + 1)}</div>`;
      } catch (err) {
        card.remove();
      }
    }
  }

  /* ----------------------------------------------------------------- render */
  async function startRender() {
    const script = $("#script").value.trim();
    if (!script) { alert("اول متن سِناوریو را بنویسید."); return; }

    setBusy(true);
    $("#result").hidden = true;
    const form = new FormData();
    form.append("script", script);
    form.append("settings", JSON.stringify(readSettings()));
    images.forEach((img) => form.append("images", img.file, img.name));
    if (musicFile) form.append("music", musicFile, musicFile.name);

    const res = await fetch("/api/render", { method: "POST", body: form });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }));
      alert("خطا: " + (detail.detail || res.statusText));
      setBusy(false);
      return;
    }
    const data = await res.json();
    currentJob = data.job.id;
    $("#log").textContent = "";
    poll();
    refreshPreviews(currentJob, 4);
  }

  function poll() {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(async () => {
      if (!currentJob) return;
      const res = await fetch(`/api/jobs/${currentJob}`);
      const job = await res.json();
      $("#bar").style.width = `${(job.progress * 100).toFixed(1)}%`;
      $("#progress-label").textContent = `${job.step} · ${fa((job.progress * 100).toFixed(0))}٪`;
      $("#log").textContent = job.logs.join("\n");
      $("#log").scrollTop = $("#log").scrollHeight;

      if (job.status === "done") {
        setBusy(false);
        const video = $("#video");
        video.src = job.output.url + "?t=" + Date.now();
        $("#download").href = job.output.url;
        $("#result").hidden = false;
        $("#result-info").textContent = `${job.output.name} · ${fa((job.output.size / 1e6).toFixed(1))} مگابایت · ${seconds(job.plan?.duration || 0)}`;
        $("#progress-label").textContent = "✅ ویدیو آماده شد";
        return;
      }
      if (job.status === "error" || job.status === "cancelled") {
        setBusy(false);
        $("#progress-label").textContent = job.status === "error" ? "❌ خطا — گزارش را ببینید" : "لغو شد";
        return;
      }
      poll();
    }, 900);
  }

  function setBusy(busy) {
    $("#btn-render").disabled = busy;
    $("#btn-cancel").style.display = busy ? "block" : "none";
  }

  async function cancelRender() {
    if (!currentJob) return;
    await fetch(`/api/jobs/${currentJob}/cancel`, { method: "POST" });
  }

  /* ------------------------------------------------------------------ init */
  function wire() {
    $("#script").addEventListener("input", onScriptChanged);
    $("#btn-sample").onclick = () => {
      $("#script").value = META.sample;
      onScriptChanged();
    };
    $("#example-select").onchange = async (e) => {
      if (!e.target.value) return;
      const res = await fetch(`/api/examples/${encodeURIComponent(e.target.value)}`);
      const data = await res.json();
      $("#script").value = data.text;
      onScriptChanged();
      e.target.value = "";
    };
    $("#btn-insert-scene").onclick = () => insertAtCursor("\n## عنوان صحنه\n\nمتن این بخش…\n");

    const dropzone = $("#dropzone");
    dropzone.onclick = () => $("#file-input").click();
    $("#file-input").onchange = (e) => addImages(e.target.files);
    ["dragenter", "dragover"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("drag"); }));
    ["dragleave", "drop"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("drag"); }));
    dropzone.addEventListener("drop", (e) => addImages(e.dataTransfer.files));

    $("#music-input").onchange = (e) => {
      musicFile = e.target.files[0] || null;
      $("#music-name").textContent = musicFile ? musicFile.name : "انتخاب نشده";
    };

    $("#language").onchange = (e) => updateVoices(e.target.value);
    $("#no-voice").onchange = (e) => {
      $("#voice-engine").disabled = e.target.checked;
      $("#voice").disabled = e.target.checked;
    };
    ["#theme", "#font", "#preset-size", "#transition", "#transition-duration",
     "#kenburns", "#quality", "#fps", "#min-scene", "#max-scene",
     "#scene-pad", "#language"].forEach((sel) => { const el = $(sel); if (el) el.addEventListener("change", refreshStats); });

    $("#btn-render").onclick = startRender;
    $("#btn-cancel").onclick = cancelRender;
  }

  window.addEventListener("beforeunload", (e) => {
    if ($("#btn-render").disabled) { e.preventDefault(); e.returnValue = ""; }
  });

  loadMeta().then(() => { wire(); refreshStats(); });
})();
