#!/usr/bin/env python3
"""Build the recipe search index: assets/data/recipes.json.

Reads every recipe .md file, normalizes each ingredient line into a
canonical core (plus quantity fields for the serving scaler), and writes
one JSON index that powers the fuzzy search, the fridge matcher, and the
serving scaler. See DESIGN.md sections 3-4 and 11.2 for the rules.

Run from anywhere (paths are resolved relative to this script):
    python3 scripts/build-search-index.py

The JSON is committed in the same commit as the recipe change, same
rule as the changelog. The script prints a short report: recipes
parsed, distinct cores, one-off cores (alias candidates), and any
lines it could not parse. Nothing is silently dropped.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ["beef", "chicken", "pork", "seafood", "soups", "sides",
            "sauce", "no-meat", "desserts"]
ALIASES_PATH = REPO_ROOT / "scripts" / "aliases.json"
OUTPUT_PATH = REPO_ROOT / "assets" / "data" / "recipes.json"

# Unicode fractions -> decimal value
FRACTIONS = {
    "½": 0.5, "¼": 0.25, "¾": 0.75,
    "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125,
    "⅙": 1 / 6, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875,
}
FRAC_CHARS = "".join(FRACTIONS)

UNITS = {
    "cup", "cups", "tbsp", "tbsps", "tablespoon", "tablespoons",
    "tsp", "tsps", "teaspoon", "teaspoons",
    "lb", "lbs", "pound", "pounds", "oz", "ounce", "ounces",
    "g", "kg", "mg", "ml", "l",
    "clove", "cloves", "can", "cans", "stalk", "stalks",
    "bunch", "bunches", "head", "heads", "slice", "slices",
    "piece", "pieces", "sprig", "sprigs", "pinch", "pinches",
    "dash", "dashes", "quart", "quarts", "pint", "pints",
    "stick", "sticks", "sheet", "sheets", "pack", "packs",
    "bag", "bags", "bottle", "bottles", "jar", "jars",
    "fillet", "fillets", "container", "containers",
}

# Leading size/prep adjectives stripped from a core (Rule 4).
PREP_WORDS = {
    "large", "small", "medium", "fresh", "finely", "roughly",
    "thinly", "thin", "boneless", "skinless", "whole", "diced", "chopped",
    "minced", "sliced", "grated", "shredded", "crushed", "cubed",
    "bone-in", "skin-on", "cooked", "cold",
}

# Small filler words stripped from the start of a core.
LEADING_FILLER = {"a", "an", "of", "the"}

SINGULAR_EXCEPTIONS = {
    "fish", "cheese", "rice", "corn", "beef", "pork", "lamb",
    "bread", "pasta", "spinach", "leaves",
}

# Trailing descriptors that are prep, not identity: "black beans
# drained and rinsed" -> "black beans"; "avocados peeled" -> "avocado".
TRAILING_DESCRIPTORS = {
    "drained", "rinsed", "peeled", "cooked", "crisp", "crumbled",
    "divided",
}
BUNDLES = {
    "salt and pepper": ["salt", "black pepper"],
    "salt & pepper": ["salt", "black pepper"],
    "salt and freshly ground black pepper": ["salt", "black pepper"],
    "salt & black pepper": ["salt", "black pepper"],
}


def _parse_number(text):
    """Parse a leading number: int, decimal, fraction, or mixed number.

    Returns (value, rest) or (None, text) when no number leads.
    """
    text = text.strip()
    # Mixed number with slash fraction: "1 1/2"
    m = re.match(r"^(\d+)\s+(\d+)/(\d+)\b\s*(.*)$", text)
    if m:
        return int(m.group(1)) + int(m.group(2)) / int(m.group(3)), m.group(4)
    # Mixed number with unicode fraction: "1 ½"
    m = re.match(r"^(\d+)\s+([%s])\s*(.*)$" % re.escape(FRAC_CHARS), text)
    if m:
        return int(m.group(1)) + FRACTIONS[m.group(2)], m.group(3)
    # Unicode fraction, with or without an attached whole number: "½", "2½"
    m = re.match(r"^(\d*)([%s])\s*(.*)$" % re.escape(FRAC_CHARS), text)
    if m:
        whole = int(m.group(1)) if m.group(1) else 0
        return whole + FRACTIONS[m.group(2)], m.group(3)
    # Slash fraction: "1/2"
    m = re.match(r"^(\d+)/(\d+)\b\s*(.*)$", text)
    if m:
        return int(m.group(1)) / int(m.group(2)), m.group(3)
    # Decimal or integer: "2.5", "4"
    m = re.match(r"^(\d+(?:\.\d+)?)\b\s*(.*)$", text)
    if m:
        return float(m.group(1)), m.group(2)
    return None, text


def _parse_quantity(text):
    """Parse a leading quantity.

    Returns (amount, unit, range, rest). amount is a float or None;
    range is [lo, hi] or None; unit is a lowercase unit string or None.
    Spelled quantities ("a pinch of") have no amount.
    """
    m = re.match(r"^(a|an)\s+(pinch|dash|handful)\s+of\s+", text, re.I)
    if m:
        return None, None, None, text[m.end():]
    # Attached unit with no space: "8oz sliced mushrooms".
    m = re.match(r"^(\d+(?:\.\d+)?)([a-zA-Z]+)\b\s*(.*)$", text)
    if m and m.group(2).lower() in UNITS:
        return float(m.group(1)), m.group(2).lower(), None, m.group(3)
    value, rest = _parse_number(text)
    if value is None:
        return None, None, None, text
    lo, hi = value, None
    m = re.match(r"^[–—-]\s*(.*)$", rest)
    if m:
        hi_val, rest2 = _parse_number(m.group(1))
        if hi_val is not None:
            hi, rest = hi_val, rest2
            # "1 - 1/2 tbsp" means 1 to 1 1/2 tbsp: a bare fraction
            # after the dash is shorthand for whole + fraction.
            if hi < lo:
                hi = lo + hi
    unit = None
    m = re.match(r"^([A-Za-z]+)\b\s*(.*)$", rest)
    if m and m.group(1).lower() in UNITS:
        unit, rest = m.group(1).lower(), m.group(2)
    if hi is not None:
        return None, unit, [lo, hi], rest
    return lo, unit, None, rest


def _singularize(word):
    w = word.lower()
    if w in SINGULAR_EXCEPTIONS:
        return w
    if w == "leaves":
        return "leaf"
    if w.endswith("oes"):
        return w[:-2]  # tomatoes -> tomato
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "y"  # berries -> berry
    if w.endswith("ses") or w.endswith("ss"):
        return w
    if w.endswith("s") and not w.endswith("us") and not w.endswith("is"):
        return w[:-1]
    return w


def _normalize_core(text, aliases):
    """Normalize one candidate ingredient text to a canonical core."""
    t = text.strip().lower()
    # Matthew's ruling: sliced, chopped, and diced bell pepper are
    # three different preparations, so the prep word stays in the core.
    bell_prep = None
    if "bell pepper" in t:
        for prep in ("sliced", "chopped", "diced"):
            if re.search(r"\b" + prep + r"\b", t):
                bell_prep = prep
                break
    # Strip leading size/prep words, filler words, and packaging words
    # ("bag coleslaw mix", "can diced tomatoes" — no quantity, so the
    # unit was never consumed as one). Repeatedly. A leading comma or
    # stray period can be left behind after stripping a word
    # ("boneless, skinless chicken thighs"), so strip those too.
    # A leading size in inches ("3 in corn on the cob", "3-inch corn")
    # is not identity either.
    t = re.sub(r"^\d+\s*-?\s*(in|inch|inches)\b\s*", "", t)
    while True:
        t = t.lstrip(", .;:").strip()
        m = re.match(r"^([a-z][a-z-]*),?\s+(.*)$", t)
        if m and (m.group(1) in PREP_WORDS or m.group(1) in LEADING_FILLER
                  or m.group(1) in UNITS):
            t = m.group(2)
        else:
            break
    # Cut at the first comma: everything after it is prep, not identity.
    t = t.split(",")[0].strip()
    # "cut into ..." phrases are prep, not identity: "asparagus cut
    # into 1/2 inch pieces" -> "asparagus". Same for "cooked according
    # to package instructions/directions".
    t = re.sub(r"\b(cut|sliced|diced|chopped)\s+into\b.*$", "", t).strip()
    t = re.sub(r"\bcooked according to\b.*$", "", t).strip()
    words = t.split()
    if bell_prep is not None:
        words = [w for w in words if w != bell_prep]
        # Other trailing prep words still go ("bell peppers thinly
        # sliced" -> "bell pepper" + "sliced"), then the noun is
        # singularized before the prep is re-attached.
        while words and words[-1] in PREP_WORDS:
            words.pop()
    else:
        # Strip trailing prep words ("garlic minced" -> "garlic") and
        # trailing descriptors ("black beans drained and rinsed").
        while words and (words[-1] in PREP_WORDS
                         or words[-1] in TRAILING_DESCRIPTORS
                         or words[-1] == "and"):
            words.pop()
    if not words:
        return ""
    pre = " ".join(words)
    words[-1] = _singularize(words[-1])
    t = " ".join(words)
    # Alias lookup on the pre-singularized core first ("scallions"),
    # then the singularized one.
    core = aliases.get(pre, aliases.get(t, t))
    if bell_prep is not None and bell_prep not in core:
        core = core + " " + bell_prep
    return core.rstrip(".")


def parse_line(raw_line, aliases):
    """Parse one ingredient bullet. Returns a list of ingredient dicts."""
    raw = raw_line.strip()
    text = raw[1:].strip() if raw.startswith("-") else raw
    # Normalize the Unicode fraction slash (U+2044) to ASCII "/".
    text = text.replace("⁄", "/")
    lower = text.lower()
    flags = []
    paren_alts = []

    def _paren(match):
        inner = match.group(1).strip().lower()
        if inner == "optional":
            flags.append("optional")
        elif inner in ("for garnish", "for serving", "for topping"):
            flags.append("garnish")
        elif inner.startswith("or "):
            paren_alts.append(inner[3:].strip())
        elif inner.startswith("such as "):
            for part in inner[8:].split(","):
                part = re.sub(r"^or\s+", "", part.strip())
                if part:
                    paren_alts.append(part)
        # Any other parenthetical is a descriptor; drop it.
        return " "

    lower = re.sub(r"\(([^)]*)\)", _paren, lower)
    m = re.search(r"(?:,\s*)?for (garnish|serving|topping)[\s.]*$", lower)
    if m:
        flags.append("garnish")
        lower = lower[:m.start()]
    if "to taste" in lower:
        flags.append("to_taste")
        lower = lower.replace("to taste", " ")
    lower = re.sub(r"\s+", " ", lower).strip()

    # Rule 1: split bundles first ("Salt and pepper to taste").
    for bundle, parts in BUNDLES.items():
        if lower.startswith(bundle):
            return [{
                "raw": raw, "core": core,
                "amount": None, "unit": None, "range": None,
                "alternatives": [], "flags": sorted(set(flags)),
            } for core in parts]

    # Rule 2: "or" alternatives — having either one counts as a hit.
    # The first candidate can normalize to nothing ("sliced fresh or
    # pickled jalapeno"), so track the first real result explicitly
    # instead of assuming results[0] exists.
    candidates = re.split(r"\s+or\s+", lower)
    results = []
    first = None
    for cand in candidates:
        amount, unit, rng, rest = _parse_quantity(cand)
        core = _normalize_core(rest, aliases)
        if not core:
            continue
        if first is None:
            first = {
                "raw": raw, "core": core,
                "amount": amount, "unit": unit, "range": rng,
                "alternatives": [],
                "flags": sorted(set(flags)),
            }
            results.append(first)
        else:
            first["alternatives"].append(core)
    for alt in paren_alts:
        core = _normalize_core(alt, aliases)
        if (core and first is not None and core not in first["alternatives"]
                and core != first["core"]):
            first["alternatives"].append(core)
    return results


# Bullets that parsed to nothing at all (silent drops). Collected
# during the run and printed in the report so they stay visible.
_UNPARSED_LINES = []


def parse_recipe(path, aliases):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = None
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = path.stem.replace("-", " ").title()
    rel = path.relative_to(REPO_ROOT)
    ingredients = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            in_section = line.strip() == "## Ingredients"
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            got = parse_line(stripped, aliases)
            if not got:
                _UNPARSED_LINES.append((str(rel), stripped))
            ingredients.extend(got)
    return {
        "slug": str(rel.with_suffix("")),
        "title": title,
        "section": rel.parts[0],
        "path": str(rel),
        "ingredients": ingredients,
    }


def main():
    aliases = {}
    if ALIASES_PATH.exists():
        aliases = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    recipes = []
    for section in SECTIONS:
        folder = REPO_ROOT / section
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            if path.name == "README.md":
                continue
            recipes.append(parse_recipe(path, aliases))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(recipes, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    total = sum(len(r["ingredients"]) for r in recipes)
    cores = {}
    empty = 0
    no_qty = 0
    for recipe in recipes:
        if not recipe["ingredients"]:
            print("WARN: no ingredients parsed: %s" % recipe["path"])
        for ing in recipe["ingredients"]:
            if not ing["core"]:
                empty += 1
            cores[ing["core"]] = cores.get(ing["core"], 0) + 1
            if ing["amount"] is None and ing["range"] is None:
                no_qty += 1
    if _UNPARSED_LINES:
        print("lines that parsed to nothing: %d" % len(_UNPARSED_LINES))
        for path, line in _UNPARSED_LINES:
            print("  %s :: %s" % (path, line))
    once = sorted(c for c, n in cores.items() if n == 1)
    print("recipes: %d" % len(recipes))
    print("ingredient entries: %d" % total)
    print("distinct cores: %d" % len(cores))
    print("cores appearing once: %d (alias candidates)" % len(once))
    for core in once[:50]:
        print("  once: %s" % core)
    if len(once) > 50:
        print("  ... and %d more" % (len(once) - 50))
    print("empty cores (unparseable): %d" % empty)
    print("entries with no quantity: %d" % no_qty)
    print("wrote %s" % OUTPUT_PATH)


if __name__ == "__main__":
    main()
