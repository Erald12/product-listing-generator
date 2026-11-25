import json
import re

TITLE_MAX = 150        # conservative; check the current limit for the listing's category
BULLET_MAX = 250
BULLET_COUNT = 5
DESCRIPTION_MAX = 2000

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
REQUIRED_FIELDS = ["sku", "product_name", "features"]


def load_terms(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith("//")]


def normalize_number(text):
    return text.replace(",", "")


def spec_problems(spec):
    problems = [f"missing field: {f}" for f in REQUIRED_FIELDS if not spec.get(f)]
    if spec.get("features") and not isinstance(spec["features"], list):
        problems.append("features must be a list")
    return problems


def spec_numbers(spec):
    """Every number that appears anywhere in the spec file."""
    text = json.dumps(spec, ensure_ascii=False)
    return {normalize_number(n) for n in NUMBER.findall(text)}


def check_listing(listing, spec, banned_terms):
    """Return a list of problems. An empty list means the draft passes these checks."""
    problems = []
    title = listing.get("title", "").strip()
    bullets = listing.get("bullets", [])
    description = listing.get("description", "").strip()
    parts = [title, *bullets, description]

    if not title:
        problems.append("missing title")
    elif len(title) > TITLE_MAX:
        problems.append(f"title is {len(title)} chars (max {TITLE_MAX})")
    elif spec["product_name"].lower() not in title.lower():
        problems.append("title does not include the product name")

    if len(bullets) != BULLET_COUNT:
        problems.append(f"{len(bullets)} bullets (need {BULLET_COUNT})")
    for i, bullet in enumerate(bullets, 1):
        if len(bullet) > BULLET_MAX:
            problems.append(f"bullet {i} is {len(bullet)} chars (max {BULLET_MAX})")

    if len(description) > DESCRIPTION_MAX:
        problems.append(f"description is {len(description)} chars (max {DESCRIPTION_MAX})")

    joined = " ".join(parts)
    for term in banned_terms:
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", joined, re.IGNORECASE):
            problems.append(f"banned term: {term}")

    allowed = spec_numbers(spec)
    for part in parts:
        for n in NUMBER.findall(part):
            if normalize_number(n) not in allowed:
                problems.append(f"number not in spec: {n}")

    return problems