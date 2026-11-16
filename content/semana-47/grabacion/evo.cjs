// evo-mascota: Evo AI Coach (luiscf1226/evo-ai-mvp) exportado para web con
// `npx expo export -p web`, contra un backend Convex local con datos de prueba.
//   EVO_DIR=/ruta/a/evo-ai-mvp EVO_WEB=http://localhost:8090 node evo.cjs <carpeta-de-trabajo>
//
// Se graba la app de verdad: el onboarding donde se elige el compañero (Orbit)
// y la forma Evo, el plan del día, completar un hábito y la subida de nivel.
// El backend local no tiene proveedor de correo, así que la cuenta de prueba
// se crea con la acción de registro y se marca el correo como verificado con
// una mutación interna que solo existe en esa copia local (ver LEEME.md).
// Para llegar a la subida de nivel sin esperar días, con el rótulo «Unos días
// después…» ya en pantalla la XP de la cuenta de prueba sube de 0 a 85 en
// pasos de 5 y la app actualiza el anillo en vivo (no se edita la imagen).
//
// Con EVO_PARTE1=<carpeta> se reusa la parte 1 ya grabada (evo-crudo-1.mp4 y
// evo-marcas.json de esa carpeta): el onboarding se hace igual, sin grabar,
// para llegar al mismo inicio en 0%.
const path = require("node:path");
const fs = require("node:fs");
const { execFileSync } = require("node:child_process");
const S = require("./estudio.cjs");

const EVO_DIR = process.env.EVO_DIR ?? "/home/user/evo-ai-mvp";
const WEB = process.env.EVO_WEB ?? "http://localhost:8090";
const BACKEND = process.env.EVO_CONVEX ?? "http://127.0.0.1:3210";
const OUT = path.resolve(__dirname, "..");
const PASSWORD = "VideoPrueba2026";
const GOAL = "Quiero tomar más agua y caminar 20 minutos al día.";

/** Cliente con la llave de admin del backend local: llama a las mutaciones internas de prueba. */
function adminClient() {
  const { ConvexHttpClient } = require(path.join(EVO_DIR, "node_modules/convex/dist/cjs/browser/index.js"));
  const env = fs.readFileSync(path.join(EVO_DIR, ".env.local"), "utf8");
  const key = env.match(/^CONVEX_SELF_HOSTED_ADMIN_KEY=(.+)$/m)?.[1]?.trim();
  if (!key) throw new Error("Falta CONVEX_SELF_HOSTED_ADMIN_KEY en .env.local de EVO_DIR");
  const client = new ConvexHttpClient(BACKEND);
  client.setAdminAuth(key);
  return client;
}

/** Parte 1: se crea la mascota (compañero Orbit + forma Evo) y el plan del día. */
async function parte1(p, mark) {
  await p.waitForTimeout(2600);
  await S.tap(p, p.getByText("Conocer a Evo"), { pause: 900 });
  mark("areas");
  await S.tap(p, p.getByText("Salud y bienestar"), { pause: 500 });
  await S.tap(p, p.getByText("Continuar"), { pause: 900 });
  mark("meta");
  const box = p.locator("textarea").first();
  await S.tap(p, box, { pause: 200 });
  await p.keyboard.type(GOAL, { delay: 32 });
  await p.waitForTimeout(500);
  await S.tap(p, p.getByText("Esto es lo que quiero"), { pause: 1200 });
  mark("companero");
  await p.getByText("Orbit Impulso").waitFor();
  await S.tap(p, p.getByText("Orbit Impulso"), { pause: 900 });
  await S.tap(p, p.getByText("Elegir este compañero"), { pause: 1100 });
  mark("forma");
  await p.getByText("Evo Cosmos").waitFor();
  await S.tap(p, p.getByText("Evo Cosmos"), { pause: 1300 });
  await S.tap(p, p.getByText("Crear mi primer plan"), { pause: 300 });
  await p.getByText("Activar mi plan").waitFor({ timeout: 60_000 });
  mark("plan");
  await p.waitForTimeout(1500);
  await S.scrollTextTo(p, "Tus tres primeras misiones", { top: 40, ms: 1300 });
  await p.waitForTimeout(1600);
  await S.tap(p, p.getByText("Activar mi plan"), { pause: 300 });
  await p.getByText("Tus pasos de hoy").waitFor({ timeout: 30_000 });
  mark("home");
  await p.waitForTimeout(3000);
}

