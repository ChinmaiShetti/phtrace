// Logs in as each role, opens every page, records console errors and failed requests, and screenshots.
import { chromium } from "playwright-core";

const BASE = "http://127.0.0.1:5173";
const OUT = process.argv[2] ?? ".";
const ROLES = [["admin", "admin123"], ["qm", "qm123"], ["investigator", "investigator123"], ["operator", "operator123"]];
const PAGES = ["/", "/shipments", "/shipments/2", "/shipments/6", "/batches", "/batches/1", "/products", "/monitoring",
  "/incidents", "/incidents/1", "/incidents/2", "/reports", "/admin"];

const browser = await chromium.launch({ channel: "msedge", headless: true });
let problems = 0;
for (const [role, pw] of ROLES) {
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
  page.on("response", (r) => { if (r.url().includes("/api/") && r.status() >= 500) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(BASE + "/");
  await page.getByLabel("Email").fill(`${role}@pharmatrace.local`);
  await page.getByLabel("Password").fill(pw);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("Dashboard", { exact: true }).first().waitFor();
  for (const p of PAGES) {
    errors.length = 0;
    await page.goto(BASE + p);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(600);
    const heading = await page.locator("h2").first().textContent().catch(() => "(no heading)");
    if (role === "qm" || role === "admin") await page.screenshot({ path: `${OUT}/${role}${p.replaceAll("/", "_") || "_home"}.png`, fullPage: true });
    const status = errors.length ? `PROBLEM ${errors.join(" | ")}` : "ok";
    if (errors.length) problems++;
    console.log(`${role.padEnd(13)} ${p.padEnd(14)} ${heading?.trim().padEnd(28)} ${status}`);
  }
  await page.close();
}
await browser.close();
console.log(problems ? `${problems} page(s) with problems` : "all pages clean");
