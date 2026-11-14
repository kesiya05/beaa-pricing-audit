# Builds the static site into site/ (plain HTML, CSS and one small JS file).
#   python src/build_site.py
import html
import json
import os
import shutil
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import analysis, normalise  # noqa: E402

SITE = os.path.join(ROOT, "site")
e = html.escape


def eur(n):
    s = f"{n:.2f}"
    return "€" + (s[:-3] if s.endswith(".00") else s)


def depth(p):
    return "d1" if p < 30 else ("d2" if p < 50 else "d3")


def off(p):
    if not p:
        return '<span class="zero">none</span>'
    w = p / 60 * 100
    return (f'<span class="pct"><svg viewBox="0 0 100 10" aria-hidden="true"><rect class="{depth(p)}" width="{w:.0f}" height="10"/></svg>{p}%</span>')


def rail(products):
    """Every clothing item as one bar, sorted by discount. Plain SVG, so no inline styles are needed."""
    items = sorted([p for p in products if not p["accessory"]],
                   key=lambda p: (analysis.pct_off(p), p["name"]))
    W, H, T, B = 1000, 250, 14, 22
    plot = H - T - B
    gap = 1.6
    bw = (W - 40) / len(items)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Every clothing item on beaa.eu as one bar, sorted by discount. '
           f'{sum(1 for p in items if p["sale"] is None)} are at full price and {sum(1 for p in items if p["sale"] is not None)} are reduced, '
           f'from 15 to 60 percent.">']
    for g in (0, 30, 60):
        y = T + plot * (1 - g / 60)
        out.append(f'<line class="gl" x1="0" x2="{W - 34}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="tick" x="{W}" y="{y + 4:.1f}" text-anchor="end">{g}%</text>')
    out.append('<g class="bars">')
    for i, p in enumerate(items):
        pc = analysis.pct_off(p)
        x = i * bw
        if pc:
            h = pc / 60 * plot
            cls = depth(pc)
            tip = f'{p["name"]}: {pc}% off'
        else:
            h = 4
            cls = "full"
            tip = f'{p["name"]}: full price'
        out.append(f'<rect class="{cls}" x="{x:.1f}" y="{T + plot - h:.1f}" width="{bw - gap:.1f}" height="{h:.1f}"><title>{e(tip)}</title></rect>')
    out.append("</g></svg>")
    n0 = sum(1 for p in items if p["sale"] is None)
    c1 = sum(1 for p in items if p["sale"] is not None and analysis.pct_off(p) < 30)
    c2 = sum(1 for p in items if p["sale"] is not None and 30 <= analysis.pct_off(p) < 50)
    c3 = sum(1 for p in items if analysis.pct_off(p) >= 50)
    legend = (f'<figcaption><span><i class="k0"></i>Full price ({n0})</span><span><i class="k1"></i>15 to 29% off ({c1})</span>'
              f'<span><i class="k2"></i>30 to 49% off ({c2})</span><span><i class="k3"></i>50 to 60% off ({c3})</span></figcaption>')
    return f'<figure class="rail">{"".join(out)}{legend}</figure>'


SWATCH = {"Brown": "brown", "Grey": "grey", "Blue": "blue", "White / Cream": "white", "Green": "green", "Black": "black",
          "Red": "red", "Purple": "purple", "Beige": "beige", "Metallic": "metallic", "Pink / Orange": "pink",
          "Yellow": "yellow", "Multi (Brown + White / Cream)": "multi1", "Multi (White / Cream + Black)": "multi2",
          "No colour (print / unspecified)": "none"}


