import json

import anthropic
from dotenv import load_dotenv

load_dotenv()
MODEL = "claude-haiku-5-5"
client = anthropic.Anthropic(max_retries=3)

PROMPT = """Write an Amazon product listing from the product spec below.

Rules:
- Use ONLY facts stated in the spec. Do not add materials, ages, certifications, awards, or claims that are not in the spec.
- Do not use superlatives or unverifiable claims (best, #1, guaranteed, clinically proven, cure, safest).
- Do not stuff keywords. Write for a shopper reading the page.
- Do not mention prices, discounts, sales, or shipping offers.
- The title must include the exact product_name from the spec.
- Write each number exactly as it appears in the spec.
- bullets: exactly 5 bullets, each one sentence, each about one feature or benefit from the spec.
- description: two short paragraphs.

Return only JSON, no other text:
{"title": "...", "bullets": ["...", "...", "...", "...", "..."], "description": "..."}

Product spec:
{SPEC}
"""


def parse_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("title"), str):
        return None
    if not isinstance(data.get("bullets"), list):
        return None
    if not isinstance(data.get("description"), str):
        return None
    return data


def generate_listing(spec):
    prompt = PROMPT.replace("{SPEC}", json.dumps(spec, indent=2, ensure_ascii=False))
    for _ in range(2):  # one retry if the reply can't be parsed
        message = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in message.content if b.type == "text")
        data = parse_json(text)
        if data:
            return data
    return None