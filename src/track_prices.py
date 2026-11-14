# Logs prices once a day from a Shopify store's public product feed
# (/products.json) into a CSV. After 30 days there is enough history for
# omnibus.py to work on real prices.
#
#   python src/track_prices.py https://beaa.eu data/price_history.csv
#
# One run a day is plenty. I could only test the parsing on a sample feed.
import csv
import json
import sys
import urllib.request
from datetime import date


def parse_products(payload, today=None):
    today = today or date.today().isoformat()
    rows = []
    for prod in payload.get("products", []):
        for v in prod.get("variants", []):
            rows.append({
                "date": today,
                "handle": prod.get("handle", ""),
                "title": prod.get("title", ""),
                "variant": v.get("title", ""),
                "sku": v.get("sku") or "",
                "price": v.get("price", ""),
                "compare_at_price": v.get("compare_at_price") or "",
                "available": v.get("available", ""),
            })
    return rows


def fetch_all(base_url, limit=250, max_pages=10):
    products = []
    for page in range(1, max_pages + 1):
        url = f"{base_url.rstrip('/')}/products.json?limit={limit}&page={page}"
        req = urllib.request.Request(url, headers={"User-Agent": "price-audit (once a day, read only)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.load(r).get("products", [])
        if not batch:
            break
        products.extend(batch)
    return {"products": products}


def append_csv(rows, path):
    fields = ["date", "handle", "title", "variant", "sku", "price", "compare_at_price", "available"]
    try:
        is_new = open(path).read(1) == ""
    except FileNotFoundError:
        is_new = True
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if is_new:
            w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    base, out = sys.argv[1], sys.argv[2]
    rows = parse_products(fetch_all(base))
    append_csv(rows, out)
    print(f"logged {len(rows)} variants to {out}")
