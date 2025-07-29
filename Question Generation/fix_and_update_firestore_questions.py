import openai
import json
import time
from google.cloud import firestore
from google.oauth2 import service_account

# === CONFIGURATION ===
OPENAI_API_KEY_PATH = "C:/The_GPK/Entry.txt"
FIRESTORE_KEY_PATH = "C:/Users/aq_pu/Desktop/soccer-trivia-app/firestore-import/serviceAccount.json"
FIRESTORE_COLLECTION = "triviaQuestions"
TARGET_SUBCATEGORY = "Premier League"
BATCH_SIZE = 20
DRY_RUN = True  # Set to False to allow Firestore updates
MODEL = "gpt-4-turbo"

# === LOAD API KEY ===
with open(OPENAI_API_KEY_PATH, "r") as f:
    openai.api_key = f.read().strip()

# === FIRESTORE CONNECTION ===
credentials = service_account.Credentials.from_service_account_file(FIRESTORE_KEY_PATH)
db = firestore.Client(credentials=credentials)
collection = db.collection(FIRESTORE_COLLECTION)

# === FETCH MATCHING DOCUMENTS ===
docs = collection.where("subcategories", "array_contains", TARGET_SUBCATEGORY).stream()
questions = []
doc_refs = []

for doc in docs:
    data = doc.to_dict()
    if all(k in data for k in ["question", "answer", "options", "category", "subcategories", "difficulty", "source"]):
        questions.append(data)
        doc_refs.append(doc.reference)

print(f"✅ Found {len(questions)} questions under subcategory '{TARGET_SUBCATEGORY}'.")

# === BATCH PROCESS WITH OPENAI ===
def gpt_fix_batch(batch):
    prompt = (
        "Review each soccer trivia question below. For each one:
"
        "- Ensure the answer is correct
"
        "- Ensure the options are valid
"
        "- Improve the question phrasing if needed
"
        "- Return revised JSON only, no commentary

"
        f"Questions:
{json.dumps(batch, indent=2)}"
    )

    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    fixed_json = response.choices[0].message["content"]
    try:
        return json.loads(fixed_json)
    except json.JSONDecodeError:
        print("❌ GPT returned invalid JSON.")
        return []

# === MAIN LOOP ===
log = []
for i in range(0, len(questions), BATCH_SIZE):
    batch = questions[i:i + BATCH_SIZE]
    refs = doc_refs[i:i + BATCH_SIZE]
    print(f"🔍 Reviewing batch {i // BATCH_SIZE + 1}...")

    fixed_batch = gpt_fix_batch(batch)
    for orig, fixed, ref in zip(batch, fixed_batch, refs):
        if (
            orig["question"] != fixed["question"] or
            orig["answer"] != fixed["answer"] or
            orig["options"] != fixed["options"]
        ):
            log.append({"original": orig, "fixed": fixed})
            print(f"✏️ Updating: {orig['question'][:60]}...")
            if not DRY_RUN:
                ref.update(fixed)

# === SAVE LOG ===
timestamp = int(time.time())
log_file = f"fixed_questions_log_{timestamp}.json"
with open(log_file, "w", encoding="utf-8") as f:
    json.dump(log, f, indent=2, ensure_ascii=False)

print(f"✅ Done. {len(log)} questions revised. Log saved to {log_file}")
