from __future__ import annotations

"""Session-16 REQ-1 verification screenshots: Executive Dashboard at FIRM and
ADVISOR scope, after the real Claude AI insight has rendered."""

import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/qa_screenshots/session16"
OUT.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1600, "height": 1000})
        page.set_default_timeout(180000)

        # ---- FIRM scope (default) ----
        await page.goto("http://127.0.0.1:3000/dashboard", wait_until="domcontentloaded")
        await page.wait_for_selector("text=Key Drivers", timeout=180000)
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT / "dashboard_firm_scope.png"), full_page=True)
        print("firm scope captured")

        # ---- ADVISOR scope via persona selector ----
        await page.select_option("select >> nth=0", "Advisor")
        await page.wait_for_timeout(1000)
        # wait until advisor tiles render (Households tile only exists at advisor scope)
        await page.wait_for_selector("text=Revenue / Household", timeout=180000)
        await page.wait_for_selector("text=GNN peer group", timeout=180000)
        await page.wait_for_selector("text=Key Drivers", timeout=180000)
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT / "dashboard_advisor_scope.png"), full_page=True)
        print("advisor scope captured")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
