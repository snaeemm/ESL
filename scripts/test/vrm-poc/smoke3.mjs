import puppeteer from 'puppeteer';
const browser = await puppeteer.launch();
const page = await browser.newPage();
const logs = [];
page.on('console', (msg) => logs.push(`[${msg.type()}] ${msg.text()}`));
page.on('pageerror', (err) => logs.push('pageerror: ' + err.message));
await page.setViewport({ width: 1400, height: 700 });
await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0', timeout: 20000 });
await page.waitForFunction(() => window.__vrmReady === true, { timeout: 15000 }).catch(() => {});
await new Promise((r) => setTimeout(r, 300));
console.log(logs.filter(l => !l.includes('vite') && !l.includes('404')).join('\n'));

await page.evaluate(() => { const v = document.getElementById('source-video'); v.pause(); v.currentTime = 1.76; });
await new Promise((r) => setTimeout(r, 400));
await page.screenshot({ path: '/tmp/v3_t176.png' });

await browser.close();