def page():
    new = analysis.load(os.path.join(ROOT, "data", "snapshot_2026-11-13.json"))
    old = analysis.load(os.path.join(ROOT, "data", "snapshot_2026-10-28.json"))
    labels = json.load(open(os.path.join(ROOT, "data", "option_labels.json"), encoding="utf-8"))
    ps = new["products"]
    o = analysis.overview(ps)
    fams = analysis.inconsistent_families(ps)
    c = analysis.creep(old, new)

    colour_groups = OrderedDict()
    for l in labels["colours"]:
        colour_groups.setdefault(normalise.normalise_colour(l["label"])["family"], []).append(l["label"])
    colour_groups = sorted(colour_groups.items(), key=lambda kv: -len(kv[1]))
    type_names = {"SIZE": "Single sizes", "PAIR": "Pairs, like M/L", "RANGE": "Ranges, like S-L",
                  "ONE_SIZE": "“One size”, with different ranges", "CUSTOM": "Made to measure",
                  "VOLUME": "Bottle volumes (beauty products)"}
    size_groups = OrderedDict()
    for l in labels["sizes"]:
        size_groups.setdefault(normalise.normalise_size(l["label"])["type"], []).append(l["label"])

    best = sorted([p for p in ps if "B" in p["tags"] and not p["accessory"]], key=lambda p: -analysis.pct_off(p))
    new_tagged = len([r for r in c["rows"] if r["was_new"]])
    lost_bl = len([r for r in c["rows"] if r["lost_black_line"]])
    big = [r["regular"] for r in c["rows"] if "Jacket" in r["name"] or "Coat" in r["name"]]
    common = max(o["buckets"], key=lambda k: o["buckets"][k])

    # --- family tables
    thead = '<thead><tr><th>Item</th><th class="r">List</th><th class="r">Now</th><th class="r">Off</th></tr></thead>'
    fam_rows = "".join(
        f'<tr><td>{e(f["family"])}</td><td class="r">{len(f["items"])}</td><td class="r">{f["low"]}%</td><td class="r">{f["high"]}%</td></tr>'
        for f in fams)
    fam_detail = ""
    for f in fams:
        rows = "".join(
            f'<tr><td>{e(i["name"])}</td><td class="r">{eur(i["regular"])}</td><td class="r">{"" if i["sale"] is None else eur(i["sale"])}</td><td class="r">{off(i["pct"])}</td></tr>'
            for i in f["items"])
        fam_detail += f'<h3>{e(f["family"])}</h3><div class="tablewrap"><table>{thead}<tbody>{rows}</tbody></table></div>'

    best_rows = "".join(
        f'<tr><td>{e(p["name"])}</td><td class="r">{eur(p["regular"])}</td><td class="r">{"" if p["sale"] is None else eur(p["sale"])}</td><td class="r">{off(analysis.pct_off(p))}</td></tr>'
        for p in best)

    creep_rows = ""
    for r in c["rows"]:
        notes = []
        if r["was_new"]:
            notes.append("tagged New")
        if r["lost_black_line"]:
            notes.append("lost Black Line tag")
        before = f'{r["from_pct"]}%' if r["from_pct"] else "full price"
        creep_rows += f'<tr><td>{e(r["name"])}</td><td class="r">{before}</td><td class="r">{off(r["to_pct"])}</td><td>{e(", ".join(notes))}</td></tr>'

    swatches = "".join(
        f'<li><i class="chip sw-{SWATCH.get(f, "none")}"></i><b>{e(f)}</b><span>{len(v)} label{"s" if len(v) != 1 else ""}</span></li>'
        for f, v in colour_groups)
    colour_list = "".join(f'<li><b>{e(f)}</b> ({len(v)}): {e(", ".join(v))}</li>' for f, v in colour_groups)
    size_kinds = "".join(
        f'<div><dt>{e(type_names[t])} <span>{len(v)}</span></dt><dd>{"".join(f"<span>{e(x)}</span>" for x in v)}</dd></div>'
        for t, v in size_groups.items())

    example = "2026-09-01,179\n2026-10-20,125\n2026-11-01,179\n2026-11-13,107.40"
    rail_svg = rail(ps)

    body = f"""
<header class="top"><div class="in"><a class="mark" href="#top">BeaA notes</a>
<a href="#discounts">Discounts</a><a href="#change">Two weeks later</a><a href="#options">Colours and sizes</a><a href="#rule">30-day rule</a><a href="#notes">Method</a></div></header>
<main class="wrap" id="top">
<section class="hero">
<h1>BeaA: a look at pricing and product data</h1>
<p class="dek">I went through beaa.eu page by page and wrote down every price, discount and option label a customer can see. I had no sales, cost or stock numbers, so this is only about what is on the shop. A few things stand out anyway.</p>
<p class="byline">Public shop, 13 November 2026. Kesiya Ann Sony.</p>
<div class="herostat"><span class="big" aria-hidden="true">{o["on_sale"]}</span><p><span class="sr">{o["on_sale"]}</span> of {o["apparel_count"]} clothing items were reduced that day, from 15% up to {o["max_discount"]}% off. Each bar below is one item.</p></div>
{rail_svg}
<ul class="glance">
<li><b>{o["on_sale"]} of {o["apparel_count"]}</b>clothing items are on sale, {round(o["avg_discount"])}% off on average, up to {o["max_discount"]}%</li>
<li><b>{o["best_sellers_30plus"]} of {o["best_sellers"]}</b>items tagged “Best Selling” are 30 to 60% off</li>
<li><b>{c["deeper"]} of {c["compared"]}</b>items were discounted more on 13 November than on 28 October</li>
<li><b>{len(labels["colours"])} → {len(colour_groups)}</b>colour labels in the filter, and the colours they come down to</li>
<li><b>{len(labels["sizes"])} → {len(size_groups)}</b>size labels in the filter, and the kinds of thing they really are</li>
</ul>
</section>

<section class="sec" id="discounts"><h2>About half the range is on sale, best sellers included</h2><div>
<p class="lead">{common}% is the most common discount, but it runs from 15% all the way to {o["max_discount"]}%.</p>
<p><span class="seen">Seen</span>Best sellers are not left out. The V-neck dress in Orchid is tagged Best Selling and is 60% off. The Libre dresses in Green and Navy are 40% off. Another {o["best_sellers_30plus"] - 3} best sellers are 30 to 40% off.</p>
<p>The same garment also gets different discounts depending on colour. The V-neck dress is 60% in Orchid and 40% in Black. The pleated trousers are 60% in Coral and 40% in Desert Shade. Palazzo trousers go from no discount to 40%.</p>
<div class="tablewrap"><table>
<thead><tr><th>Garment</th><th class="r">Colours</th><th class="r">Lowest</th><th class="r">Highest</th></tr></thead>
<tbody>{fam_rows}</tbody></table></div>
<p class="small">Only garments where the gap between colours is 20 points or more.</p>
<details><summary>Every colour, garment by garment</summary><div>{fam_detail}</div></details>
<details><summary>All {o["best_sellers"]} “Best Selling” items and their discounts</summary><div class="tablewrap"><table>{thead}<tbody>{best_rows}</tbody></table></div></details>
<p><span class="mine">My reading</span>If these really are the best sellers, they may sell fine with a smaller discount. A small test on a few of them would show it. Without cost numbers I can’t say how much margin the current level gives up. That is the first thing I would want to measure.</p>
</div></section>

<section class="sec" id="change"><h2>Two weeks later, more of it was reduced</h2><div>
<p class="lead">I also had an older copy of one listing page, from 28 October. {c["compared"]} products are on both. {c["deeper"]} of them were discounted more on 13 November. I found none going the other way.</p>
<div class="tablewrap"><table>
<thead><tr><th>Item</th><th class="r">28 Oct</th><th class="r">13 Nov</th><th>Note</th></tr></thead>
<tbody>{creep_rows}</tbody></table></div>
<p><span class="seen">Seen</span>The jackets and coats were full price on 28 October at {eur(min(big))} to {eur(max(big))}. {new_tagged} items still tagged “New” were already 20 to 30% off. {lost_bl} items carried a “Black Line” tag on 28 October and no longer do. All {lost_bl} are now discounted.</p>
<p><span class="mine">My reading</span>Black Line looks like the full-price range, and items leave it when they go on sale. The shop doesn’t say so, so treat that as a guess. If it is right, a customer can see that nothing is safe from a discount for long.</p>
<p class="small">The 28 October copy covers one listing page only, so the real number of changes is probably higher.</p>
</div></section>

<section class="sec" id="options"><h2>{len(labels["colours"])} colour names that are really {len(colour_groups)} colours</h2><div>
<p class="lead">The colour filter on the shop page has {len(labels["colours"])} entries. Gray, Grey, Dark gray and Dark Grey are four separate choices. Materials and patterns sit in the same list (Black Silk, White crinkled, Dark Blue stripes), and so does a sleeve length (Red 3/4 sleeves). Grouped by the colour word, they come down to {len(colour_groups)}.</p>
<ul class="swatches">{swatches}</ul>
<details><summary>How the {len(labels["colours"])} colour labels group together</summary><div><ul class="plain">{colour_list}</ul><p class="small">The grouping uses the last colour word in each label, so “greyish beige” is a beige. It is a judgement call and easy to change in <code>src/normalise.py</code>.</p></div></details>
<p>The size filter has {len(labels["sizes"])} entries, and they are not all sizes. There are single sizes, pairs like M/L, ranges like S-L, “One size” written with seven different ranges, a made-to-measure option, and bottle volumes for the beauty range. That is {len(size_groups)} different kinds of information in one list.</p>
<dl class="kinds">{size_kinds}</dl>
<p>Why bother: shoppers face a long filter, and a report that asks “how many size L did we sell?” has to add up L, S-L, M/L and “One size”. Any email segment built on colour or size has the same problem.</p>
</div></section>

<section class="sec" id="rule"><h2>The 30-day price rule</h2><div>
<p class="lead">Under the EU Omnibus Directive, when a shop shows a reduced price, the “before” price has to be the lowest price charged in the 30 days before the cut.</p>
<p>Latvia’s consumer protection centre (PTAC) has been checking shops on this. I didn’t see a “lowest price in the last 30 days” line on the shop pages I looked at. Items that sit on sale for weeks, or move between offers every 24 hours, are the cases where the rule bites.</p>
<p>The form below shows how the check works. The prices in the box are made up. They are not BeaA’s.</p>
<form class="checker" id="checker">
<label for="hist">Price history: date of each price change, then the price</label>
<textarea id="hist">{example}</textarea>
<div class="three">
<div><label for="start">Reduction starts</label><input id="start" value="2026-11-13"></div>
<div><label for="regular">“Before” price shown (€)</label><input id="regular" value="179"></div>
<div><label for="sale">Sale price (€)</label><input id="sale" value="107.40"></div>
</div>
<button type="submit">Check this price</button>
<div id="result" role="status"></div>
</form>
<p>In the example the price dropped to €125 for twelve days in October. A sale starting 13 November that shows €179 as the “before” price overstates the cut: it is really 14%, not 40%. To run this on real prices you need the history first. <code>src/track_prices.py</code> logs the prices once a day from the shop’s public product feed.</p>
</div></section>

<section class="sec" id="notes"><h2>How I did it, and what I couldn’t see</h2><div>
<ul class="plain">
<li>Prices, tags and filters come from pages 1 to 3 of beaa.eu/collections/all on 13 November 2026. That is {len(ps)} products. Page 4 (about ten products), gift cards, beauty products and the styling session are not included.</li>
<li>The clothing numbers leave out accessories (belt, bag, cap, socks, eye mask, hair tie).</li>
<li>Discount is one minus the sale price over the shown regular price, rounded.</li>
<li>No sales, costs or stock. So there is nothing here about margin or about whether the discounts bring in extra sales.</li>
<li>Prices change within hours. Everything above is a snapshot.</li>
<li>Code, data and tests are in the project folder, so each number can be re-run. The data files are also here: <a href="data/snapshot_2026-11-13.json">13 Nov</a>, <a href="data/snapshot_2026-10-28.json">28 Oct</a>, <a href="data/option_labels.json">filter labels</a>.</li>
</ul>
</div></section>
<footer>Kesiya Ann Sony. Built from public information only. Not legal advice.</footer>
</main>"""

    desc = "Notes on discounting, product options and the 30-day price rule on beaa.eu, from public information, November 2026."
    head = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>BeaA: a look at pricing and product data</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#e9e6e4">
