// Researcher: capture a REAL source page as B-roll (screenshot + smooth scrolling recording).
//
// Usage:
//   node tools/scripts/capture.mjs <url> broll/<project>/<name> [--highlight "exact text"]... [--no-scroll]
//        [--width 1920] [--height 1080] [--dark] [--wait 2000]
//
// Writes:
//   <name>.png        crisp 2x screenshot of the viewport, scrolled to the first highlight
//   <name>.full.png   full-page screenshot
//   <name>.mp4        smooth scroll from the top down to the highlight (unless --no-scroll)
//   <name>.json       source URL, final URL, page title, capture time, highlight boxes
//                     (as fractions of the screenshot, for zooms in the edit plan)
// Highlights only add a marker colour behind text that is really on the page; nothing is rewritten.

import { chromium } from "playwright-core";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error("Usage: node tools/scripts/capture.mjs <url> <out-prefix> [--highlight text]... [--no-scroll]");
  process.exit(1);
}
const [url, prefix] = args;
const opt = (name, def) => {
  const i = args.indexOf(`--${name}`);
  return i > -1 ? args[i + 1] : def;
};
const highlights = args.flatMap((a, i) => (a === "--highlight" ? [args[i + 1]] : []));
const W = Number(opt("width", 1920));
const H = Number(opt("height", 1080));
const wait = Number(opt("wait", 2000));
const scroll = !args.includes("--no-scroll");
const executablePath =
  process.env.CHROME_PATH ||
  ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/usr/bin/chromium", "/usr/bin/google-chrome",
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"].find((p) => fs.existsSync(p));

fs.mkdirSync(path.dirname(prefix), { recursive: true });
const browser = await chromium.launch({ executablePath, args: ["--hide-scrollbars"] });
const videoDir = fs.mkdtempSync(path.join(path.dirname(prefix), ".rec-"));

async function open(record) {
  const ctx = await browser.newContext({
    viewport: { width: W, height: H },
    deviceScaleFactor: record ? 1 : 2,
    colorScheme: args.includes("--dark") ? "dark" : "light",
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    ...(record ? { recordVideo: { dir: videoDir, size: { width: W, height: H } } } : {}),
  });
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  // Dismiss common cookie / consent banners so they don't cover the source.
  for (const label of ["Accept all", "Accept", "I agree", "Agree", "Allow all", "Got it", "OK"]) {
    const b = page.getByRole("button", { name: label, exact: true });
    if (await b.count().catch(() => 0)) {
      await b.first().click({ timeout: 1500 }).catch(() => {});
      break;
    }
  }
  await page.waitForTimeout(wait);
  // Mark the requested lines (real text on the page) with a highlighter colour.
  const found = await page.evaluate((needles) => {
    const out = [];
    for (const needle of needles) {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let node, hit = null;
      const low = needle.toLowerCase();
      while ((node = walker.nextNode())) {
        const i = node.textContent.toLowerCase().indexOf(low);
        if (i > -1 && node.parentElement && node.parentElement.offsetParent !== null) { hit = { node, i }; break; }
      }
      if (!hit) { out.push({ text: needle, found: false }); continue; }
      const range = document.createRange();
      range.setStart(hit.node, hit.i);
      range.setEnd(hit.node, hit.i + needle.length);
      const mark = document.createElement("mark");
      mark.style.cssText = "background:rgba(255,214,10,.55);color:inherit;border-radius:3px;padding:0 2px;box-shadow:0 0 0 2px rgba(255,214,10,.35)";
      range.surroundContents(mark);
      mark.dataset.ve = String(out.length);
      out.push({ text: needle, found: true });
    }
    return out;
  }, highlights);
  return { ctx, page, found };
}

// 1) Screenshots at 2x for 4K-sharp B-roll.
const shot = await open(false);
const meta = {
  url, final_url: shot.page.url(), title: await shot.page.title(), captured_at: new Date().toISOString(),
  viewport: [W, H], highlights: shot.found,
};
await shot.page.screenshot({ path: `${prefix}.full.png`, fullPage: true });
const first = shot.page.locator("mark[data-ve]").first();
if (await first.count()) {
  await first.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await shot.page.waitForTimeout(400);
}
await shot.page.screenshot({ path: `${prefix}.png` });
meta.boxes = await shot.page.evaluate(() =>
  [...document.querySelectorAll("mark[data-ve]")].map((m) => {
    const r = m.getBoundingClientRect();
    return { text: m.textContent, x: r.left / innerWidth, y: r.top / innerHeight, w: r.width / innerWidth, h: r.height / innerHeight };
  }),
);
await shot.ctx.close();

// 2) Smooth scrolling recording down to the first highlight.
if (scroll) {
  const rec = await open(true);
  const target = await rec.page.evaluate(() => {
    const m = document.querySelector("mark[data-ve]");
    return m ? Math.max(0, m.getBoundingClientRect().top + scrollY - innerHeight / 2)
             : Math.min(document.body.scrollHeight - innerHeight, innerHeight * 2);
  });
  await rec.page.waitForTimeout(800);
  await rec.page.evaluate(async (y) => {
    const start = scrollY, dur = Math.min(6000, 1200 + Math.abs(y - start) * 1.2), t0 = performance.now();
    await new Promise((res) => {
      const step = (now) => {
        const k = Math.min((now - t0) / dur, 1), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        scrollTo(0, start + (y - start) * e);
        k < 1 ? requestAnimationFrame(step) : res();
      };
      requestAnimationFrame(step);
    });
  }, target);
  await rec.page.waitForTimeout(1500);
  const video = rec.page.video();
  await rec.ctx.close();
  const webm = await video.path();
  // Drop the loading frames at the start (page load + wait) so the clip starts on the settled page.
  const trim = (wait + 300) / 1000;
  execFileSync("ffmpeg", ["-v", "error", "-y", "-ss", String(trim), "-i", webm, "-c:v", "libx264", "-crf", "16",
    "-pix_fmt", "yuv420p", "-r", "30", "-an", `${prefix}.mp4`]);
}
await browser.close();
fs.rmSync(videoDir, { recursive: true, force: true });
fs.writeFileSync(`${prefix}.json`, JSON.stringify(meta, null, 2));
const missing = meta.highlights.filter((h) => !h.found).map((h) => h.text);
console.log(`Captured ${meta.title} → ${prefix}.png${scroll ? `, ${prefix}.mp4` : ""}`);
if (missing.length) console.log(`Not found on the page (not highlighted): ${missing.join(" | ")}`);
