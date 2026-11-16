// Graba una app real en un navegador con tamaño de teléfono y arma el video
// vertical (1080×1920) con el gancho arriba y una tarjeta de cierre.
//
// No dibuja pantallas: lo que se ve es la app abierta con Playwright. Los
// textos que se agregan (gancho, rótulos de paso y cierre) se dibujan aparte
// en HTML y se ponen encima con ffmpeg.
//
// Requiere: Playwright con Chromium (require('playwright')) y ffmpeg/ffprobe.
const { chromium } = require("playwright");
const { spawn, execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const W = 1080;
const H = 1920;
const FPS = 30;
// Viewport de teléfono (405×720 pt) a 8/3 de densidad = 1080×1920 px reales.
const VIEWPORT = { width: 405, height: 720 };
const SCALE = W / VIEWPORT.width;

const sleep = (ms) => new Promise((ok) => setTimeout(ok, ms));

/** Círculo que marca cada toque: en un video de pantalla no se ve el dedo. */
const TAP_SCRIPT = () => {
  const show = (x, y) => {
    const dot = document.createElement("div");
    dot.style.cssText = `position:fixed;left:${x - 22}px;top:${y - 22}px;width:44px;height:44px;border-radius:50%;
      background:rgba(255,255,255,.55);border:3px solid rgba(20,20,20,.55);z-index:2147483647;pointer-events:none;
      transform:scale(.6);opacity:1;transition:transform .45s ease-out,opacity .45s ease-out;`;
    document.documentElement.appendChild(dot);
    requestAnimationFrame(() => {
      dot.style.transform = "scale(1.25)";
      dot.style.opacity = "0";
    });
    setTimeout(() => dot.remove(), 600);
  };
  window.addEventListener("pointerdown", (e) => show(e.clientX, e.clientY), true);
  window.__tapAt = show;
};

async function launch() {
  return chromium.launch();
}

async function newPhone(browser, { clockAt } = {}) {
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: SCALE,
    isMobile: true,
    hasTouch: false,
    locale: "es-HN",
    timezoneId: "America/Tegucigalpa",
    userAgent:
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
  });
  if (clockAt) await context.clock.install({ time: clockAt });
  await context.addInitScript(TAP_SCRIPT);
  const page = await context.newPage();
  return { context, page };
}

/**
 * Graba la página mientras corre `script(page, mark)`. Capturas seguidas por
 * CDP (salen a 1080 px de verdad) y luego un MP4 a 30 cuadros por segundo.
 * Devuelve { file, seconds, marks } con las marcas en segundos del clip.
 */
async function record(page, out, script) {
  const cdp = await page.context().newCDPSession(page);
  const frames = [];
  let capturing = true;
  const loop = (async () => {
    while (capturing) {
      const t0 = Date.now() / 1000;
      try {
        const { data } = await cdp.send("Page.captureScreenshot", { format: "jpeg", quality: 90, optimizeForSpeed: true });
        frames.push({ data, time: (t0 + Date.now() / 1000) / 2 });
      } catch {
        await sleep(20);
      }
    }
  })();
  await sleep(150);
  const started = Date.now() / 1000;
  const marks = {};
  await script(page, (name) => (marks[name] = Date.now() / 1000));
  const ended = Date.now() / 1000;
  capturing = false;
  await loop;
  await cdp.detach().catch(() => {});
  if (frames.length === 0) throw new Error("No se grabó ningún cuadro");

  const total = Math.round((ended - started) * FPS);
  const ff = spawn(
    "ffmpeg",
    ["-v", "error", "-y", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", String(FPS), "-i", "-",
      "-vf", `scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},format=yuv420p`,
      "-c:v", "libx264", "-crf", "16", "-preset", "medium", out],
    { stdio: ["pipe", "inherit", "inherit"] },
  );
  const done = new Promise((ok, fail) => ff.on("close", (c) => (c === 0 ? ok() : fail(new Error(`ffmpeg ${c}`)))));
  let i = 0;
  for (let n = 0; n < total; n++) {
    const t = started + n / FPS;
    while (i + 1 < frames.length && frames[i + 1].time <= t) i++;
    if (!ff.stdin.write(Buffer.from(frames[i].data, "base64"))) await new Promise((ok) => ff.stdin.once("drain", ok));
  }
  ff.stdin.end();
  await done;
  console.log(`  clip ${path.basename(out)}: ${(total / FPS).toFixed(1)} s, ${frames.length} capturas (${(frames.length / (ended - started)).toFixed(1)}/s)`);
  return { file: out, seconds: total / FPS, marks: Object.fromEntries(Object.entries(marks).map(([k, v]) => [k, v - started])) };
}

