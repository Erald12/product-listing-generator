# Product Listing Generator

A Python workflow that reads product spec files, asks Claude to draft an Amazon-style listing (title, five bullets, description) using only facts from the spec, checks the draft with rules in Python, and writes a review file. Nothing is published automatically. A person reviews every draft before it goes to Seller Central.

## What it does

For each `.json` spec in `incoming/products/`:

1. Validates the spec (required fields are present and `features` is a list).
2. Sends the spec to Claude with rules: use only stated facts, no superlatives, no prices or promotions, exact product name in the title, five bullets.
3. Checks the draft in Python:
   - Title length and inclusion of the product name
   - Exactly five bullets, and bullet and description length limits
   - Banned terms from `guidelines/banned_terms.txt`
   - Every number in the draft must appear in the spec
4. Writes `output/drafts/<spec-name>.md`, marked **READY FOR REVIEW** or **NEEDS EDIT**, with the problems listed.
5. Skips any spec that hasn't changed since the last run, so API calls are only spent on new or edited specs.
6. Appends a row to `output/run_log.csv` for every run.

## What it does not do

- It does not verify that claims are true. It checks the draft against the spec, and the spec is only as accurate as the data you give it.
- It does not check Amazon's current policies for your category. Check those yourself.
- It does not publish or edit listings in Seller Central.

## Project structure

```
product-listing-generator/
├── requirements.txt
├── .env.example
├── .gitignore
├── run_listing_generator.bat
├── guidelines/
│   └── banned_terms.txt      # one term per line; lines starting with // are comments
├── incoming/
│   └── products/             # one JSON spec per product
├── output/                   # generated; not committed
│   ├── drafts/               # one .md draft per spec
│   ├── processed.json        # tracks file hashes to skip unchanged specs
│   └── run_log.csv           # one row per run
└── src/
    ├── rules.py              # Python checks: spec validation and draft checks
    ├── generate.py           # Claude call and JSON parsing
    └── main.py               # file loop, state, drafts, run log
```

## Spec format

```json
{
  "sku": "WCS-001",
  "product_name": "Wooden Counting Set",
  "material": "Natural beech wood, water-based paint",
  "age_range": "3 to 6 years",
  "contents": "40 colored counting blocks, 1 storage tray",
  "dimensions": "24 x 18 x 6 cm",
  "features": [
    "Helps children practice counting from 1 to 10",
    "Blocks stack and sort by color"
  ],
  "certifications": "None stated"
}
```

Required: `sku`, `product_name`, `features`. Other fields are optional, but the more facts the spec contains, the better the draft.

## Setup

Requires Python 3.10 or later and an Anthropic API key.

```powershell
cd D:\PythonProject\product-listing-generator
python -m venv ..\.venv        # skip if the shared venv already exists
..\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
mkdir output
```

Open `.env` and replace `your_key_here` with your API key. Do not commit this file.

## Run

From the project root:

```powershell
python -m src.main
```

Run it with `-m` from the project root. Running `src\main.py` directly causes import errors.

Then open the drafts in `output\drafts\`. Each draft lists any problems the checks found.

## Scheduling

To run it daily at 07:00 on Windows:

```powershell
schtasks /create /tn "ListingGenerator" /tr "D:\PythonProject\product-listing-generator\run_listing_generator.bat" /sc daily /st 07:00
```

Test the scheduled task once with `schtasks /run /tn "ListingGenerator"`, then check `output\run.log` and `output\run_log.csv`.

## Run log

| Column | Meaning |
|---|---|
| `timestamp` | When the run started |
| `files_seen` | Spec files found |
| `processed` | Files sent to Claude this run |
| `ready` / `needs_edit` | Drafts that passed / failed the checks |
| `invalid_spec` | Specs missing required fields |
| `failed` | Files where Claude's reply couldn't be parsed or an error occurred |
| `skipped` | Unchanged files, not reprocessed |
| `seconds` | Run duration |
| `status` | `ok` if no failures, `partial` if any failed |

A failed file is not remembered, so the next run retries it.

## Testing the checks

1. Add `beech` to `guidelines\banned_terms.txt`.
2. Delete `output\processed.json`.
3. Run again. Drafts that contain "beech" should be marked **NEEDS EDIT**.
4. Remove the test term and delete `processed.json` again.

## Limitations

- Checks catch numbers, length, banned words, and missing fields. They do not catch invented claims that use different words, such as "organic" or "safe for toddlers," unless those words are added to the banned list.
- Claude can still write a misleading sentence that passes every check. Human review is required.
- Output quality depends on the spec. Thin specs produce thin listings.
- The sample specs are fictional.

## Results

Fill these in from your own measurements before sharing the repo.

- Manual time to write one listing: about ___ minutes (average of ___ attempts)
- Time to review and edit one generated draft: about ___ minutes
- Estimated hours saved per month at ___ listings per month: ___
- Drafts marked READY FOR REVIEW in testing: ___ of ___
- Runs with status `ok` (from `run_log.csv`): ___ of ___
- Measurement period: ___

## Tools

Python 3.10+, the Anthropic API (Claude Haiku), and Claude Code for development.
