# BeaA pricing and product data audit

I looked at the public BeaA shop (beaa.eu) on 13 November 2026 and wrote up what I found about discounts,
colour and size options, and the EU rule for showing reduced prices. Everything comes from what a customer can see.
I had no sales, cost or stock data.

The write-up is a small static site in `site/`.

## What's in it

- How deep and how consistent the discounts are (65 of 128 clothing items on sale, 15 to 60% off)
- What changed between 28 October and 13 November (15 of 40 comparable items got a bigger discount)
- The shop's filters: 66 colour labels that are really 15 colours, 27 size labels that are 6 kinds of thing
- A small checker for the "lowest price in the last 30 days" rule, and a script that logs prices daily so the check can run on real history

## Put it online with Netlify

Option 1, no setup: go to https://app.netlify.com/drop and drag the `site` folder onto the page.

Option 2, from GitHub: push this folder to a repo, then in Netlify choose "Add new site", "Import an existing project",
pick the repo. The build command is empty and the publish directory is `site` (already set in `netlify.toml`).

The site is set to `noindex`, so search engines won't list it. Delete the robots lines in `src/build_site.py` if you want it public.

## Run it locally

```
python tests/test_all.py     # 13 tests
python src/build_site.py     # rebuilds site/
```

Python 3.9 or newer, nothing to install.

## Files

```
data/       the two price snapshots and the filter labels, as JSON
src/        analysis.py, normalise.py, omnibus.py, track_prices.py, build_site.py
tests/      test_all.py
site/       the finished website (this is what gets deployed)
```

## Limits

- No cost, sales or stock numbers, so I can't say what the discounts cost in margin.
- Prices change fast. These are snapshots. Page 4 of the shop listing (about 10 products) wasn't available to me.
- The 28 October copy is one listing page, so the real number of discount changes is likely higher.
- `track_prices.py` is tested on a sample feed only, not on the live shop.
- The colour groups and "same garment" groups are my judgement calls.
- Not legal advice.
