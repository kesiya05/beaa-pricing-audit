# EU rule for advertised price cuts: the "before" price has to be the lowest
# price charged in the 30 days before the cut started (Omnibus Directive).
# This only helps spot problems. It isn't legal advice.
from datetime import date, timedelta


def parse_history(text):
    # lines like "2026-11-01,179" (date of a price change, new price)
    rows = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.lower().startswith("date"):
            continue
        d, p = [x.strip() for x in line.replace(";", ",").split(",")[:2]]
        rows.append((date.fromisoformat(d), float(p.replace("\u20ac", "").replace(",", "."))))
    return sorted(rows)


def price_on(history, day):
    current = None
    for d, p in history:
        if d <= day:
            current = p
        else:
            break
    return current


def lowest_prior_30_days(history, reduction_start):
    prices = []
    day = reduction_start - timedelta(days=30)
    while day < reduction_start:
        p = price_on(history, day)
        if p is not None:
            prices.append(p)
        day += timedelta(days=1)
    return min(prices) if prices else None


def check(history, reduction_start, claimed_regular, sale_price):
    low = lowest_prior_30_days(history, reduction_start)
    if low is None:
        return {"status": "NO_DATA", "message": "No price in the 30 days before the reduction."}
    claimed_pct = round((1 - sale_price / claimed_regular) * 100)
    true_pct = round((1 - sale_price / low) * 100)
    if abs(claimed_regular - low) < 0.005:
        return {"status": "OK", "lowest_30d": low, "claimed_pct": claimed_pct, "true_pct": true_pct,
                "message": "The before price matches the 30-day low."}
    if claimed_regular > low:
        return {"status": "RISK", "lowest_30d": low, "claimed_pct": claimed_pct, "true_pct": true_pct,
                "message": (f"The before price ({claimed_regular:.2f}) is above the lowest price in the "
                            f"previous 30 days ({low:.2f}). The real cut is {true_pct}%, not {claimed_pct}%.")}
    return {"status": "OK", "lowest_30d": low, "claimed_pct": claimed_pct, "true_pct": true_pct,
            "message": "The before price is below the 30-day low, so the claim is on the safe side."}
