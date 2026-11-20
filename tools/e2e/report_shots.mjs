// Screenshots for the final report: every screen, forms with validation messages, role restrictions,
// and each step of the demo scenario. Needs the API (:8000) and Vite (:5173) on FRESHLY seeded data.
//   node report_shots.mjs <output dir>
import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = "http://127.0.0.1:5173";
const OUT = process.argv[2] ?? "shots";
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ channel: "msedge", headless: true });
const failures = [];
const log = (m) => console.log(m);

async function session(email, pw) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("pageerror", (e) => failures.push(`${email} pageerror ${e.message}`));
  await page.goto(BASE);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(pw);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("Dashboard", { exact: true }).first().waitFor();
  return page;
}
async function settle(page, ms = 700) {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(ms);
}
async function shot(page, name, full = true) {
  await settle(page);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: full });
  log(`  saved ${name}.png`);
}
async function step(name, fn) {
  try { await fn(); } catch (e) { failures.push(`${name}: ${e.message.split("\n")[0]}`); log(`  FAILED ${name}`); }
}
async function pick(page, label, option) {
  await page.getByRole("textbox", { name: label }).first().click();
  await page.getByRole("option", { name: option }).first().click();
}
const toast = (page, text) => page.getByText(text).first().waitFor({ timeout: 12000 });

// ---------------------------------------------------------------- A. login
await step("login", async () => {
  const p = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto(BASE);
  await shot(p, "01_login");
  await p.getByLabel("Email").fill("operator@pharmatrace.local");
  await p.getByLabel("Password").fill("wrong-password");
  await p.getByRole("button", { name: "Sign in" }).click();
  await p.getByText("Incorrect email or password").waitFor();
  await shot(p, "01b_login_wrong_password");
  await p.close();
});

// ---------------------------------------------------------------- B. screens (quality manager)
const qm = await session("qm@pharmatrace.local", "qm123");
const pages = [
  ["02_dashboard", "/"], ["03_shipments", "/shipments"], ["04_shipment_detail_SH002", "/shipments/2"],
  ["05_shipment_planned_SH006", "/shipments/6"], ["06_batches", "/batches"], ["07_batch_trace_B001", "/batches/1"],
  ["08_products", "/products"], ["09_incidents", "/incidents"], ["10_incident_closed_INC0001", "/incidents/1"],
  ["11_incident_investigating_INC0002", "/incidents/2"],
];
for (const [name, path] of pages) await step(name, async () => { await qm.goto(BASE + path); await shot(qm, name); });

await step("12_monitoring", async () => {
  await qm.goto(BASE + "/monitoring");
  await pick(qm, "Sensor", "TL-1001");
  await pick(qm, "Window", "24h");
  await shot(qm, "12_monitoring_chart", false);
});
await step("13_reports", async () => {
  await qm.goto(BASE + "/reports");
  const tabs = ["Incidents by type and severity", "Batches involved in incidents", "Vehicles with repeated incidents",
    "Corrective actions pending completion", "Batches expiring within 60 days", "Sensor data-quality problems"];
  for (const [i, t] of tabs.entries()) {
    await qm.getByRole("tab", { name: t }).click();
    await shot(qm, `13${String.fromCharCode(97 + i)}_report_${t.split(" ")[0].toLowerCase()}`, false);
  }
});
await step("14_admin", async () => {
  await qm.goto(BASE + "/admin");
  for (const [i, t] of ["Facilities", "Vehicles", "Sensors", "Staff", "Audit log"].entries()) {
    await qm.getByRole("tab", { name: t }).click();
    await shot(qm, `14${String.fromCharCode(97 + i)}_admin_${t.split(" ")[0].toLowerCase()}`);
  }
});

// ---------------------------------------------------------------- C. forms and validation (operator)
const op = await session("operator@pharmatrace.local", "operator123");
await step("15_form_shipment", async () => {
  await op.goto(BASE + "/shipments");
  await op.getByRole("button", { name: "New shipment" }).click();
  await op.getByRole("button", { name: "Create shipment" }).click();
  await op.getByText("Destination is required").waitFor();
  await shot(op, "15_form_new_shipment_validation", false);
  await op.keyboard.press("Escape");
});
await step("16_form_batch", async () => {
  await op.goto(BASE + "/batches");
  await op.getByRole("button", { name: "Register batch" }).click();
  const dlg = op.getByRole("dialog");
  await dlg.getByLabel("Batch number").fill("B 13!");
  await dlg.getByLabel("Manufactured").fill("2026-05-01");
  await dlg.getByLabel("Expires").fill("2026-04-01");
  await dlg.getByRole("button", { name: "Register" }).click();
  await op.getByText("Must be after manufacturing date").waitFor();
  await shot(op, "16_form_register_batch_validation", false);
  await op.keyboard.press("Escape");
});
await step("17_form_product", async () => {
  await op.goto(BASE + "/products");
  await op.getByRole("button", { name: "Register product" }).click();
  const dlg = op.getByRole("dialog");
  await dlg.getByLabel("Product name").fill("Test Serum");
  await dlg.getByLabel("Min °C").fill("8");
  await dlg.getByLabel("Max °C").fill("2");
  await dlg.getByRole("button", { name: "Save" }).click();
  await op.getByText("Maximum must be above minimum").waitFor();
  await shot(op, "17_form_new_product_validation", false);
  await op.keyboard.press("Escape");
});
await step("18_form_facility", async () => {
  await op.goto(BASE + "/admin");
  await op.getByRole("button", { name: "Add" }).first().click();
  const dlg = op.getByRole("dialog");
  await dlg.getByLabel("Name").fill("Test Clinic");
  await dlg.getByLabel("PIN code").fill("012345");
  await dlg.getByRole("button", { name: "Save" }).click();
  await op.getByText("Six digits, not starting with 0").waitFor();
  await shot(op, "18_form_facility_validation", false);
  await op.keyboard.press("Escape");
});

