const fs = require('fs');
const path = require('path');
const puppeteer = require(path.join(__dirname, '../dashboard/node_modules/puppeteer-core'));

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const SCREENSHOTS_DIR = path.resolve(__dirname, '..', 'docs', 'screenshots');

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function run() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
  }

  console.log('Launching headless Microsoft Edge with puppeteer-core...');
  const browser = await puppeteer.launch({
    executablePath: EDGE_PATH,
    headless: 'new',
    defaultViewport: { width: 1400, height: 950, deviceScaleFactor: 1.5 },
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1400,950']
  });

  const page = await browser.newPage();

  // 1. Authenticate with backend
  console.log('Authenticating with backend...');
  let token = '';
  try {
    const loginRes = await fetch('http://127.0.0.1:5000/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: 'admin123' })
    });
    const loginData = await loginRes.json();
    token = loginData.token;
    console.log('Got JWT auth token successfully.');
  } catch (err) {
    console.warn('Could not fetch token:', err.message);
  }

  // Pre-seed localStorage before page scripts execute
  await page.evaluateOnNewDocument((t) => {
    if (t) localStorage.setItem('smart_shelf_token', t);
  }, token);

  console.log('Navigating to http://localhost:5173...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(2000);

  // --------------------------------------------------------------------------
  // Screenshot 1: Demo page with annotated sample
  // --------------------------------------------------------------------------
  console.log('\n[1/4] Navigating to Demo Studio & Sandbox...');
  await page.evaluate(() => {
    const navItems = Array.from(document.querySelectorAll('nav div'));
    const demoItem = navItems.find((el) => el.textContent && el.textContent.includes('Try It / Demo'));
    if (demoItem) demoItem.click();
  });
  console.log('Waiting for YOLO inference and side-by-side visualization...');
  await sleep(6000);

  const demoPath = path.join(SCREENSHOTS_DIR, 'demo_page_annotated.png');
  await page.screenshot({ path: demoPath, fullPage: false });
  console.log(`Saved: ${demoPath}`);

  // --------------------------------------------------------------------------
  // Screenshot 2: Dashboard in DEMO MODE with Low alert and shortage prediction
  // --------------------------------------------------------------------------
  console.log('\n[2/4] Switching to gradual_depletion scenario in DEMO MODE...');
  try {
    await fetch('http://127.0.0.1:5000/camera/mode', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        mode: 'simulated',
        scenario: 'gradual_depletion',
        speed: 10.0
      })
    });
  } catch (e) {
    console.warn('Camera mode fetch error:', e.message);
  }

  // Navigate back to Dashboard
  await page.evaluate(() => {
    const navItems = Array.from(document.querySelectorAll('nav div'));
    const dashItem = navItems.find((el) => el.textContent && el.textContent.includes('Home') || el.textContent.includes('Live Shelves'));
    if (dashItem) dashItem.click();
  });
  console.log('Waiting for pipeline to cycle through gradual depletion frames to trigger Low alert...');
  await sleep(6000);

  const dashPath = path.join(SCREENSHOTS_DIR, 'dashboard_demo_mode.png');
  await page.screenshot({ path: dashPath, fullPage: false });
  console.log(`Saved: ${dashPath}`);

  // --------------------------------------------------------------------------
  // Screenshot 3: Pipeline trace card showing 3-photo confirmation counter
  // --------------------------------------------------------------------------
  console.log('\n[3/4] Capturing Pipeline trace card...');
  // Scroll down slightly so the trace card & camera feed are front and center
  await page.evaluate(() => {
    window.scrollBy(0, 420);
  });
  await sleep(1000);

  const tracePath = path.join(SCREENSHOTS_DIR, 'pipeline_trace_card.png');
  await page.screenshot({ path: tracePath, fullPage: false });
  console.log(`Saved: ${tracePath}`);

  // --------------------------------------------------------------------------
  // Screenshot 4: Customer blocking scenario showing no false alert
  // --------------------------------------------------------------------------
  console.log('\n[4/4] Switching to customer_blocking scenario...');
  try {
    await fetch('http://127.0.0.1:5000/camera/mode', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        mode: 'simulated',
        scenario: 'customer_blocking',
        speed: 5.0
      })
    });
  } catch (e) {
    console.warn('Customer blocking switch error:', e.message);
  }
  await sleep(4000);

  const cbPath = path.join(SCREENSHOTS_DIR, 'customer_blocking_no_false_alert.png');
  await page.screenshot({ path: cbPath, fullPage: false });
  console.log(`Saved: ${cbPath}`);

  // --------------------------------------------------------------------------
  // Mobile Screenshots (375px)
  // --------------------------------------------------------------------------
  console.log('\nCapturing Mobile View at 375px...');
  await page.setViewport({ width: 375, height: 812, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(1500);

  const mobileDashPath = path.join(SCREENSHOTS_DIR, 'dashboard_mobile_375px.png');
  await page.screenshot({ path: mobileDashPath, fullPage: false });
  console.log(`Saved: ${mobileDashPath}`);

  // Mobile Demo Studio
  await page.evaluate(() => {
    const bottomNavButtons = Array.from(document.querySelectorAll('.mobile-bottom-bar button, .mobile-nav-pill-item'));
    const demoBtn = bottomNavButtons.find((el) => el.textContent && el.textContent.includes('Demo'));
    if (demoBtn) demoBtn.click();
  });
  await sleep(3000);

  const mobileDemoPath = path.join(SCREENSHOTS_DIR, 'demo_mobile_375px.png');
  await page.screenshot({ path: mobileDemoPath, fullPage: false });
  console.log(`Saved: ${mobileDemoPath}`);

  await browser.close();
  console.log('\nAll Phase 10 screenshots successfully captured and saved in docs/screenshots/!');
}

run().catch((err) => {
  console.error('Screenshot script error:', err);
  process.exit(1);
});
