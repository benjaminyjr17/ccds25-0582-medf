"""
Headless Playwright screenshot capture for MEDF Streamlit UI.
Captures 4 pages in order: Evaluate, Conflict Detection, Pareto Resolution, Case Studies.
Triggers the Demo Scenario first to populate data, then captures each page.
Requirements: wide layout, 100% zoom, >=1800px width, high-res PNG.
"""
import asyncio
import json
import os
import time
from pathlib import Path
from playwright.async_api import async_playwright

STREAMLIT_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = Path("/home/ubuntu/ccds25-0582-medf/screenshots")
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
PAGES_ORDER = ["Evaluate", "Conflict Detection", "Pareto Resolution", "Case Studies"]

async def wait_for_streamlit_ready(page, timeout=30000):
    """Wait until Streamlit app is fully loaded."""
    try:
        await page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=timeout)
        await page.wait_for_timeout(3000)
    except Exception:
        await page.wait_for_timeout(5000)

async def click_radio_option(page, label_text):
    """Click a radio button option in the Streamlit page navigation."""
    try:
        radio = page.locator(f'label:has-text("{label_text}")')
        count = await radio.count()
        if count > 0:
            await radio.first.click()
            await page.wait_for_timeout(4000)
            return True
    except Exception as e:
        print(f"  Warning clicking radio '{label_text}': {e}")
    
    try:
        elements = page.locator(f'text="{label_text}"')
        count = await elements.count()
        if count > 0:
            await elements.first.click()
            await page.wait_for_timeout(4000)
            return True
    except Exception as e:
        print(f"  Warning with text selector '{label_text}': {e}")
    
    return False

async def click_button(page, button_text, timeout=10000):
    """Click a button by its text."""
    try:
        btn = page.locator(f'button:has-text("{button_text}")')
        count = await btn.count()
        if count > 0:
            await btn.first.click()
            print(f"  Clicked button: '{button_text}'")
            return True
    except Exception as e:
        print(f"  Warning clicking button '{button_text}': {e}")
    return False

async def capture_full_page(page, filepath):
    """Capture full page screenshot."""
    await page.screenshot(path=str(filepath), full_page=True, type="png")
    size = os.path.getsize(filepath)
    print(f"  Saved: {filepath} ({size:,} bytes)")

async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "capture_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "streamlit_url": STREAMLIT_URL,
        "viewport": {"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
        "screenshots": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--force-device-scale-factor=1",
                "--high-dpi-support=1",
            ]
        )
        context = await browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=2,  # High DPI for crisp screenshots
        )
        page = await context.new_page()

        print(f"Navigating to {STREAMLIT_URL}...")
        await page.goto(STREAMLIT_URL, wait_until="networkidle", timeout=60000)
        await wait_for_streamlit_ready(page)
        print("Streamlit app loaded.")

        # Step 1: Click "Run Demo Scenario" to populate data
        print("\n--- Running Demo Scenario ---")
        demo_clicked = await click_button(page, "Run Demo Scenario")
        if demo_clicked:
            # Wait for the demo to complete - it triggers evaluate, conflicts, pareto
            await page.wait_for_timeout(15000)
            print("  Demo scenario completed.")
        else:
            print("  WARNING: Could not click 'Run Demo Scenario'")

        # Step 2: Capture each page in order WITHOUT refreshing
        for page_name in PAGES_ORDER:
            print(f"\n--- Capturing: {page_name} ---")
            
            clicked = await click_radio_option(page, page_name)
            if not clicked:
                print(f"  ERROR: Could not navigate to '{page_name}'")
                continue

            # Wait for content to load
            await page.wait_for_timeout(5000)
            
            # Scroll to top
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)

            safe_name = page_name.lower().replace(" ", "_")
            filepath = OUTPUT_DIR / f"screenshot_{safe_name}.png"
            
            await capture_full_page(page, filepath)
            
            manifest["screenshots"].append({
                "page": page_name,
                "filename": filepath.name,
                "filepath": str(filepath),
                "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "viewport_width": VIEWPORT_WIDTH,
                "viewport_height": VIEWPORT_HEIGHT,
                "device_scale_factor": 2,
                "effective_width_px": VIEWPORT_WIDTH * 2,
                "demo_scenario_run": demo_clicked,
            })

        await browser.close()

    # Save manifest
    manifest_path = OUTPUT_DIR / "screenshot_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved: {manifest_path}")
    print("Screenshot capture complete.")

if __name__ == "__main__":
    asyncio.run(main())