// ---------------------------------------------------------------- D. role restrictions
await step("19_roles", async () => {
  await op.goto(BASE + "/batches/1");
  await shot(op, "19a_role_operator_batch_no_decision_button", false);
  await op.goto(BASE + "/admin");
  await shot(op, "19b_role_operator_admin_no_audit_tab", false);
  const inv = await session("investigator@pharmatrace.local", "investigator123");
  await inv.goto(BASE + "/batches/1");
  await inv.getByRole("button", { name: "Record decision" }).click();
  await inv.getByRole("textbox", { name: "New status" }).click();
  await shot(inv, "19c_role_investigator_only_allowed_transitions", false);
  await inv.close();
});

// ---------------------------------------------------------------- E. demo scenario, step by step
const admin = await session("admin@pharmatrace.local", "admin123");
await step("D01_simulate", async () => {
  await pick(admin, "Shipment", /SH004/);
  await shot(admin, "D01_dashboard_before_failure", false);
  await admin.getByRole("button", { name: "Simulate failure" }).click();
  await toast(admin, "Refrigeration failure started");
  await shot(admin, "D02_simulation_started", false);
  await admin.waitForTimeout(40000);
});
const inv = await session("investigator@pharmatrace.local", "investigator123");
let incidentUrl = "";
await step("D03_incident", async () => {
  await qm.goto(BASE + "/incidents");
  await shot(qm, "D03_incidents_list_new_INC0003");
  await qm.getByRole("row", { name: /INC0003/ }).click();
  await qm.getByText("Incident INC0003").waitFor();
  incidentUrl = qm.url();
  await shot(qm, "D04_incident_raised_automatically");
});
await step("D05_assign", async () => {
  await pick(qm, "Assign investigator", /Meera Nair/);
  await qm.getByRole("button", { name: "Assign" }).click();
  await toast(qm, "Investigator assigned");
  await shot(qm, "D05_investigator_assigned");
});
await step("D06_investigate", async () => {
  await inv.goto(incidentUrl);
  await inv.getByText("Incident INC0003").waitFor();
  const rows = inv.locator("tr", { has: inv.getByRole("button", { name: "Assess" }) });
  const n = await rows.count();
  for (let i = 0; i < n; i++) {
    await rows.nth(i).getByRole("button", { name: "Assess" }).click();
    await pick(inv, "Assessment", "Assessed");
    await inv.getByLabel("Note").fill("Peak exposure reviewed against stability data");
    await inv.getByRole("dialog").getByRole("button", { name: "Save", exact: true }).click();
    await toast(inv, "Assessment saved");
    await inv.waitForTimeout(400);
  }
  await rows.first().getByRole("button", { name: "Decision" }).click();
  await pick(inv, "New status", "On hold");
  await inv.getByLabel("Reason").fill("Hold pending quality review");
  await inv.getByRole("button", { name: "Save decision" }).click();
  await toast(inv, "Decision recorded");
  await inv.getByRole("button", { name: "Add", exact: true }).click();
  await inv.getByLabel("Action required").fill("Inspect compressor of KA05CD5678");
  await pick(inv, "Responsible", /Ravi Kumar/);
  await inv.getByRole("dialog").getByRole("button", { name: "Add", exact: true }).click();
  await toast(inv, "Corrective action added");
  await inv.getByPlaceholder("Findings").fill("Compressor tripped for about 25 minutes near Tumakuru.");
  await inv.getByRole("button", { name: "Complete investigation" }).click();
  await toast(inv, "Investigation updated");
  await shot(inv, "D06_investigation_recorded");
});
await step("D07_early_close", async () => {
  await qm.reload();
  await qm.getByRole("button", { name: "Mark resolved" }).click();
  await qm.getByRole("dialog").getByLabel("Reason").fill("Investigation complete");
  await qm.getByRole("button", { name: "Confirm" }).click();
  await toast(qm, "Incident resolved");
  await qm.getByRole("button", { name: "Close incident" }).click();
  await qm.getByRole("dialog").getByLabel("Reason").fill("Attempt close");
  await qm.getByRole("button", { name: "Confirm" }).click();
  await toast(qm, "corrective actions that are not finished");
  await shot(qm, "D07_close_refused_by_database", false);
  await qm.keyboard.press("Escape");
});
await step("D08_operator_action", async () => {
  await op.goto(incidentUrl);
  await op.getByText("Corrective actions").waitFor();
  await op.locator("table").last().locator("input:not([type=hidden])").last().click();
  await op.getByRole("option", { name: "Completed" }).click();
  await toast(op, "Corrective action updated");
  await shot(op, "D08_operator_completed_action", false);
});
await step("D09_close", async () => {
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
  await shot(qm, "D09_incident_closed");
});
await step("D10_trace", async () => {
  await qm.goto(BASE + "/batches");
  await qm.getByRole("row", { name: /B002/ }).click();
  await qm.getByText("Batch B002").waitFor();
  await shot(qm, "D10_batch_trace_after_decisions");
  await qm.goto(BASE + "/shipments/4");
  await shot(qm, "D11_shipment_timeline_with_incident");
  await qm.goto(BASE + "/admin");
  await qm.getByRole("tab", { name: "Audit log" }).click();
  await shot(qm, "D12_audit_log_after_demo", false);
  await qm.goto(BASE + "/");
  await shot(qm, "D13_dashboard_after_demo");
});

await browser.close();
console.log(failures.length ? `FAILURES:\n${failures.join("\n")}` : "all screenshots captured");