/** Toca un elemento como un dedo: marca el toque y hace clic. */
async function tap(page, locator, { pause = 350 } = {}) {
  await locator.scrollIntoViewIfNeeded().catch(() => {});
  const box = await locator.boundingBox();
  if (box) {
    await page.evaluate(({ x, y }) => window.__tapAt?.(x, y), { x: box.x + box.width / 2, y: box.y + box.height / 2 });
  }
  await page.waitForTimeout(120);
  await locator.click({ noWaitAfter: true });
  await page.waitForTimeout(pause);
}

/** Baja el contenedor con scroll que contiene `selectorText` hasta `toY` en `ms`, suave. */
async function smoothScroll(page, { by, to, ms, within }) {
  await page.evaluate(
    async ({ by, to, ms, within }) => {
      const anchor = within ? [...document.querySelectorAll("div")].find((d) => d.innerText?.startsWith(within)) : document.body;
      let s = anchor;
      const scrollable = (el) => el && el.scrollHeight > el.clientHeight + 4 && getComputedStyle(el).overflowY !== "visible";
      const all = [...document.querySelectorAll("div")].filter(scrollable).sort((a, b) => b.clientHeight - a.clientHeight);
      while (s && !scrollable(s)) s = s.parentElement;
      s = s || all[0] || document.scrollingElement;
      const from = s.scrollTop;
      const target = to !== undefined ? to : from + by;
      const end = Math.max(0, Math.min(target, s.scrollHeight - s.clientHeight));
      const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
      await new Promise((ok) => {
        const t0 = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - t0) / ms);
          s.scrollTop = from + (end - from) * ease(t);
          t < 1 ? requestAnimationFrame(step) : ok();
        };
        requestAnimationFrame(step);
      });
    },
    { by, to, ms, within },
  );
}

/** Lleva un elemento (por texto) hasta `top` px del borde superior, suave. */
async function scrollTextTo(page, text, { top = 90, ms = 1800 } = {}) {
  await page.evaluate(
    async ({ text, top, ms }) => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let node = null;
      while (walker.nextNode()) if (walker.currentNode.nodeValue.trim().startsWith(text)) { node = walker.currentNode.parentElement; break; }
      if (!node) throw new Error(`No está en pantalla: ${text}`);
      let s = node.parentElement;
      const scrollable = (el) => el.scrollHeight > el.clientHeight + 4 && getComputedStyle(el).overflowY !== "visible";
      while (s && !scrollable(s)) s = s.parentElement;
      s = s || document.scrollingElement;
      const from = s.scrollTop;
      const delta = node.getBoundingClientRect().top - s.getBoundingClientRect().top - top;
      const end = Math.max(0, Math.min(from + delta, s.scrollHeight - s.clientHeight));
      const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
      await new Promise((ok) => {
        const t0 = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - t0) / ms);
          s.scrollTop = from + (end - from) * ease(t);
          t < 1 ? requestAnimationFrame(step) : ok();
        };
        requestAnimationFrame(step);
      });
    },
    { text, top, ms },
  );
}

// ---------- Textos encima del video (HTML → PNG transparente) ----------

const BASE_CSS = `
  html,body{margin:0;width:${W}px;height:${H}px;background:transparent;font-family:Inter,'DejaVu Sans',sans-serif;}
  .wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;}
`;

async function renderPng(browser, html, out) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.setContent(`<!doctype html><meta charset="utf-8"><style>${BASE_CSS}</style>${html}`);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: out, omitBackground: true });
  await page.close();
  return out;
}

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

/** Gancho: tarjeta grande arriba, legible en un teléfono. */
function hookHtml(text, { accent = "#111" } = {}) {
  return `<div class="wrap"><div style="margin-top:250px;width:920px;background:rgba(255,255,255,.97);border-radius:44px;
    padding:46px 54px;box-shadow:0 18px 60px rgba(0,0,0,.28);border:4px solid ${accent};">
    <div style="font-size:74px;line-height:1.12;font-weight:800;color:#111;letter-spacing:-1.2px;text-align:center">${esc(text)}</div>
  </div></div>`;
}

