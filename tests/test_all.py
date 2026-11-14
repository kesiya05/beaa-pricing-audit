import json, sys, os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import analysis, normalise, omnibus, track_prices, build_site

D = os.path.join(os.path.dirname(__file__), "..", "data")
new = analysis.load(os.path.join(D, "snapshot_2026-11-13.json"))
old = analysis.load(os.path.join(D, "snapshot_2026-10-28.json"))
labels = json.load(open(os.path.join(D, "option_labels.json")))

def test_pct():
    assert analysis.pct_off({"regular": 169, "sale": 67.60}) == 60
    assert analysis.pct_off({"regular": 100, "sale": None}) == 0

def test_snapshot_sane():
    ps = new["products"]
    assert len({p["slug"] for p in ps}) == len(ps)
    for p in ps:
        if p["sale"] is not None:
            assert p["sale"] < p["regular"]

def test_overview():
    o = analysis.overview(new["products"])
    assert o["apparel_count"] == len([p for p in new["products"] if not p["accessory"]])
    assert 0 < o["share_on_sale"] < 1
    assert o["max_discount"] == 60

def test_inconsistent_families():
    fams = {f["family"]: f for f in analysis.inconsistent_families(new["products"])}
    assert "V-neck dress" in fams            # orchid 60% vs black 40%
    assert fams["V-neck dress"]["spread"] == 20
    assert fams["Pleated trousers"]["spread"] == 20

def test_creep():
    c = analysis.creep(old, new)
    assert c["compared"] >= 30
    names = {r["name"]: r for r in c["rows"]}
    assert names["Jacket Yellow Saffron"]["from_pct"] == 0 and names["Jacket Yellow Saffron"]["to_pct"] == 30
    assert names["Regular-fit Trousers Navy"]["from_pct"] == 15 and names["Regular-fit Trousers Navy"]["to_pct"] == 30
    assert names["Jacket Dove"]["lost_black_line"] is True
    assert "Relax Wear Trousers Black" not in names   # unchanged at 30%

def test_sizes():
    assert normalise.normalise_size("S-L")["type"] == "RANGE"
    assert normalise.normalise_size("S-L")["covers"] == ["S", "M", "L"]
    assert normalise.normalise_size("XL/2XL")["type"] == "PAIR"
    assert normalise.normalise_size("One size( S-XL)")["type"] == "ONE_SIZE"
    assert normalise.normalise_size("Personalized size (XXS-3XL)")["type"] == "CUSTOM"
    assert normalise.normalise_size("50 ml")["type"] == "VOLUME"
    assert normalise.normalise_size("2XL")["type"] == "SIZE"
    unknown = [l["label"] for l in labels["sizes"] if normalise.normalise_size(l["label"])["type"] == "UNKNOWN"]
    assert unknown == []

def test_colours():
    assert normalise.normalise_colour("Dark Grey")["family"] == "Grey"
    assert normalise.normalise_colour("Light gray")["family"] == "Grey"
    assert normalise.normalise_colour("Black silk")["family"] == "Black"
    assert normalise.normalise_colour("Greyish Beige")["family"] == "Beige"
    assert normalise.normalise_colour("Grayish purple")["family"] == "Purple"
    assert normalise.normalise_colour("Brown/White")["family"].startswith("Multi")
    assert normalise.normalise_colour("Red 3/4 sleeves")["family"] == "Red"
    assert normalise.normalise_colour("Red 3/4 sleeves")["descriptors"] == ["3/4 sleeves"]
    others = [l["label"] for l in labels["colours"] if normalise.normalise_colour(l["label"])["family"] == "Other"]
    assert others == [], others

def test_omnibus():
    hist = omnibus.parse_history("2026-09-01,179\n2026-10-20,125\n2026-11-01,179\n2026-11-13,107.40")
    # discount starts 13 Nov; 30-day window (14 Oct - 12 Nov) includes the 125 price
    r = omnibus.check(hist, date(2026, 11, 13), 179, 107.40)
    assert r["status"] == "RISK" and r["lowest_30d"] == 125
    assert r["claimed_pct"] == 40 and r["true_pct"] == 14
    ok = omnibus.check(omnibus.parse_history("2026-09-01,179"), date(2026, 11, 13), 179, 107.40)
    assert ok["status"] == "OK"

def test_tracker_parse():
    payload = {"products": [{"handle": "x", "title": "X", "variants": [
        {"title": "S", "sku": "A1", "price": "89.00", "compare_at_price": "149.00", "available": True},
        {"title": "M", "sku": "A1", "price": "89.00", "compare_at_price": None, "available": False}]}]}
    rows = track_prices.parse_products(payload, today="2026-11-13")
    assert len(rows) == 2 and rows[0]["compare_at_price"] == "149.00" and rows[1]["compare_at_price"] == ""
    # duplicate SKU across variants is exactly the data-quality issue we flag
    assert len({r["sku"] for r in rows}) == 1

def test_new_tag_claim():
    # "items still tagged New were already 20-30% off" must hold for the current snapshot
    c = analysis.creep(old, new)
    cur = {p["name"]: p for p in new["products"]}
    new_rows = [r for r in c["rows"] if r["was_new"]]
    assert len(new_rows) == 4
    for r in new_rows:
        assert "N" in cur[r["name"]]["tags"]
        assert 20 <= r["to_pct"] <= 30

def test_black_line_claim():
    c = analysis.creep(old, new)
    lost = [r for r in c["rows"] if r["lost_black_line"]]
    assert len(lost) == 5 and all(r["to_pct"] > 0 for r in lost)

def test_best_seller_claim():
    # text says: Orchid 60, Libre Green/Navy 40, and seven more at 30-40%
    best = {p["name"]: analysis.pct_off(p) for p in new["products"] if "B" in p["tags"]}
    assert best["V-Neck Dress Orchid"] == 60
    assert best["Libre Dress Green"] == best["Libre Dress Navy"] == 40
    others = [v for k, v in best.items() if k not in ("V-Neck Dress Orchid", "Libre Dress Green", "Libre Dress Navy") and v >= 30]
    assert len(others) == 7 and all(30 <= v <= 40 for v in others)

def test_site_builds():
    site = build_site.build()
    index = open(os.path.join(site, "index.html"), encoding="utf-8").read()
    o = analysis.overview(new["products"])
    assert f'{o["on_sale"]} of {o["apparel_count"]}' in index
    assert "66 → 15" in index and "27 → 6" in index
    for f in ("style.css", "app.js", "_headers", "favicon.svg", "robots.txt"):
        assert os.path.exists(os.path.join(site, f)), f
    assert "<style" not in index and 'style="' not in index   # strict CSP: no inline styles
    assert "<script>" not in index                              # no inline scripts

if __name__ == "__main__":
    # tiny runner so no extra packages are needed:  python tests/test_all.py
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("ok  ", name)
            except Exception as e:
                failed += 1; print("FAIL", name, "->", repr(e))
    sys.exit(1 if failed else 0)
