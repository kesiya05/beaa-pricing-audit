# Numbers behind the audit. Works on the two snapshot files in data/.
import json
import re
from collections import defaultdict


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pct_off(p):
    # whole-number discount, 0 when the item isn't on sale
    if p.get("sale") is None:
        return 0
    return round((1 - p["sale"] / p["regular"]) * 100)


# Same garment in different colours. Matched on the product name.
FAMILIES = [
    ("Libre dress", r"^Libre Dress"),
    ("V-neck dress", r"^V-Neck Dress"),
    ("Palazzo trousers", r"Palazzo Trousers|Palazzo Pants"),
    ("Pleated trousers", r"^Pleated Trousers"),
    ("Python set", r"^Python Top|^Trousers Python"),
    ("Midi skirt", r"^Midi Skirt"),
    ("Silk satin top", r"^Silk Satin Top"),
    ("Silk shirt", r"^Silk Shirt"),
    ("Relax wear", r"^Relax Wear"),
    ("Regular-fit trousers", r"^Regular-fit Trousers"),
    ("Riviera shirt", r"^Riviera Shirt"),
    ("Oversized turtleneck", r"^Oversized Turtleneck"),
]


def family_of(name):
    for fam, rx in FAMILIES:
        if re.search(rx, name):
            return fam
    return None


def overview(products):
    clothes = [p for p in products if not p["accessory"]]
    on_sale = [p for p in clothes if p["sale"] is not None]
    pcts = [pct_off(p) for p in on_sale]
    best = [p for p in clothes if "B" in p["tags"]]
    new = [p for p in clothes if "N" in p["tags"]]
    buckets = defaultdict(int)
    for x in pcts:
        buckets[x] += 1
    return {
        "apparel_count": len(clothes),
        "on_sale": len(on_sale),
        "share_on_sale": len(on_sale) / len(clothes) if clothes else 0,
        "avg_discount": sum(pcts) / len(pcts) if pcts else 0,
        "max_discount": max(pcts) if pcts else 0,
        "buckets": dict(sorted(buckets.items())),
        "best_sellers": len(best),
        "best_sellers_30plus": len([p for p in best if pct_off(p) >= 30]),
        "new_items": len(new),
        "new_items_on_sale": len([p for p in new if p["sale"] is not None]),
        "black_line_items": len([p for p in clothes if "BL" in p["tags"]]),
        "avg_list_price": sum(p["regular"] for p in clothes) / len(clothes) if clothes else 0,
    }


def inconsistent_families(products, min_spread=20):
    groups = defaultdict(list)
    for p in products:
        if p["accessory"]:
            continue
        fam = family_of(p["name"])
        if fam:
            groups[fam].append(p)
    out = []
    for fam, items in groups.items():
        pcts = [pct_off(i) for i in items]
        if len(items) >= 2 and max(pcts) - min(pcts) >= min_spread:
            out.append({
                "family": fam,
                "spread": max(pcts) - min(pcts),
                "low": min(pcts),
                "high": max(pcts),
                "items": sorted(
                    [{"name": i["name"], "pct": pct_off(i), "regular": i["regular"],
                      "sale": i["sale"], "tags": i["tags"]} for i in items],
                    key=lambda r: -r["pct"]),
            })
    return sorted(out, key=lambda r: -r["spread"])


def creep(old, new):
    # products that are in both snapshots and whose discount changed
    old_map = {p["slug"]: p for p in old["products"]}
    rows = []
    for p in new["products"]:
        o = old_map.get(p["slug"])
        if not o:
            continue
        a, b = pct_off(o), pct_off(p)
        if a != b:
            rows.append({
                "name": p["name"], "from_pct": a, "to_pct": b,
                "regular": p["regular"], "sale": p["sale"],
                "lost_black_line": ("BL" in o["tags"]) and ("BL" not in p["tags"]),
                "was_new": "N" in o["tags"] or "N" in p["tags"],
            })
    rows.sort(key=lambda r: -(r["to_pct"] - r["from_pct"]))
    return {
        "compared": len([p for p in new["products"] if p["slug"] in old_map]),
        "changed": len(rows),
        "deeper": len([r for r in rows if r["to_pct"] > r["from_pct"]]),
        "rows": rows,
    }
