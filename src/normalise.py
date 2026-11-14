# The shop's filters list 27 size labels and 66 colour labels, many of them
# the same thing spelled differently. This maps them to a short fixed list.
import re

SIZE_ORDER = ["XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]


def _expand(lo, hi):
    if lo in SIZE_ORDER and hi in SIZE_ORDER:
        i, j = SIZE_ORDER.index(lo), SIZE_ORDER.index(hi)
        return SIZE_ORDER[min(i, j):max(i, j) + 1]
    return []


def normalise_size(label):
    # type is one of: SIZE, PAIR (M/L), RANGE (S-L), ONE_SIZE, CUSTOM, VOLUME, UNKNOWN
    raw = label
    s = re.sub(r"\s+", " ", label.strip().upper().replace("( ", "(").replace(" )", ")"))
    s = s.replace("ONE SIZE(", "ONE SIZE (")
    if re.fullmatch(r"\d+\s*ML", s):
        return {"type": "VOLUME", "covers": [s.replace(" ", "")], "raw": raw}
    if s.startswith("PERSONALIZED SIZE"):
        m = re.search(r"\(([A-Z0-9]+)-([A-Z0-9]+)\)", s)
        return {"type": "CUSTOM", "covers": _expand(*m.groups()) if m else [], "raw": raw}
    if s.startswith("ONE SIZE"):
        m = re.search(r"\(([A-Z0-9]+)-([A-Z0-9]+)\)", s)
        return {"type": "ONE_SIZE", "covers": _expand(*m.groups()) if m else [], "raw": raw}
    if s in SIZE_ORDER:
        return {"type": "SIZE", "covers": [s], "raw": raw}
    m = re.fullmatch(r"([A-Z0-9]+)/([A-Z0-9]+)", s)
    if m and m.group(1) in SIZE_ORDER and m.group(2) in SIZE_ORDER:
        return {"type": "PAIR", "covers": _expand(*m.groups()), "raw": raw}
    m = re.fullmatch(r"([A-Z0-9]+)-([A-Z0-9]+)", s)
    if m and m.group(1) in SIZE_ORDER and m.group(2) in SIZE_ORDER:
        return {"type": "RANGE", "covers": _expand(*m.groups()), "raw": raw}
    return {"type": "UNKNOWN", "covers": [], "raw": raw}


# ---- colours -------------------------------------------------------------
DESCRIPTORS = [
    ("eco leather", "eco leather"), ("polyester", "polyester"), ("cotton", "cotton"),
    ("silk", "silk"), ("crushed", "crushed"), ("crinkled", "crinkled"), ("smooth", "smooth"),
    ("python", "python print"), ("with print", "print"), ("stripes", "stripes"),
    ("3/4 sleeves", "3/4 sleeves"), ("long sleeves", "long sleeves"), ("check", "check"),
]
# order matters: more specific words first
FAMILY_RULES = [
    ("beige", "Beige"), ("champagne", "Beige"), ("camel", "Brown"), ("khaki", "Brown"),
    ("purple", "Purple"), ("plum", "Purple"), ("mauve", "Purple"), ("lavender", "Purple"),
    ("green", "Green"), ("basil", "Green"), ("moss", "Green"), ("mint", "Green"), ("forest", "Green"),
    ("blue", "Blue"), ("midnight", "Blue"),
    ("burgundy", "Red"), ("bordo", "Red"), ("cherry", "Red"), ("red", "Red"),
    ("pink", "Pink / Orange"), ("orange", "Pink / Orange"), ("rose", "Pink / Orange"), ("yellow", "Yellow"),
    ("brown", "Brown"), ("grey", "Grey"), ("dove", "Grey"),
    ("black", "Black"), ("white", "White / Cream"), ("milk", "White / Cream"),
    ("cream", "White / Cream"), ("stone", "Beige"), ("vanilla", "White / Cream"),
    ("metallic", "Metallic"),
]


def _family_of_text(text):
    # the last colour word wins: "greyish beige" is a beige, "lavender grey" a grey
    best = None
    for key, fam in FAMILY_RULES:
        pos = text.rfind(key)
        if pos >= 0 and (best is None or pos > best[0] or (pos == best[0] and len(key) > best[2])):
            best = (pos, fam, len(key))
    return best[1] if best else None


def normalise_colour(label):
    raw = label
    s = label.strip().lower().replace("gray", "grey").replace("-", " ")
    s = re.sub(r"\s+", " ", s)
    desc = []
    for key, name in DESCRIPTORS:
        if key in s:
            desc.append(name)
            s = s.replace(key, " ")
    s = re.sub(r"\s+", " ", s).strip()
    if " with " in s or s.startswith("with "):
        s = s.split("with")[0].strip()
    if "/" in s:
        fams = [f for f in (_family_of_text(p.strip()) for p in s.split("/")) if f]
        fams = list(dict.fromkeys(fams))
        return {"family": "Multi (" + " + ".join(fams) + ")" if fams else "Multi",
                "shade": s, "descriptors": desc, "raw": raw}
    family = _family_of_text(s)
    if family is None:
        family = "No colour (print / unspecified)" if (not s or desc) else "Other"
    return {"family": family, "shade": s or "-", "descriptors": desc, "raw": raw}


def summarise(labels, fn, key):
    # group raw labels by their normalised value
    out = {}
    for lab in labels:
        out.setdefault(fn(lab)[key], []).append(lab)
    return out
