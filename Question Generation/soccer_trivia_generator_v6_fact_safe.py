import tkinter as tk
from tkinter import ttk, messagebox
import openai

from tkinter import filedialog
import json
import time
import os
from datetime import datetime
import re
import random
from TOPIC_LIBRARY_LEAGUES import TOPIC_LIBRARY
from google.cloud import firestore
from google.oauth2 import service_account

# === CONFIGURATION ===
API_KEY_PATH = "C:/The_GPK/Entry.txt"
ASSISTANT_ID = "asst_H7vkIlX7pFpBSCQ0U9kKCGfd"
MODEL_COST_PER_1K = 0.005
OUTPUT_DIR = "C:/PhotoCull/TriviaOutput"
MASTER_FILE = os.path.join(OUTPUT_DIR, "master_trivia.json")
ERROR_LOG = os.path.join(OUTPUT_DIR, "trivia_error_log.txt")
FIRESTORE_KEY_PATH = "C:/Users/aq_pu/Desktop/soccer-trivia-app/firestore-import/serviceAccount.json"
FIRESTORE_COLLECTION = "triviaQuestions"

CATEGORY_SUBCATEGORY_OPTIONS = [
    "International – World Cup", "International – UEFA", "International – CONMEBOL", "International – CONCACAF",
    "International – CAF", "International – AFC", "International – OFC", "Leagues – Premier League",
    "Leagues – La Liga", "Leagues – Serie A", "Leagues – Bundesliga", "Leagues – Ligue 1", "Leagues – MLS",
    "Leagues – Rest of World", "Transfers – Transfer Fees", "Transfers – Transfer Facts", "Transfers – Market Value",
    "Transfers – Career Paths", "Time Periods – 2020s", "Time Periods – 2010s", "Time Periods – 2000s",
    "Time Periods – 1990s", "Time Periods – 1980s", "Time Periods – 1970s or Earlier",
    "Club Competitions – UEFA Champions League", "Club Competitions – Domestic Cups",
    "Club Competitions – Club World Cup", "Club Competitions – UEFA Europa League",
    "Club Competitions – UEFA Conference League"
]

DIFFICULTY_OPTIONS = ["easy", "hard", "default"]

# === API KEY ===
with open(API_KEY_PATH, "r") as f:
    api_key = f.read().strip()
client = openai.OpenAI(api_key=api_key)

# === FIRESTORE ===
credentials = service_account.Credentials.from_service_account_file(FIRESTORE_KEY_PATH)
db = firestore.Client(credentials=credentials)

# === HELPER FUNCTIONS ===
def extract_concept_tag(question):
    question = question.lower()
    question = re.sub(r"[^a-z0-9\s\-]", "", question)
    season_matches = re.findall(r"(\d{4})[-–](\d{2,4})", question)
    season_tokens = []
    for start, end in season_matches:
        if len(end) == 2:
            end = str(int(start[:2]) * 100 + int(end))
        season_tokens.append(start + end)
    if not season_tokens and ("all-time" in question or "all time" in question):
        season_tokens.append("alltime")
    elif "as of" in question or "currently" in question or "record" in question:
        season_tokens.append("recent")

    synonyms = {
        "manager": "coach", "coach": "coach", "kit": "uniform", "jersey": "uniform",
        "goal": "score", "goals": "score", "stadium": "venue", "ground": "venue",
        "nickname": "alias", "record": "stat", "shirt": "uniform"
    }
    stop_words = {
        "the", "in", "of", "to", "a", "an", "is", "was", "which", "who",
        "what", "when", "where", "how", "many", "did", "has", "as", "for", "on"
    }
    tokens = [
        synonyms.get(word, word)
        for word in question.split()
        if word not in stop_words
    ]
    all_tokens = sorted(set(tokens + season_tokens))
    return " ".join(all_tokens)

