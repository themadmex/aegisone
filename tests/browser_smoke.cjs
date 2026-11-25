const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const { createHmac, randomUUID } = require("node:crypto");
const { mkdirSync, writeFileSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { join } = require("node:path");
const { chromium } = require("playwright-core");
const { AxeBuilder } = require("@axe-core/playwright");

const root = process.env.AEGIS_BROWSER_URL || "http://localhost:58042";
assert(["localhost", "127.0.0.1"].includes(new URL(root).hostname), "Use an isolated local application");
const evidence = process.env.AEGIS_BROWSER_EVIDENCE || join(tmpdir(), "aegisone-verification");
mkdirSync(evidence, { recursive: true });
const outcomes = [];

function fixture(name) {
    const email = "browser-" + randomUUID() + "@example.invalid";
    const code = [
        "from apps.workspaces.services import provision_workspace",
        "from django.test.utils import override_settings",
        "with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):",
        "    _, token = provision_workspace(" + JSON.stringify(name) + ", " + JSON.stringify(email) + ")",
        "print(token)",
    ].join("\n");
    const python = process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python";
    const result = execFileSync(python, ["manage.py", "shell", "-c", code], {
        encoding: "utf8",
        env: { ...process.env, DJANGO_DEBUG: "1", DJANGO_DB_ROLE: "owner", DB_PORT: process.env.AEGIS_BROWSER_DB_PORT || "55492" },
    });
    const token = result.trim().split("\n").at(-1);
    assert.match(token, /^[A-Za-z0-9_-]{43}$/);
    return root + "/invite/" + token;
}

function totp(base32) {
    const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    let buffer = 0, bits = 0;
    const bytes = [];
    for (const character of base32.replace(/[\s=-]/g, "").toUpperCase()) {
        const offset = alphabet.indexOf(character);
        assert(offset >= 0);
        buffer = (buffer << 5) | offset;
        bits += 5;
        if (bits >= 8) {
            bits -= 8;
            bytes.push((buffer >> bits) & 255);
        }
    }
    const clock = Buffer.alloc(8);
    clock.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
    const hash = createHmac("sha1", Buffer.from(bytes)).update(clock).digest();
    return String((hash.readUInt32BE(hash.at(-1) & 15) & 0x7fffffff) % 1e6).padStart(6, "0");
}

async function checkAccessibility(page, surface, device) {
    const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    outcomes.push({ device, surface, violations: result.violations.map(item => ({
        id: item.id,
        impact: item.impact,
        targets: item.nodes.flatMap(node => node.target),
    })) });
}

async function verify(device, channel, viewport, mobile) {
    const browser = await chromium.launch({ channel, headless: true, args: ["--enable-unsafe-swiftshader"] });
    try {
        const context = await browser.newContext({ viewport, isMobile: mobile, hasTouch: mobile, reducedMotion: "reduce" });
        const page = await context.newPage();
        const exceptions = [];
        const failures = [];
        page.on("pageerror", error => exceptions.push(error.name));
        page.on("response", response => {
            if (response.status() >= 500) failures.push(new URL(response.url()).pathname.split("/").slice(0, 2).join("/"));
        });
        await page.goto(root + "/");
        const entryPath = new URL(page.url()).pathname;
        if (entryPath === "/") {
            assert(await page.getByRole("link", { name: /sign in/i }).first().count());
        } else {
            assert.equal(entryPath, "/signin");
            assert(await page.getByRole("heading", { name: "Sign in" }).isVisible());
        }
        await checkAccessibility(page, entryPath === "/" ? "public landing" : "public sign-in", device);
        await page.goto(root + "/overview");
        assert.equal(new URL(page.url()).pathname, "/signin");
        await page.goto(fixture("Browser " + device));
        await page.getByLabel("Your name").fill("Synthetic browser owner");
        await page.getByLabel("Create a password").fill("sufficiently long synthetic credentials 72");
        await page.getByRole("button", { name: "Create account" }).click();
        const secret = await page.locator(".qr .mono").textContent();
        await page.getByLabel("Code", { exact: true }).fill(totp(secret));
        await page.getByRole("button", { name: "Verify and continue" }).click();
        await page.getByRole("link", { name: "I’ve saved them, continue" }).click();
        assert(await page.getByRole("heading", { name: /Welcome, Synthetic browser owner/ }).isVisible());

        if (mobile) {
            await page.locator(".mobile-nav summary").focus();
            await page.keyboard.press("Enter");
            assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth));
            await page.keyboard.press("Escape");
            assert(await page.locator(".mobile-nav summary").evaluate(element => element === document.activeElement));
            await page.keyboard.press("Enter");
            await page.getByRole("link", { name: "Assessment", exact: true }).click();
        } else {
            await page.getByRole("navigation", { name: "Workspace" }).getByRole("link", { name: "Assessment" }).click();
        }
        await page.getByRole("button", { name: "Start assessment" }).click();
        await checkAccessibility(page, "assessment question", device);
        await page.screenshot({ path: join(evidence, device + "-assessment.png") });
        for (let index = 1; index <= 20; index++) {
            await page.getByText(new RegExp("Question " + index + " of 20")).waitFor();
            const answer = index === 1 ? "No" : index === 2 ? "Unsure" : "Yes";
            const choice = page.getByRole("radio", { name: answer, exact: true });
            if (mobile && index === 1) {
                await choice.focus();
                await page.keyboard.press("Space");
            } else {
                await choice.check();
            }
            await page.getByRole("button", { name: "Save and continue" }).click();
            if (index === 3) {
                await page.goto(root + "/assessment");
                await page.getByText(/Question 4 of 20/).waitFor();
            }
        }
        await page.getByRole("button", { name: "Submit assessment" }).click();
        await page.getByRole("heading", { name: "90% · Self-reported baseline" }).waitFor();
        await page.getByRole("link", { name: "View your actions" }).click();
        await page.getByRole("link", { name: "Protect administrator accounts with MFA" }).click();
        await page.getByRole("button", { name: "In progress" }).click();
        await page.getByRole("button", { name: "Done", exact: true }).click();
        await page.getByText("High priority · Done", { exact: true }).waitFor();
        await checkAccessibility(page, "action details", device);

        await page.goto(root + "/reports");
        await page.getByRole("link", { name: "Preview a new report" }).click();
        await page.getByRole("button", { name: "Save report" }).click();
        const reportUrl = page.url();
        await page.getByRole("button", { name: "Print or save as PDF" }).waitFor();
        await checkAccessibility(page, "saved report", device);
        await page.emulateMedia({ media: "print", reducedMotion: "reduce" });
        assert.equal(await page.locator(".app-header").isVisible(), false);
        if (!mobile) await page.pdf({ path: join(evidence, "example-report.pdf"), format: "A4" });
        await page.emulateMedia({ media: "screen", reducedMotion: "reduce" });

        await page.goto(root + "/settings/data");
        await page.getByRole("checkbox", { name: /confirm workspace export/i }).check();
        await page.getByRole("button", { name: "Request workspace export", exact: true }).click();
        await page.getByText("Received", { exact: true }).waitFor();
        await page.goto(root + "/domains");
        await page.getByText(/New DNS checks are disabled/).waitFor();
        await page.goto(root + "/profile");
        await page.getByLabel("Display name").fill("Updated synthetic name");
        await page.getByRole("button", { name: "Save profile" }).click();
        await page.getByText("Profile saved.").waitFor();

        await page.goto(root + "/overview");
        const layout = await page.evaluate(() => ({
            width: document.documentElement.clientWidth,
            scrollWidth: document.documentElement.scrollWidth,
            noMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
        }));
        assert(layout.scrollWidth <= layout.width, "Unexpected horizontal document overflow");
        assert(layout.noMotion);
        await page.screenshot({ path: join(evidence, device + "-overview.png") });

        await page.locator('summary[aria-label^="Account menu"]').click();
        await page.getByRole("button", { name: "Sign out" }).click();
        await page.goto(reportUrl);
        assert.equal(new URL(page.url()).pathname, "/signin");
        assert.deepEqual(exceptions, []);
        assert.deepEqual(failures, []);
        outcomes.push({ device, journey: "invite, MFA, 20 answers, resume, score, action, report, print, data request, DNS off, profile, sign-out", result: "PASS" });
    } finally {
        await browser.close();
    }
}

(async () => {
    try {
        await verify("Edge-desktop", "msedge", { width: 1440, height: 900 }, false);
        await verify("Chrome-mobile-320", "chrome", { width: 320, height: 799 }, true);
    } finally {
        writeFileSync(join(evidence, "browser-results.json"), JSON.stringify(outcomes, null, 2));
        console.log(JSON.stringify(outcomes));
    }
})().catch(error => {
    console.error(error.message.split("\n").map(line => line.replace(/\/invite\/[A-Za-z0-9_-]{43}/g, "/invite/[redacted]")).join("\n"));
    process.exitCode = 1;
});
