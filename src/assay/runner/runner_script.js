/**
 * Assay Playwright runner entry point.
 *
 * Single-URL mode (ASSAY_TARGET_URL set):
 *   Navigate to URL, take full-page screenshot, write result.json
 *
 * Script mode (ASSAY_SCRIPT_FILE set):
 *   Execute step-by-step script, write script_result.json + per-step screenshots
 *
 * Environment variables:
 *   ASSAY_TARGET_URL   — URL to test (single-URL mode)
 *   ASSAY_SCRIPT_FILE  — path to script JSON inside the container (script mode)
 *   ASSAY_SUITE        — suite name for result metadata (default: "default")
 *   ASSAY_OUTPUT_DIR   — directory to write outputs (default: "/output")
 *
 * Exit codes:
 *   0 — pass
 *   1 — fail or error
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.ASSAY_TARGET_URL;
const scriptFile = process.env.ASSAY_SCRIPT_FILE;
const suite = process.env.ASSAY_SUITE || 'default';
const outputDir = process.env.ASSAY_OUTPUT_DIR || '/output';

fs.mkdirSync(outputDir, { recursive: true });

if (scriptFile) {
  runScript(scriptFile).catch((err) => {
    console.error('script runner fatal error:', err.message);
    process.exit(1);
  });
} else {
  if (!targetUrl) {
    console.error('ASSAY_TARGET_URL or ASSAY_SCRIPT_FILE is required');
    process.exit(1);
  }
  runUrl(targetUrl).catch((err) => {
    console.error('url runner fatal error:', err.message);
    process.exit(1);
  });
}

// ── Single-URL mode ───────────────────────────────────────────────────────────

async function runUrl(url) {
  const timestamp = new Date().toISOString();
  const screenshotPath = path.join(outputDir, 'screenshot.png');
  const resultPath = path.join(outputDir, 'result.json');

  let browser;
  try {
    browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const result = { outcome: 'pass', url, suite, timestamp, error: null };
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
    process.exit(0);
  } catch (err) {
    const result = { outcome: 'fail', url, suite, timestamp, error: err.message };
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result));
    process.exit(1);
  } finally {
    if (browser) await browser.close();
  }
}

// ── Script mode ───────────────────────────────────────────────────────────────

async function runScript(scriptFilePath) {
  const timestamp = new Date().toISOString();
  const resultPath = path.join(outputDir, 'script_result.json');

  let rawScript;
  try {
    rawScript = JSON.parse(fs.readFileSync(scriptFilePath, 'utf8'));
  } catch (err) {
    const result = {
      outcome: 'fail', name: path.basename(scriptFilePath, '.json'),
      url: '', suite, timestamp, error: `Failed to parse script: ${err.message}`, steps: [],
    };
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));
    process.exit(1);
  }

  const scriptName = rawScript.name || path.basename(scriptFilePath, '.json');
  const steps = Array.isArray(rawScript.steps) ? rawScript.steps : [];
  const stepResults = [];
  let firstUrl = '';
  let overallOutcome = 'pass';
  let browser;

  try {
    browser = await chromium.launch();
    const page = await browser.newPage();

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      const stepResult = {
        index: i,
        type: step.type,
        label: step.label || step.type,
        outcome: 'pass',
        error: null,
        screenshot: null,
      };

      try {
        switch (step.type) {
          case 'navigate':
            await page.goto(step.url, { waitUntil: 'networkidle', timeout: 30000 });
            if (!firstUrl) firstUrl = step.url;
            break;
          case 'click':
            await page.click(step.selector, { timeout: step.timeout || 5000 });
            break;
          case 'fill':
            await page.fill(step.selector, step.value || '');
            break;
          case 'wait_for':
            await page.waitForSelector(step.selector, { timeout: step.timeout || 5000 });
            break;
          case 'wait':
            await page.waitForTimeout(step.ms || 1000);
            break;
          case 'screenshot': {
            const label = step.label || `step-${i}`;
            const filename = `step-${i}-${label.replace(/[^a-z0-9-]/gi, '_')}.png`;
            await page.screenshot({ path: path.join(outputDir, filename), fullPage: true });
            stepResult.screenshot = filename;
            break;
          }
          default:
            throw new Error(`Unknown step type: ${step.type}`);
        }
      } catch (err) {
        stepResult.outcome = 'fail';
        stepResult.error = err.message;
        overallOutcome = 'fail';
        // Continue collecting evidence from remaining steps
      }

      stepResults.push(stepResult);
    }
  } catch (err) {
    overallOutcome = 'fail';
    const result = {
      outcome: overallOutcome, name: scriptName, url: firstUrl,
      suite, timestamp, error: err.message, steps: stepResults,
    };
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));
    process.exit(1);
  } finally {
    if (browser) await browser.close();
  }

  const scriptResult = {
    outcome: overallOutcome, name: scriptName, url: firstUrl,
    suite, timestamp, error: null, steps: stepResults,
  };
  fs.writeFileSync(resultPath, JSON.stringify(scriptResult, null, 2));
  console.log(JSON.stringify(scriptResult));
  process.exit(overallOutcome === 'pass' ? 0 : 1);
}