def clean_json_response(answer):
    cleaned = re.sub(r"```(?:json)?\n?", "", answer)  # remove ```json
    cleaned = re.sub(r"```", "", cleaned)             # remove closing ```
    cleaned = cleaned.strip()

    # Trim everything before the first [
    start_index = cleaned.find("[")
    if start_index != -1:
        cleaned = cleaned[start_index:]

    # Trim everything after the final closing ]
    end_index = cleaned.rfind("]")
    if end_index != -1:
        cleaned = cleaned[:end_index + 1]

    return cleaned

def save_questions(category, subcategory, difficulty, all_unique_questions):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trivia_{category}_{subcategory}_{difficulty}_{timestamp}.json".replace(" ", "_")
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(all_unique_questions, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Trivia questions saved to: {filepath}")
    return filepath

def log_error(text):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {text}\n")


def load_fact_file():
    global fact_list
    file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
    if not file_path:
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            fact_list = json.load(f)
        messagebox.showinfo("Facts Loaded", f"{len(fact_list)} facts loaded.")
    except Exception as e:
        messagebox.showerror("Load Error", f"Could not load facts: {str(e)}")

def generate_prompt_from_facts(facts_batch, num_questions):
    prompt = "Here are verified soccer facts:\n"
    for fact in facts_batch:
        prompt += f"- {fact['fact']}\n"
    prompt += f"\nGenerate {num_questions} multiple-choice soccer trivia questions using only these facts.\n"
    prompt += "Output JSON in this format: [{\"question\":..., \"answer\":..., \"options\": [...], \"source\":...}]\n"
    prompt += "Do not hallucinate or invent any information."
    return prompt

# === MAIN LOGIC ===
def submit_request():
    selected_combo = category_box.get()
    difficulty = difficulty_box.get()
    try:
        num_total = int(count_entry.get())
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid number of questions.")
        return

    category, subcategory = [s.strip() for s in selected_combo.split(" – ")]
    batch_size = 20
    num_batches = (num_total + batch_size - 1) // batch_size

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            master_questions = json.load(f)
    else:
        master_questions = []

    existing_concepts = set(q.get("concept_tag") for q in master_questions if q.get("concept_tag"))

    # ✅ NEW: Check Firestore for existing questions too
    existing_firestore_questions = db.collection(FIRESTORE_COLLECTION).stream()
    for doc in existing_firestore_questions:
        q = doc.to_dict()
        concept = extract_concept_tag(q.get("question", ""))
        if concept:
            existing_concepts.add(concept)

    all_unique_questions = []

    for i in range(num_batches):
        this_batch_size = min(batch_size, num_total - i * batch_size)
        selected_topic_text = selected_topic.get()

        if fact_mode_var.get() and fact_list:
            facts_batch = fact_list[i * this_batch_size : i * this_batch_size + this_batch_size]
            if not facts_batch:
                messagebox.showwarning("No More Facts", "You've run out of facts to generate from.")
                break
            user_prompt = generate_prompt_from_facts(facts_batch, this_batch_size)
        else:
            user_prompt = (
            )
            if selected_topic_text:
                user_prompt += f"Focus: {selected_topic_text}\n"
            
        if selected_topic_text:
            user_prompt += f"Focus: {selected_topic_text}\n"

        try:
            print(f"\nWaiting for GPT to generate batch {i+1}...")
            start = time.time()
            thread = client.beta.threads.create()
            client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_prompt)
            run = client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=ASSISTANT_ID)
            end = time.time()

            if run.status != "completed":
                raise Exception(f"Batch {i+1} failed: Run did not complete.")

            response = client.beta.threads.messages.list(thread_id=thread.id)
            answer = response.data[0].content[0].text.value.strip()
            print("\n=== RAW RESPONSE START ===")
            print(answer)
            print("\n=== RAW RESPONSE END ===")

            if not answer:
                raise Exception("Empty response from assistant.")

            answer = clean_json_response(answer)
            print("=== CLEANED START ===")
            print(repr(answer))
            print("=== CLEANED END ===")
            try:
                questions = json.loads(answer)
            except json.JSONDecodeError as e:
                raise Exception(f"JSON parsing error: {e}")

            batch_unique = []

            for q in questions:
                options = q["options"]
                answer = q["answer"]

                if answer not in options:
                    print(f"⚠️ Skipping question — answer not in options: {q['question']}")
                    continue

                random.shuffle(options)
                q["options"] = options
                q["answer"] = answer

                concept = extract_concept_tag(q["question"])
                if concept not in existing_concepts:
                    q["concept_tag"] = concept
                    batch_unique.append(q)
                    existing_concepts.add(concept)

                    try:
                        print(f"📤 Uploading to Firestore: {q['question'][:60]}...")
                        db.collection(FIRESTORE_COLLECTION).add({
                            "question": q["question"],
                            "answer": q["answer"],
                            "options": q["options"],
                            "category": q["category"],
                            "subcategories": q["subcategories"],
                            "difficulty": difficulty,  # Enforce GUI setting
                            "source": q["source"],
                            "createdAt": firestore.SERVER_TIMESTAMP,
                            "updatedAt": firestore.SERVER_TIMESTAMP
                        })
                        print("✅ Upload successful")
                    except Exception as firestore_error:
                        print(f"❌ Firestore upload failed: {firestore_error}")

            all_unique_questions.extend(batch_unique)

            usage = run.usage
            cost = (usage.prompt_tokens + usage.completion_tokens) * MODEL_COST_PER_1K / 1000

            print("==========================")
            print(f"📊 Batch {i+1} Token Usage:")
            print(f"Prompt:     {usage.prompt_tokens}")
            print(f"Completion: {usage.completion_tokens}")
            print(f"Total:      {usage.prompt_tokens + usage.completion_tokens}")
            print(f"💰 Cost:     ${cost:.4f}")
            print(f"⏱️ Time:      {end - start:.2f} seconds")
            print("==========================")

        except Exception as e:
            error_msg = f"Batch {i+1} error: {str(e)}"
            print("❌", error_msg)
            log_error(error_msg)

    if all_unique_questions:
        filepath = save_questions(category, subcategory, difficulty, all_unique_questions)
        master_questions.extend(all_unique_questions)
        with open(MASTER_FILE, "w", encoding="utf-8") as f:
            json.dump(master_questions, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Done", f"Trivia saved to:\n{filepath}")
    else:
        messagebox.showwarning("No Questions", "No new trivia questions were saved.")

# === GUI ===

fact_list = []
root = tk.Tk()
fact_mode_var = tk.BooleanVar()
root.title("Soccer Trivia Generator v4")
root.geometry("540x240")

tk.Label(root, text="Select Category + Subcategory:").pack(pady=(10, 0))
category_box = ttk.Combobox(root, values=CATEGORY_SUBCATEGORY_OPTIONS, width=50)
category_box.pack()
category_box.current(0)

tk.Label(root, text="Select Difficulty:").pack(pady=(10, 0))
difficulty_box = ttk.Combobox(root, values=DIFFICULTY_OPTIONS, width=15)
difficulty_box.pack()
difficulty_box.current(0)

tk.Label(root, text="How many questions?").pack(pady=(10, 0))
count_entry = tk.Entry(root, width=10)
count_entry.pack()
count_entry.insert(0, "50")

tk.Label(root, text="Select Topic (Optional):").pack(pady=(10, 0))

tk.Checkbutton(root, text="Use Verified Fact List", variable=fact_mode_var).pack(pady=(10, 0))
tk.Button(root, text="Upload Fact List (JSON)", command=load_fact_file).pack()
selected_topic = tk.StringVar()
topic_dropdown = ttk.Combobox(root, textvariable=selected_topic, width=50, state="readonly")
topic_dropdown.pack()

def update_topics(event):
    try:
        selected_combo = category_box.get()
        _, subcategory = [s.strip() for s in selected_combo.split("–")]
        topic_list = TOPIC_LIBRARY.get(subcategory, [])
        topic_dropdown["values"] = topic_list
        if topic_list:
            topic_dropdown.current(0)
        else:
            selected_topic.set("")  # Clear selection
    except Exception as e:
        print("❌ Error updating topics:", e)

category_box.bind("<<ComboboxSelected>>", update_topics)

tk.Button(root, text="Generate Trivia Questions", command=submit_request).pack(pady=20)

root.mainloop()