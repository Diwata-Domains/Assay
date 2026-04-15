/**
 * Assay Playwright runner entry point.
 *
 * Environment variables:
 *   ASSAY_TARGET_URL   — required; URL to navigate to
 *   ASSAY_SUITE        — optional; suite name for result metadata (default: "default")
 *   ASSAY_OUTPUT_DIR   — optional; directory to write outputs (default: "/output")
 *
 * Outputs (written to ASSAY_OUTPUT_DIR):
 *   screenshot.png     — full-page screenshot
 *   result.json        — { outcome, url, suite, timestamp, error }
 *
 * Exit codes:
 *   0 — navigation and screenshot succeeded (outcome: "pass")
 *   1 — error during execution (outcome: "fail")
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.ASSAY_TARGET_URL;
const suite = process.env.ASSAY_SUITE || 'default';
const outputDir = process.env.ASSAY_OUTPUT_DIR || '/output';

if (!targetUrl) {
  console.error('ASSAY_TARGET_URL is required');
  process.exit(1);
}

async function run() {
  const timestamp = new Date().toISOString();
  const screenshotPath = path.join(outputDir, 'screenshot.png');
  const resultPath = path.join(outputDir, 'result.json');

  fs.mkdirSync(outputDir, { recursive: true });

  let browser;
  try {
    browser = await chromium.launch();
    const page = await browser.newPage();

    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30000 });
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const result = {
      outcome: 'pass',
      url: targetUrl,
      suite,
      timestamp,
      error: null,
    };
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
    process.exit(0);
  } catch (err) {
    const result = {
      outcome: 'fail',
      url: targetUrl,
      suite,
      timestamp,
      error: err.message,
    };
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result));
    process.exit(1);
  } finally {
    if (browser) await browser.close();
  }
}

run();