const convexRun = (fn, args) =>
  execFileSync("npx", ["convex", "run", fn, JSON.stringify(args)], { cwd: EVO_DIR, encoding: "utf8" }).trim();

async function createTestAccount(email) {
  const { ConvexHttpClient } = require(path.join(EVO_DIR, "node_modules/convex/dist/cjs/browser/index.js"));
  const client = new ConvexHttpClient(BACKEND);
  try {
    await client.action("auth:signIn", { provider: "password", params: { email, password: PASSWORD, name: "Luis", flow: "signUp" } });
  } catch (e) {
    // Sin proveedor de correo el envío del código falla, pero la cuenta queda creada.
    if (!/email delivery is not configured/.test(e.message)) throw e;
  }
  convexRun("zzVideoLocal:verifyTestEmail", { email });
}

(async () => {
  const work = path.resolve(process.argv[2] ?? "/tmp/semana-47");
  fs.mkdirSync(work, { recursive: true });
  const email = `video-evo-${Date.now()}@evo-ai.test`;
  await createTestAccount(email);
  console.log(`  cuenta de prueba: ${email}`);

  const browser = await S.launch();
  const { page, context } = await S.newPhone(browser);
  await page.goto(`${WEB}/sign-in`, { waitUntil: "networkidle" });
  const inputs = page.locator("input");
  await inputs.nth(0).fill(email);
  await inputs.nth(1).fill(PASSWORD);
  await page.getByText("Entrar a mi espacio").click();
  await page.getByText("Conocer a Evo").waitFor({ timeout: 30_000 });
  await page.addStyleTag({ content: "*:focus,*:focus-visible{outline:none!important}" });
  await page.waitForTimeout(1500);

  let a;
  if (process.env.EVO_PARTE1) {
    const dir = path.resolve(process.env.EVO_PARTE1);
    const saved = JSON.parse(fs.readFileSync(path.join(dir, "evo-marcas.json"), "utf8"));
    await parte1(page, () => {});
    a = { file: path.join(dir, "evo-crudo-1.mp4"), seconds: saved.aSec, marks: saved.a };
    console.log(`  parte 1 reusada: ${a.file}`);
  } else {
    a = await S.record(page, path.join(work, "evo-crudo-1.mp4"), parte1);
  }
  await page.getByText("100 XP para avanzar").waitFor({ timeout: 30_000 });
  const admin = adminClient();

  // Parte 2: se cumple un hábito, sube de nivel y desbloquea una recompensa.
  const b = await S.record(page, path.join(work, "evo-crudo-2.mp4"), async (p, mark) => {
    // Mismo inicio en 0% con el que termina la parte 1. Primero entra el
    // rótulo y, ya con el rótulo en pantalla, la XP sube de 0 a 85.
    await p.waitForTimeout(500);
    mark("rotulo");
    await p.waitForTimeout(900);
    mark("xp0");
    for (let xp = 5; xp <= 85; xp += 5) {
      await admin.mutation("zzVideoLocal:setTestXp", { email, totalXp: xp });
      await p.waitForTimeout(60);
    }
    await p.getByText("15 XP para avanzar").waitFor({ timeout: 10_000 });
    mark("xp85");
    await p.waitForTimeout(1100);
    mark("tarea");
    await S.tap(p, p.getByRole("button", { name: /^Practica durante 20 minutos\. 20 min\. 20 XP$/ }), { pause: 900 });
    const complete = p.getByRole("button", { name: "Completar" });
    await complete.scrollIntoViewIfNeeded();
    await p.waitForTimeout(700);
    mark("completar");
    await S.tap(p, complete, { pause: 300 });
    await p.getByText("celebra contigo").first().waitFor({ timeout: 20_000 });
    mark("logrado");
    await p.waitForTimeout(1800);
    await S.smoothScroll(p, { to: 0, ms: 1300 });
    mark("nivel2");
    await p.waitForTimeout(2600);
    const tab = p.getByRole("tab", { name: /Progreso/ });
    if (await tab.count()) await S.tap(p, tab.first(), { pause: 300 });
    else await p.goto(`${WEB}/progress`, { waitUntil: "networkidle" });
    await p.getByText("TU EVOLUCIÓN", { exact: true }).waitFor();
    await p.waitForTimeout(700);
    mark("progreso");
    await S.tap(p, p.getByText("Recompensas", { exact: true }), { pause: 700 });
    await S.scrollTextTo(p, "Brillo de Enfoque", { top: 260, ms: 1300 });
    mark("recompensa");
    await p.waitForTimeout(3000);
  });
  await context.close();

  const hook = await S.renderPng(browser, S.hookHtml("Esta app te pone una mascota que crece cuando tú creces.", { accent: "#2BC3A0" }), path.join(work, "evo-hook.png"));
  const chips = {};
  for (const [k, t] of Object.entries({
    c1: "1 · Creas tu compañero",
    c2: "2 · Tu plan del día",
    c3: "Unos días después…",
    c4: "3 · Cumples un hábito",
    c5: "¡Sube a nivel 2!",
    c6: "Desbloquea Brillo de Enfoque",
  })) chips[k] = await S.renderPng(browser, S.chipHtml(t, { y: 1580 }), path.join(work, `evo-${k}.png`));
  const close = await S.renderPng(
    browser,
    S.closeHtml(["Búscala en el App Store:", "Evo AI Coach"], { sizes: [66, 112] }),
    path.join(work, "evo-cierre.png"),
  );
  await browser.close();
  fs.writeFileSync(path.join(work, "evo-marcas.json"), JSON.stringify({ a: a.marks, b: b.marks, aSec: a.seconds, bSec: b.seconds, parte1: a.file }, null, 2));

  // Montaje: se acortan las esperas (generar el plan) y se acelera la escritura.
  const A = a.marks;
  const B = b.marks;
  const segs = [
    { file: a.file, from: 0.1, to: A.meta, speed: 1.3 },
    { file: a.file, from: A.meta, to: A.companero, speed: 1.8 },
    { file: a.file, from: A.companero, to: A.plan + 0.2, speed: 1.5 },
    { file: a.file, from: A.plan + 0.2, to: A.home + 1.6, speed: 1.4 },
    { file: b.file, from: 0.2, to: B.progreso, speed: 1.3 },
    { file: b.file, from: B.progreso, to: b.seconds - 0.1, speed: 1.15 },
  ];
  // Tiempo de cada marca en el video final.
  const at = (segIndex, t) => {
    let acc = 0;
    for (let i = 0; i < segIndex; i++) acc += (segs[i].to - segs[i].from) / (segs[i].speed ?? 1);
    return acc + (t - segs[segIndex].from) / (segs[segIndex].speed ?? 1);
  };
  const overlays = [
    { png: hook, from: 0, to: 3.6 },
    { png: chips.c1, from: at(2, A.companero) + 0.1, to: at(2, A.plan) - 0.2 },
    { png: chips.c2, from: at(3, A.plan + 0.3), to: at(3, A.home) },
    { png: chips.c3, from: at(4, B.rotulo), to: at(4, B.xp85) + 0.7 },
    { png: chips.c4, from: at(4, B.tarea) + 0.4, to: at(4, B.logrado) },
    { png: chips.c5, from: at(4, B.nivel2), to: at(4, B.progreso) - 0.1 },
    { png: chips.c6, from: at(5, B.recompensa) - 0.2, to: at(5, b.seconds - 0.2) },
  ];
  const out = path.join(OUT, "evo-mascota.mp4");
  S.compose({ segments: segs, overlays, close: { png: close, seconds: 3.2 }, out });
  S.frame(out, 1.6, path.join(OUT, "frames", "evo-mascota.png"));
  console.log(`  cuenta de prueba usada: ${email}`);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
