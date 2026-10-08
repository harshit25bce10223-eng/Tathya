const { chromium, expect } = require("@playwright/test")
;(async () => {
  const browser = await chromium.launch({ channel: "chromium", headless: true })
  const context = await browser.newContext({
    viewport: { width: 1100, height: 800 },
    recordVideo: {
      dir: "artifacts/ui-review/splash-video",
      size: { width: 1100, height: 800 },
    },
  })
  const page = await context.newPage()
  await page.goto("http://127.0.0.1:4173/login")
  await expect(
    page.getByRole("status", { name: "Welcome to Tathya" }),
  ).toBeVisible()
  await expect(
    page.getByRole("status", { name: "Welcome to Tathya" }),
  ).toHaveCount(0, { timeout: 6000 })
  await page.reload()
  await expect(
    page.getByRole("status", { name: "Welcome to Tathya" }),
  ).toHaveCount(0)
  await page.goto("http://127.0.0.1:4173/splash")
  await page
    .locator(".splash-art img")
    .first()
    .evaluate((img) => img.decode())
  await page.waitForTimeout(2800)
  await page.getByRole("button", { name: "Replay animation" }).click()
  await page.waitForTimeout(2800)
  const video = page.video()
  await context.close()
  await video.saveAs("artifacts/ui-review/splash-animation.webm")
  await browser.close()
  console.log(
    "Splash first visit, session persistence and replay passed; video recorded.",
  )
})().catch((e) => {
  console.error(e)
  process.exit(1)
})
