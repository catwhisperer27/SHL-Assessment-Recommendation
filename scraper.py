"""
SHL Catalogue Scraper — Individual Test Solutions ONLY
Extracts:
- test_types (A/B/C/K/P/S badges)
- remote_testing
- adaptive/irt flags
- description
- duration
- job_levels (structured metadata)

Setup:
    pip install playwright beautifulsoup4
    playwright install chromium

Run:
    python scraper.py
    python scraper.py --no-enrich
"""

import sys, json, re, time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"

TYPE_MAP = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behaviour",
    "S": "Simulations",
}


def is_checked(cell):
    if not cell:
        return False

    text = cell.get_text(strip=True).lower()
    if text in ("yes", "✓", "✔", "true", "1"):
        return True

    for img in cell.find_all("img"):
        alt = img.get("alt", "").lower()
        src = img.get("src", "").lower()
        if "yes" in alt or "check" in alt or "tick" in alt:
            return True
        if "yes" in src or "check" in src or "tick" in src:
            return True

    html = str(cell)
    if any(x in html.lower() for x in [
        "catalogue-checked", "yes", "checkmark", "tick",
        "icon-check", "fa-check", "-yes", "_yes",
        "custom-tooltip", "true"
    ]):
        if "no" not in text and "false" not in text:
            return True

    for span in cell.find_all("span"):
        cls = " ".join(span.get("class", []))
        if any(x in cls for x in ["yes", "check", "tick", "active"]):
            return True

    return False


def extract_test_types(first_col):
    letters = []
    for span in first_col.find_all("span"):
        t = span.get_text(strip=True)
        if t in TYPE_MAP:
            letters.append(t)
    return [TYPE_MAP[l] for l in letters]


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    rows = soup.select("table tbody tr")
    for row in rows:
        cols = row.find_all("td")
        if not cols:
            continue

        link = cols[0].find("a")
        if not link:
            continue

        name = link.get_text(strip=True)
        href = link.get("href", "")
        if not name or not href:
            continue

        url = (BASE + href) if href.startswith("/") else href

        remote   = is_checked(cols[1]) if len(cols) > 1 else False
        adaptive = is_checked(cols[2]) if len(cols) > 2 else False
        test_types = extract_test_types(cols[3]) if len(cols) > 3 else []

        results.append({
            "name": name,
            "url": url,
            "category": "Individual Test Solutions",
            "test_types": test_types,
            "remote_testing": remote,
            "adaptive": adaptive,
            "description": "",
            "duration_minutes": None,
            "job_levels": [],
        })

    return results


def enrich(page, items):
    print(f"\nEnriching {len(items)} assessments (description + duration + job_levels)...")

    for i, a in enumerate(items):
        sys.stdout.write(f"\r  [{i+1}/{len(items)}] {a['name'][:60]:<60}")
        sys.stdout.flush()

        try:
            page.goto(a["url"], wait_until="domcontentloaded", timeout=60000)
            time.sleep(0.8)
            soup = BeautifulSoup(page.content(), "html.parser")

            # Description
            meta = soup.select_one("meta[name='description']")
            if meta:
                a["description"] = meta.get("content", "").strip()

            text = soup.get_text(" ")

            # Duration
            m = re.search(r'Approximate Completion Time in minutes\s*[=:]\s*(\d+)', text, re.I)
            if m:
                a["duration_minutes"] = int(m.group(1))
            else:
                m2 = re.search(r'\b(\d{1,3})\s*(?:minutes?|mins?)\b', text, re.I)
                if m2:
                    val = int(m2.group(1))
                    if 1 <= val <= 180:
                        a["duration_minutes"] = val

            # -------- Job Level Extraction (Structured Metadata) --------
            # -------- Job Level Extraction (Dynamic + Structured) --------
            job_levels = []

            label = soup.find(string=re.compile(r'^Job levels?$', re.I))

            if label:
                parent = label.find_parent()

                if parent:
                    container = parent.find_next_sibling()

                    if container:
            # Extract only direct text from this container
                        for item in container.find_all(["li", "span", "a"]):
                            text = item.get_text(strip=True)

                            if text and len(text) < 50:   # avoid long paragraphs
                                job_levels.append(text)

                        # Fallback if structured tags not present
                        if not job_levels:
                            text_block = container.get_text(separator=",", strip=True)
                            parts = re.split(r',|\n', text_block)

                            for p in parts:
                                clean = p.strip()
                                if clean and len(clean) < 50:
                                    job_levels.append(clean)

            a["job_levels"] = sorted(list(set(job_levels)))

        except Exception as e:
            print(f"\n  [!] Error enriching {a['name']}: {e}")

    print("\nEnrichment done.")


def scrape(no_enrich=False):
    all_items = []
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()

        print("Loading SHL homepage...")
        page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        print("\nScraping Individual Test Solutions ONLY...")
        pg = 0

        while True:
            start = pg * 12
            url = f"{CATALOG_URL}?type=1&start={start}"
            print(f"  Page {pg+1} start={start}")

            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(1.5)

            html = page.content()
            rows = parse_page(html)

            if not rows:
                break

            new = [r for r in rows if r["url"] not in seen]
            for r in new:
                seen.add(r["url"])
                all_items.append(r)

            pg += 1

        if not no_enrich:
            enrich(page, all_items)

        browser.close()

    return all_items


def save(items):
    # Save JSON (unchanged)
    with open("catalogue.json", "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    # Save Python file (VALID Python syntax)
    with open("catalogue.py", "w", encoding="utf-8") as f:
        f.write('"""\nAuto-generated by scraper.py\n"""\n\n')
        f.write("ASSESSMENTS = ")
        f.write(repr(items))   # <-- FIXED
        f.write("\n")

    print("\n✅ Saved catalogue.json + catalogue.py")
    print(f"Total Individual Test Solutions: {len(items)}")

if __name__ == "__main__":
    no_enrich = "--no-enrich" in sys.argv

    print("SHL Scraper — Individual Only")
    print(f"Enrichment : {'OFF' if no_enrich else 'ON'}\n")

    items = scrape(no_enrich=no_enrich)
    save(items)