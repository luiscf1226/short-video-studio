// bible-devocional: el devocional del día de la app en producción
// (https://bible-ai-honduras.vercel.app/hoy), grabado en un teléfono.
//   node devocional.cjs <carpeta-de-trabajo>
const path = require("node:path");
const fs = require("node:fs");
const S = require("./estudio.cjs");

const APP = "https://bible-ai-honduras.vercel.app";
const OUT = path.resolve(__dirname, "..");

(async () => {
  const work = path.resolve(process.argv[2] ?? "/tmp/semana-47");
  fs.mkdirSync(work, { recursive: true });
  const browser = await S.launch();
  const { page, context } = await S.newPhone(browser);
  // Una vuelta antes para que fuentes e imágenes queden en caché.
  await page.goto(`${APP}/hoy`, { waitUntil: "networkidle" });
  await page.getByText("UNA PAUSA PARA HOY").waitFor({ timeout: 60_000 });
  await page.reload({ waitUntil: "networkidle" });
  await page.getByText("ORACIÓN FINAL").waitFor({ timeout: 60_000 });
  await page.addStyleTag({ content: "*:focus,*:focus-visible{outline:none!important}" });
  await page.waitForTimeout(1500);

  const clip = await S.record(page, path.join(work, "devocional-crudo.mp4"), async (p, mark) => {
    await p.waitForTimeout(4200); // versículo del día (debajo del gancho)
    mark("oracion");
    await S.scrollTextTo(p, "ORACIÓN INICIAL", { top: 70, ms: 1600 });
    await p.waitForTimeout(4200);
    mark("pausa");
    await S.scrollTextTo(p, "UNA PAUSA PARA HOY", { top: 70, ms: 1600 });
    await p.waitForTimeout(7000);
    mark("final");
    await S.scrollTextTo(p, "ORACIÓN FINAL", { top: 70, ms: 1600 });
    await p.waitForTimeout(4500);
  });
  await context.close();

  const hook = await S.renderPng(browser, S.hookHtml("Esto es lo primero que leo cada mañana.", { accent: "#B87A4B" }), path.join(work, "dev-hook.png"));
  const chip1 = await S.renderPng(browser, S.chipHtml("Versículo + oración", { y: 1560 }), path.join(work, "dev-chip1.png"));
  const chip2 = await S.renderPng(browser, S.chipHtml("Una reflexión para hoy", { y: 1560 }), path.join(work, "dev-chip2.png"));
  const close = await S.renderPng(browser, S.closeHtml(["Descarga la app."], { sub: "3C · Biblia y Devocional" }), path.join(work, "dev-cierre.png"));
  await browser.close();

  const m = clip.marks;
  const out = path.join(OUT, "bible-devocional.mp4");
  S.compose({
    segments: [{ file: clip.file, from: 0.2, to: clip.seconds - 0.1 }],
    overlays: [
      { png: hook, from: 0, to: 4.0 },
      { png: chip1, from: m.oracion + 0.3, to: m.oracion + 3.6 },
      { png: chip2, from: m.pausa + 0.3, to: m.pausa + 4.0 },
    ],
    close: { png: close, seconds: 3.2 },
    out,
  });
  S.frame(out, 1.8, path.join(OUT, "frames", "bible-devocional.png"));
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