<meta property="og:title" content="BeaA: a look at pricing and product data">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="article">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preload" href="fonts/bodoni-moda-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="style.css">
</head>
<body>
{body}
<script src="app.js"></script>
</body>
</html>
"""
    return head


def build():
    os.makedirs(SITE, exist_ok=True)
    open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(page())
    for name in ("style.css", "app.js"):
        shutil.copy(os.path.join(HERE, "assets", name), os.path.join(SITE, name))
    os.makedirs(os.path.join(SITE, "fonts"), exist_ok=True)
    for name in os.listdir(os.path.join(HERE, "assets", "fonts")):
        shutil.copy(os.path.join(HERE, "assets", "fonts", name), os.path.join(SITE, "fonts", name))
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    for name in ("snapshot_2026-11-13.json", "snapshot_2026-10-28.json", "option_labels.json"):
        shutil.copy(os.path.join(ROOT, "data", name), os.path.join(SITE, "data", name))
    open(os.path.join(SITE, "favicon.svg"), "w").write(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#4a1d3f"/>'
        '<text x="16" y="24" font-family="Georgia,serif" font-size="22" text-anchor="middle" fill="#e9e6e4">B</text></svg>')
    open(os.path.join(SITE, "robots.txt"), "w").write("User-agent: *\nDisallow: /\n")
    open(os.path.join(SITE, "_headers"), "w").write(
        "/*\n"
        "  Content-Security-Policy: default-src 'none'; img-src 'self' data:; font-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: no-referrer\n"
        "  X-Robots-Tag: noindex, nofollow\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
        )
    return SITE


if __name__ == "__main__":
    print("built", build())
