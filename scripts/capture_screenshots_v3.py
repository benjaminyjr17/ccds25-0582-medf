"""
Headless Playwright screenshot capture for MEDF Streamlit UI v3.
Captures 4 pages in order: Evaluate, Conflict Detection, Pareto Resolution, Case Studies.
Triggers actions on each page to populate data before capturing.
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
            device_scale_factor=2,
        )
        page = await context.new_page()

        print(f"Navigating to {STREAMLIT_URL}...")
        await page.goto(STREAMLIT_URL, wait_until="networkidle", timeout=60000)
        await wait_for_streamlit_ready(page)
        print("Streamlit app loaded.")

        # ===== PAGE 1: EVALUATE =====
        print("\n=== PAGE 1: Evaluate ===")
        # Already on Evaluate page by default
        await page.wait_for_timeout(2000)
        
        # Click Evaluate button to run evaluation
        await click_button(page, "Evaluate")
        await page.wait_for_timeout(8000)  # Wait for API call and rendering
        
        # Scroll to top and capture
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        filepath = OUTPUT_DIR / "screenshot_evaluate.png"
        await capture_full_page(page, filepath)
        manifest["screenshots"].append({
            "page": "Evaluate",
            "filename": filepath.name,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "viewport_width": VIEWPORT_WIDTH,
            "device_scale_factor": 2,
            "effective_width_px": VIEWPORT_WIDTH * 2,
        })

        # ===== PAGE 2: CONFLICT DETECTION =====
        print("\n=== PAGE 2: Conflict Detection ===")
        await click_radio_option(page, "Conflict Detection")
        await page.wait_for_timeout(3000)
        
        # Click Detect Conflicts button
        await click_button(page, "Detect Conflicts")
        await page.wait_for_timeout(8000)
        
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        filepath = OUTPUT_DIR / "screenshot_conflict_detection.png"
        await capture_full_page(page, filepath)
        manifest["screenshots"].append({
            "page": "Conflict Detection",
            "filename": filepath.name,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "viewport_width": VIEWPORT_WIDTH,
            "device_scale_factor": 2,
            "effective_width_px": VIEWPORT_WIDTH * 2,
        })

        # ===== PAGE 3: PARETO RESOLUTION =====
        print("\n=== PAGE 3: Pareto Resolution ===")
        await click_radio_option(page, "Pareto Resolution")
        await page.wait_for_timeout(3000)
        
        # Click Generate Pareto Frontier button
        await click_button(page, "Generate Pareto Frontier")
        await page.wait_for_timeout(15000)  # Pareto takes longer (NSGA-II optimization)
        
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        filepath = OUTPUT_DIR / "screenshot_pareto_resolution.png"
        await capture_full_page(page, filepath)
        manifest["screenshots"].append({
            "page": "Pareto Resolution",
            "filename": filepath.name,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "viewport_width": VIEWPORT_WIDTH,
            "device_scale_factor": 2,
            "effective_width_px": VIEWPORT_WIDTH * 2,
        })

        # ===== PAGE 4: CASE STUDIES =====
        print("\n=== PAGE 4: Case Studies ===")
        await click_radio_option(page, "Case Studies")
        await page.wait_for_timeout(3000)
        
        # Click Run Case Study button for the first case study
        await click_button(page, "Run Case Study")
        await page.wait_for_timeout(10000)
        
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        filepath = OUTPUT_DIR / "screenshot_case_studies.png"
        await capture_full_page(page, filepath)
        manifest["screenshots"].append({
            "page": "Case Studies",
            "filename": filepath.name,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "viewport_width": VIEWPORT_WIDTH,
            "device_scale_factor": 2,
            "effective_width_px": VIEWPORT_WIDTH * 2,
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
