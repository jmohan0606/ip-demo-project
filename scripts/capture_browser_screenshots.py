from __future__ import annotations

import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/real_browser_screenshots"
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("dashboard", "http://127.0.0.1:3000/dashboard"),
    ("advisor_360", "http://127.0.0.1:3000/advisor-360"),
    ("what_if", "http://127.0.0.1:3000/what-if"),
    ("recommendation_runtime", "http://127.0.0.1:3000/recommendation-runtime"),
    ("feature_runtime", "http://127.0.0.1:3000/feature-runtime"),
    ("memory_runtime", "http://127.0.0.1:3000/memory-runtime"),
    ("knowledge_runtime", "http://127.0.0.1:3000/knowledge-runtime"),
    ("graph_runtime", "http://127.0.0.1:3000/graph-runtime"),
    ("tigergraph_activation", "http://127.0.0.1:3000/tigergraph-activation"),
    ("llm_activation", "http://127.0.0.1:3000/llm-activation"),
    ("orchestration", "http://127.0.0.1:3000/orchestration"),
]


async def main() -> None:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        raise SystemExit(
            "Playwright is not installed. Run: cd frontend && npm install && npx playwright install chromium"
        ) from exc

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1600, "height": 950})
        results = []
        for name, url in PAGES:
            path = OUT / f"{name}.png"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.screenshot(path=str(path), full_page=True)
                results.append({"page": name, "url": url, "status": "passed", "path": str(path)})
            except Exception as exc:
                results.append({"page": name, "url": url, "status": "failed", "error": str(exc)})
        await browser.close()

    report = OUT / "screenshot_report.json"
    import json
    report.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
