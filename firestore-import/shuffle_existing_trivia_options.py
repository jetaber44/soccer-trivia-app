import random
from google.cloud import firestore
from google.oauth2 import service_account

# ===== CONFIG =====
SERVICE_ACCOUNT_PATH = r"C:/Users/aq_pu/Desktop/quizlazo/soccer-trivia-app/firestore-import/serviceAccount.json"
COLLECTION_NAME = "triviaQuestions"
BATCH_SIZE = 400  # under Firestore's 500 limit

# ===== CONNECT =====
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH)
db = firestore.Client(credentials=credentials)
col_ref = db.collection(COLLECTION_NAME)

# ===== PROCESS =====
docs = list(col_ref.stream())
batch = db.batch()
count = 0

for doc in docs:
    data = doc.to_dict() or {}
    options = data.get("options")
    answer = data.get("answer")

    # Only process if options is a list and contains the answer
    if isinstance(options, list) and answer in options and len(options) > 1:
        new_opts = options[:]
        random.shuffle(new_opts)
        batch.update(doc.reference, {
            "options": new_opts,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        count += 1

        if count % BATCH_SIZE == 0:
            batch.commit()
            print(f"✅ Committed {count} updates...")
            batch = db.batch()

# Commit any leftovers
if count % BATCH_SIZE != 0:
    batch.commit()

print(f"\n🎯 Shuffled options for {count} documents in '{COLLECTION_NAME}'.")
