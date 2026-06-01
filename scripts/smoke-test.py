#!/usr/bin/env python3
"""Smoke test the webui in headless Firefox.

Loads the home page plus reference game pages, waits for async fetches to
settle, then asserts:
  - placeholder strings (e.g. "Loading reports...") have been replaced
  - expected content markers are present
  - no JavaScript errors fired during page load (via early-installed
    window.addEventListener('error') / unhandledrejection hooks)

The error catcher must be in place before the bundle scripts run, so this
expects to be pointed at a server that injects a small <script> at the top
of app.html's <head>. The wrapping bash script (`scripts/smoke.sh`) handles
that by copying the site to a temp dir and inserting the snippet.

Exit code: 0 if all pages pass, 1 otherwise. Page failures are printed with
context so CI logs are usable without a screenshot.
"""

import argparse
import sys
import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options


PAGES = [
    {
        "path": "/app.html",
        "label": "home",
        "forbidden": ["Loading Proton Pulse reports..."],
        # Home renders a "Recent Reports" feed OR an empty state -- accept either
        "required_any": ["Recent Reports", "Search for a game"],
    },
    {
        # Cyberpunk 2077: rich reference, lots of reports + a saved config
        "path": "/app.html#/app/1091500",
        "label": "app/cyberpunk",
        "forbidden": ["Loading reports..."],
        "required_any": ["game-header"],
    },
    {
        # Wukong: the config-heavy case that surfaced the renderFormResponses
        # ReferenceError. Keep it in the rotation so a similar bug shows up
        # here before it ships
        "path": "/app.html#/app/2358720",
        "label": "app/wukong",
        "forbidden": ["Loading reports..."],
        "required_any": ["game-header"],
    },
]


def setup_driver():
    opts = Options()
    opts.add_argument("--headless")
    return webdriver.Firefox(options=opts)


def smoke_page(driver, base_url, spec, wait_s):
    url = base_url + spec["path"]
    label = spec["label"]
    print(f"-> {label}: {url}")
    driver.get(url)
    time.sleep(wait_s)
    content = driver.execute_script(
        "return document.getElementById('content')?.innerHTML || ''"
    ) or ""
    errs = driver.execute_script("return (window.__smoke_errors || []).slice()") or []
    title = driver.title or ""
    failures = []
    for bad in spec["forbidden"]:
        if bad in content:
            failures.append(f"forbidden string still present after {wait_s}s: {bad!r}")
    if spec["required_any"] and not any(g in content for g in spec["required_any"]):
        failures.append(
            f"none of required markers present in content (first 200 chars: "
            f"{content[:200]!r})"
        )
    if errs:
        # Dedupe -- the same error often fires multiple times
        unique = list(dict.fromkeys(errs))
        failures.append(f"{len(errs)} JS errors captured ({len(unique)} unique):")
        for e in unique[:5]:
            failures.append(f"    {e}")
    if failures:
        print(f"   FAIL")
        for f in failures:
            print(f"   {f}")
        return False
    print(f"   OK | title={title!r} content_chars={len(content)}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8765",
        help="Base URL to load pages from (default: %(default)s)",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=10,
        help="Seconds to wait after each navigation before checking (default: %(default)s)",
    )
    args = parser.parse_args()

    driver = setup_driver()
    try:
        results = [smoke_page(driver, args.base_url, p, args.wait) for p in PAGES]
    finally:
        driver.quit()

    passed = sum(1 for r in results if r)
    total = len(results)
    print()
    print("=" * 40)
    if passed != total:
        print(f"FAILED: {total - passed}/{total} pages")
        sys.exit(1)
    print(f"PASSED: {passed}/{total} pages")


if __name__ == "__main__":
    main()
