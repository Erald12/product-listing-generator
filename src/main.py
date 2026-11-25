import csv
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

from src.generate import generate_listing
from src.rules import check_listing, load_terms, spec_problems

ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = ROOT / "incoming" / "products"
BANNED_FILE = ROOT / "guidelines" / "banned_terms.txt"
OUTPUT = ROOT / "output"
DRAFTS = OUTPUT / "drafts"
STATE_FILE = OUTPUT / "processed.json"
RUN_LOG = OUTPUT / "run_log.csv"

LOG_COLS = ["timestamp", "files_seen", "processed", "ready", "needs_edit",
            "invalid_spec", "failed", "skipped", "seconds", "status"]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def write_draft(name, spec, listing, problems):
    DRAFTS.mkdir(parents=True, exist_ok=True)
    status = "NEEDS EDIT" if problems else "READY FOR REVIEW"
    lines = [f"# {spec['sku']}: {spec['product_name']}", "", f"**Status:** {status}", ""]
    if problems:
        lines += ["**Problems found:**"] + [f"- {p}" for p in problems] + [""]
    lines += ["## Title", "", listing["title"], "", "## Bullets", ""]
    lines += [f"{i}. {b}" for i, b in enumerate(listing["bullets"], 1)]
    lines += ["", "## Description", "", listing["description"], ""]
    (DRAFTS / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")


def process_file(path, banned):
    spec = json.loads(path.read_text(encoding="utf-8"))
    problems = spec_problems(spec)
    if problems:
        return "invalid_spec", problems

    listing = generate_listing(spec)
    if listing is None:
        return "failed", ["Claude reply could not be parsed after retry"]

    problems = check_listing(listing, spec, banned)
    write_draft(path.stem, spec, listing, problems)
    return ("needs_edit" if problems else "ready"), problems


def append_run_log(entry):
    new_file = not RUN_LOG.exists()
    with RUN_LOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLS)
        if new_file:
            writer.writeheader()
        writer.writerow(entry)


def run():
    OUTPUT.mkdir(exist_ok=True)
    start = time.time()
    state = load_state()
    banned = load_terms(BANNED_FILE)
    files = sorted(SPEC_DIR.glob("*.json"))
    counts = {"ready": 0, "needs_edit": 0, "invalid_spec": 0, "failed": 0, "skipped": 0}
    status = "crashed"

    try:
        for path in files:
            digest = file_hash(path)
            if state.get(path.name, {}).get("hash") == digest:
                counts["skipped"] += 1  # unchanged since the last run
                continue

            try:
                outcome, detail = process_file(path, banned)
            except Exception as e:  # one bad file shouldn't stop the batch
                outcome, detail = "failed", [f"{type(e).__name__}: {e}"]

            counts[outcome] += 1
            print(f"{path.name}: {outcome}")
            if outcome == "failed":
                # Don't remember failures, so the next run retries them.
                state.pop(path.name, None)
            else:
                state[path.name] = {
                    "hash": digest,
                    "outcome": outcome,
                    "detail": "; ".join(detail),
                    "date": datetime.now().isoformat(timespec="seconds"),
                }

        failures = counts["failed"] + counts["invalid_spec"]
        status = "ok" if failures == 0 else "partial"
    finally:
        save_state(state)
        processed = counts["ready"] + counts["needs_edit"] + counts["invalid_spec"] + counts["failed"]
        append_run_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "files_seen": len(files),
            "processed": processed,
            "ready": counts["ready"],
            "needs_edit": counts["needs_edit"],
            "invalid_spec": counts["invalid_spec"],
            "failed": counts["failed"],
            "skipped": counts["skipped"],
            "seconds": round(time.time() - start, 1),
            "status": status,
        })

    print(f"Done: {counts['ready']} ready, {counts['needs_edit']} need edit, "
          f"{counts['invalid_spec']} invalid spec, {counts['failed']} failed, "
          f"{counts['skipped']} unchanged. Drafts are in output\\drafts.")


if __name__ == "__main__":
    run()