import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List

from google.cloud import firestore
from google.oauth2 import service_account

# ====== CONFIG ======
SERVICE_ACCOUNT_PATH = r"C:/Users/aq_pu/Desktop/quizlazo/soccer-trivia-app/firestore-import/serviceAccount.json"
JSONL_PATH = r"C:/Users/aq_pu/Desktop/quizlazo/soccer-trivia-app/factually_correct_questions.jsonl"
COLLECTION_NAME = "triviaQuestions"
# If True, we generate a stable doc ID from a hash of (question + category + subcategories)
# so re-imports won't create duplicates.
UPSERT_BY_HASH = True

# Commit batches under the 500 write limit
BATCH_SIZE = 400

# ====== HELPERS ======
def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def validate_record(rec: Dict[str, Any]) -> List[str]:
    """Return list of error messages (empty list == valid)."""
    errs = []
    # Required fields your app expects
    required = ["question", "options", "answer", "category", "subcategories"]
    for k in required:
        if k not in rec:
            errs.append(f"Missing required field: '{k}'")

    if "options" in rec and not (isinstance(rec["options"], list) and len(rec["options"]) >= 2):
        errs.append("Field 'options' must be a list with at least 2 options")

    if "answer" in rec and "options" in rec:
        if isinstance(rec["options"], list) and rec["answer"] not in rec["options"]:
            errs.append("Field 'answer' must be one of the 'options'")

    if "subcategories" in rec and not isinstance(rec["subcategories"], list):
        errs.append("Field 'subcategories' must be a list")

    return errs

def stable_doc_id(rec: Dict[str, Any]) -> str:
    """
    Create a deterministic, URL-safe ID from question + category + subcategories.
    This prevents dupes on re-imports.
    """
    import hashlib, base64
    core = json.dumps({
        "q": normalize_whitespace(rec.get("question", "")),
        "c": rec.get("category", ""),
        "s": rec.get("subcategories", []),
    }, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(core.encode("utf-8")).digest()
    # Shorten and make URL-safe
    return base64.urlsafe_b64encode(digest)[:22].decode("ascii").rstrip("=")

def clean_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and add timestamps/safety fields without mutating the original."""
    out = dict(rec)

    # Trim strings and normalize whitespace in question/options/answer
    if "question" in out and isinstance(out["question"], str):
        out["question"] = normalize_whitespace(out["question"])

    if "answer" in out and isinstance(out["answer"], str):
        out["answer"] = normalize_whitespace(out["answer"])

    if "options" in out and isinstance(out["options"], list):
        out["options"] = [normalize_whitespace(str(x)) for x in out["options"]]

    # Optional: ensure difficulty exists (your app currently hides it, but DB can keep it)
    if "difficulty" not in out or not out["difficulty"]:
        out["difficulty"] = "default"

    # Add/override timestamps with server timestamps
    out["createdAt"] = firestore.SERVER_TIMESTAMP
    out["updatedAt"] = firestore.SERVER_TIMESTAMP
    return out

def load_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield i, json.loads(line)
            except json.JSONDecodeError as e:
                yield i, {"__parse_error__": str(e)}

def main():
    # Connect to Firestore
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH)
    db = firestore.Client(credentials=credentials)

    col_ref = db.collection(COLLECTION_NAME)
    batch = db.batch()
    pending = 0

    total = 0
    written = 0
    skipped = 0
    parse_errors = 0
    validation_errors = 0
    upserts = 0

    for lineno, rec in load_jsonl(JSONL_PATH):
        total += 1

        if "__parse_error__" in rec:
            parse_errors += 1
            print(f"❌ Line {lineno}: JSON parse error -> {rec['__parse_error__']}")
            continue

        # Validate
        errs = validate_record(rec)
        if errs:
            validation_errors += 1
            print(f"❌ Line {lineno}: Validation failed -> {', '.join(errs)}")
            continue

        # Clean & prep
        doc_data = clean_record(rec)

        # Choose doc ref (upsert) or add (new)
        if UPSERT_BY_HASH:
            doc_id = stable_doc_id(rec)
            doc_ref = col_ref.document(doc_id)
            batch.set(doc_ref, doc_data, merge=True)  # upsert
            upserts += 1
        else:
            doc_ref = col_ref.document()
            batch.set(doc_ref, doc_data)

        pending += 1
        written += 1

        # Commit batch when we hit the size
        if pending >= BATCH_SIZE:
            batch.commit()
            print(f"✅ Committed batch of {pending} writes...")
            batch = db.batch()
            pending = 0

    # Final commit
    if pending > 0:
        batch.commit()
        print(f"✅ Committed final batch of {pending} writes...")

    print("\n🎯 Import complete!")
    print(f"Total lines read:        {total}")
    print(f"Written to Firestore:    {written}")
    print(f" - As upserts (hashed):  {upserts if UPSERT_BY_HASH else 0}")
    print(f"Skipped (parse errors):  {parse_errors}")
    print(f"Skipped (validation):    {validation_errors}")

if __name__ == "__main__":
    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(f"Service account not found at: {SERVICE_ACCOUNT_PATH}")
    if not os.path.exists(JSONL_PATH):
        raise FileNotFoundError(f"JSONL file not found at: {JSONL_PATH}")
    main()
