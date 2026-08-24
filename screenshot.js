const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const htmlPath = path.resolve(__dirname, '公众号长文-男生视角.html');
  const outPath = path.resolve(__dirname, 'assets/wechat-long-image.png');

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 750, height: 800, deviceScaleFactor: 2 });
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });

  // Wait for images to load
  await page.evaluate(() => {
    return new Promise((resolve) => {
      const imgs = document.querySelectorAll('img');
      let loaded = 0;
      if (imgs.length === 0) return resolve();
      imgs.forEach(img => {
        if (img.complete) { loaded++; if (loaded === imgs.length) resolve(); }
        else img.onload = () => { loaded++; if (loaded === imgs.length) resolve(); };
        img.onerror = () => { loaded++; if (loaded === imgs.length) resolve(); };
      });
      setTimeout(resolve, 8000); // fallback
    });
  });

  await page.screenshot({
    path: outPath,
    fullPage: true,
    type: 'png'
  });

  console.log(`Screenshot saved to ${outPath}`);
  await browser.close();
})();