/** Rótulo de paso: pastilla oscura abajo, sobre la app. */
function chipHtml(text, { y = 1500 } = {}) {
  return `<div class="wrap"><div style="margin-top:${y}px;background:rgba(17,17,17,.88);color:#fff;border-radius:999px;
    padding:26px 48px;font-size:52px;font-weight:700;letter-spacing:-.5px;box-shadow:0 10px 40px rgba(0,0,0,.3)">${esc(text)}</div></div>`;
}

/** Cierre: velo sobre el último cuadro y la llamada a la acción. */
function closeHtml(lines, { bg = "rgba(255,255,255,.88)", color = "#111", sub = "", sizes = [] } = {}) {
  return `<div class="wrap" style="background:${bg};justify-content:center;">
    <div style="width:900px;text-align:center;color:${color}">
      ${lines.map((l, i) => `<div style="font-size:${sizes[i] ?? 84}px;line-height:1.12;font-weight:800;letter-spacing:-1.5px;margin:12px 0">${esc(l)}</div>`).join("")}
      ${sub ? `<div style="margin-top:44px;font-size:50px;font-weight:600;opacity:.75">${esc(sub)}</div>` : ""}
    </div></div>`;
}

// ---------- Montaje ----------

function probeSeconds(file) {
  return Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", file], { encoding: "utf8" }));
}

/**
 * Arma el video final.
 *  segments: [{ file, from, to, speed=1 }] cortes de los clips grabados, en orden.
 *  overlays: [{ png, from, to }] en segundos del video final (antes del cierre).
 *  close: { png, seconds } tarjeta de cierre sobre el último cuadro congelado.
 */
function compose({ segments, overlays, close, out }) {
  const args = ["-v", "error", "-y"];
  const parts = [];
  segments.forEach((s, i) => {
    args.push("-i", s.file);
    const speed = s.speed ?? 1;
    parts.push(`[${i}:v]trim=start=${s.from}:end=${s.to},setpts=(PTS-STARTPTS)/${speed},fps=${FPS},setsar=1[s${i}]`);
  });
  const nSeg = segments.length;
  let filter = parts.join(";") + ";" + segments.map((_, i) => `[s${i}]`).join("") + `concat=n=${nSeg}:v=1:a=0[body0]`;
  const bodySeconds = segments.reduce((sum, s) => sum + (s.to - s.from) / (s.speed ?? 1), 0);

  // Congela el último cuadro para el cierre.
  filter += `;[body0]tpad=stop_mode=clone:stop_duration=${close.seconds}[body]`;
  let last = "body";
  const inputs = [...overlays, { png: close.png, from: bodySeconds, to: bodySeconds + close.seconds, fade: 0.35 }];
  inputs.forEach((o, k) => {
    const idx = nSeg + k;
    args.push("-loop", "1", "-t", String(bodySeconds + close.seconds), "-i", o.png);
    const fade = o.fade ?? 0.25;
    filter += `;[${idx}:v]format=rgba,fade=t=in:st=${o.from}:d=${fade}:alpha=1,fade=t=out:st=${Math.max(o.from, o.to - fade)}:d=${fade}:alpha=1[o${k}]`;
    filter += `;[${last}][o${k}]overlay=0:0:enable='between(t,${o.from},${o.to})'[v${k}]`;
    last = `v${k}`;
  });
  const total = bodySeconds + close.seconds;
  // Pista de audio en silencio: algunas redes rechazan o silencian mal un MP4 sin audio.
  args.push("-f", "lavfi", "-t", String(total), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100");
  const audioIdx = nSeg + inputs.length;
  filter += `;[${last}]format=yuv420p[out]`;
  args.push("-filter_complex", filter, "-map", "[out]", "-map", `${audioIdx}:a`,
    "-t", String(total), "-r", String(FPS), "-c:v", "libx264", "-profile:v", "high", "-crf", "19", "-preset", "slow",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out);
  execFileSync("ffmpeg", args, { stdio: "inherit" });
  const seconds = probeSeconds(out);
  console.log(`  final ${out}: ${seconds.toFixed(2)} s`);
  return seconds;
}

/** Fotograma PNG del video final en el segundo `at`. */
function frame(video, at, out) {
  fs.mkdirSync(path.dirname(out), { recursive: true });
  execFileSync("ffmpeg", ["-v", "error", "-y", "-ss", String(at), "-i", video, "-frames:v", "1", out]);
  return out;
}

module.exports = {
  W, H, FPS, launch, newPhone, record, tap, smoothScroll, scrollTextTo, renderPng,
  hookHtml, chipHtml, closeHtml, compose, frame, probeSeconds, sleep,
};
