"""Capture UI screenshots for README."""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8000"

pages = [
    ("dashboard.png", "/"),
    ("objects.png", "/objects"),
    ("assistant.png", "/assistant"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    for name, path in pages:
        page.goto(f"{BASE}{path}", wait_until="networkidle")
        page.screenshot(path=str(OUT / name), full_page=True)
    browser.close()

print("Saved to", OUT)
