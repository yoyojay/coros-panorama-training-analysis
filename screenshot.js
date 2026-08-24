const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const htmlPath = path.resolve(__dirname, '公众号长文-男生视角.html');
  const outPathPng = path.resolve(__dirname, 'assets/wechat-long-image.png');
  const outPathJpg = path.resolve(__dirname, 'assets/wechat-long-image.jpg');

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  // 1x scale, 750px width = standard mobile
  await page.setViewport({ width: 750, height: 800, deviceScaleFactor: 1 });
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
      setTimeout(resolve, 10000);
    });
  });

  // PNG version (lossless)
  await page.screenshot({ path: outPathPng, fullPage: true, type: 'png' });

  // JPEG version (compressed, better for WeChat)
  await page.screenshot({ path: outPathJpg, fullPage: true, type: 'jpeg', quality: 85 });

  console.log(`PNG saved to ${outPathPng}`);
  console.log(`JPEG saved to ${outPathJpg}`);
  await browser.close();
})();
