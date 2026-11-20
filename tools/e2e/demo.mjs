// Drives the full demo scenario through the UI: failure -> incident -> trace -> investigate -> close.
import { chromium } from "playwright-core";

const BASE = "http://127.0.0.1:5173";
const OUT = process.argv[2] ?? ".";
const browser = await chromium.launch({ channel: "msedge", headless: true });
const errors = [];
const step = (m) => console.log("step:", m);

async function session(email, pw) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  page.on("pageerror", (e) => errors.push(`${email} pageerror ${e.message}`));
  page.on("response", (r) => { if (r.url().includes("/api/") && r.status() >= 500) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(BASE);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(pw);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("Dashboard", { exact: true }).first().waitFor();
  return page;
}
async function pick(page, label, optionText) {
  await page.getByRole("textbox", { name: label }).click();
  await page.getByRole("option", { name: optionText }).first().click();
}
async function toast(page, text) {
  await page.getByText(text).first().waitFor({ timeout: 10000 });
}

// 1. Admin simulates a refrigeration failure on SH004
const admin = await session("admin@pharmatrace.local", "admin123");
await pick(admin, "Shipment", /SH004/);
await admin.getByRole("button", { name: "Simulate failure" }).click();
await toast(admin, "Refrigeration failure started");
step("failure simulated on SH004");
await admin.waitForTimeout(40000);   // 14 readings at 2.5 s

// 2. The incident exists, with readings and affected batches
const qm = await session("qm@pharmatrace.local", "qm123");
await qm.goto(BASE + "/incidents");
await qm.getByRole("row", { name: /INC0003/ }).click();
await qm.getByText("Incident INC0003").waitFor();
const batches = await qm.locator("table").nth(0).innerText();
step(`incident INC0003 opened; affected batches table: ${batches.split("\n").filter((l) => /^B0/.test(l)).join(" ")}`);
await qm.screenshot({ path: `${OUT}/demo_1_incident.png`, fullPage: true });

// 3. QM assigns the investigator
await pick(qm, "Assign investigator", /Meera Nair/);
await qm.getByRole("button", { name: "Assign" }).click();
await toast(qm, "Investigator assigned");
step("investigator assigned");

// 4. Investigator assesses batches, puts one on hold, adds an action, records findings
const inv = await session("investigator@pharmatrace.local", "investigator123");
await inv.goto(qm.url());
await inv.getByText("Incident INC0003").waitFor();
const rows = inv.locator("tr", { has: inv.getByRole("button", { name: "Assess" }) });
const n = await rows.count();
for (let i = 0; i < n; i++) {
  await rows.nth(i).getByRole("button", { name: "Assess" }).click();
  await pick(inv, "Assessment", "Assessed");
  await inv.getByLabel("Note").fill("Peak exposure reviewed against stability data");
  await inv.getByRole("dialog").getByRole("button", { name: "Save", exact: true }).click();
  await toast(inv, "Assessment saved");
  await inv.waitForTimeout(500);
}
step(`${n} batches assessed`);
await rows.first().getByRole("button", { name: "Decision" }).click();
await pick(inv, "New status", "On hold");
await inv.getByLabel("Reason").fill("Hold pending quality review");
await inv.getByRole("button", { name: "Save decision" }).click();
await toast(inv, "Decision recorded");
step("first batch put on hold");
await inv.getByRole("button", { name: "Add", exact: true }).click();
await inv.getByLabel("Action required").fill("Inspect compressor of KA05CD5678");
await pick(inv, "Responsible", /Ravi Kumar/);
await inv.getByRole("dialog").getByRole("button", { name: "Add", exact: true }).click();
await toast(inv, "Corrective action added");
await inv.getByPlaceholder("Findings").fill("Compressor tripped for about 25 minutes near Tumakuru.");
await inv.getByRole("button", { name: "Complete investigation" }).click();
await toast(inv, "Investigation updated");
step("action added, investigation completed");

// 5. Closing too early is refused by the database (action still pending)
await qm.reload();
await qm.getByRole("button", { name: "Mark resolved" }).click();
await qm.getByRole("dialog").getByLabel("Reason").fill("Investigation complete");
await qm.getByRole("button", { name: "Confirm" }).click();
await toast(qm, "Incident resolved");
await qm.getByRole("button", { name: "Close incident" }).click();
await qm.getByRole("dialog").getByLabel("Reason").fill("Attempt close");
await qm.getByRole("button", { name: "Confirm" }).click();
await toast(qm, "corrective actions that are not finished");
step("early close refused: " + (await qm.getByText("corrective actions that are not finished").first().innerText()));
await qm.keyboard.press("Escape");

// 6. Operator completes the action; QM releases the batch and closes the incident
const op = await session("operator@pharmatrace.local", "operator123");
await op.goto(qm.url());
await op.getByText("Corrective actions").waitFor();
const statusSelect = op.locator("table").last().locator("input:not([type=hidden])").last();
await statusSelect.click();
await op.getByRole("option", { name: "Completed" }).click();
await toast(op, "Corrective action updated");
step("operator completed the action");

await qm.reload();
await qm.getByRole("button", { name: "Decision" }).first().click();
await pick(qm, "New status", "Released");
await qm.getByLabel("Reason").fill("Released after quality review");
await qm.getByRole("button", { name: "Save decision" }).click();
await toast(qm, "Decision recorded");
await qm.getByRole("button", { name: "Close incident" }).click();
await qm.getByRole("dialog").getByLabel("Reason").fill("All actions done, batches assessed");
await qm.getByRole("button", { name: "Confirm" }).click();
await toast(qm, "Incident closed");
await qm.waitForTimeout(1500);
await qm.screenshot({ path: `${OUT}/demo_2_closed.png`, fullPage: true });
step("incident closed: status badge = " + (await qm.locator("h2 + div").first().innerText()).split("\n")[0]);

console.log(errors.length ? "ERRORS:\n" + errors.join("\n") : "demo flow clean");
await browser.close();
