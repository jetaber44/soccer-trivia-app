import tkinter as tk
from tkinter import ttk, messagebox
import openai
import json
import time
import os
from datetime import datetime

# === CONFIGURATION ===
API_KEY_PATH = "C:/The_GPK/Entry.txt"
ASSISTANT_ID = "asst_H7vkIlX7pFpBSCQ0U9kKCGfd"
MODEL_COST_PER_1K = 0.005
OUTPUT_DIR = "C:/PhotoCull/TriviaOutput"
MASTER_FILE = os.path.join(OUTPUT_DIR, "master_trivia.json")
ERROR_LOG = os.path.join(OUTPUT_DIR, "trivia_error_log.txt")

CATEGORY_SUBCATEGORY_OPTIONS = [
    "International – World Cup",
    "International – UEFA",
    "International – CONMEBOL",
    "International – CONCACAF",
    "International – CAF",
    "International – AFC",
    "International – OFC",
    "Leagues – Premier League",
    "Leagues – La Liga",
    "Leagues – Serie A",
    "Leagues – Bundesliga",
    "Leagues – Ligue 1",
    "Leagues – MLS",
    "Leagues – Rest of World",
    "Transfers – Transfer Fees",
    "Transfers – Transfer Facts",
    "Transfers – Market Value",
    "Transfers – Career Paths",
    "Time Periods – 2020s",
    "Time Periods – 2010s",
    "Time Periods – 2000s",
    "Time Periods – 1990s",
    "Time Periods – 1980s",
    "Time Periods – 1970s or Earlier",
    "Club Competitions – UEFA Champions League",
    "Club Competitions – Domestic Cups",
    "Club Competitions – Club World Cup",
    "Club Competitions – UEFA Europa League",
    "Club Competitions – UEFA Conference League"
]

DIFFICULTY_OPTIONS = ["easy", "hard", "default"]

# === SETUP OPENAI ===
with open(API_KEY_PATH, "r") as f:
    openai.api_key = f.read().strip()

# === HELPER FUNCTION ===
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
    existing_texts = set(q["question"].strip().lower() for q in master_questions)

    all_unique_questions = []

    for i in range(num_batches):
        this_batch_size = min(batch_size, num_total - i * batch_size)
        user_prompt = (
            f"Generate {this_batch_size} {difficulty} soccer trivia questions.\n"
            f"Category: {category}\n"
            f"Subcategory: {subcategory}\n"
        )

        try:
            print(f"\nWaiting for GPT to generate batch {i+1}...")
            start = time.time()
            thread = openai.beta.threads.create()
            openai.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_prompt)
            run = openai.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=ASSISTANT_ID)
            end = time.time()

            if run.status != "completed":
                raise Exception(f"Batch {i+1} failed: Run did not complete.")

            response = openai.beta.threads.messages.list(thread_id=thread.id)
            answer = response.data[0].content[0].text.value.strip()
            print("\n=== RAW RESPONSE START ===")
            print(answer)
            print("\n=== RAW RESPONSE END ===")

            if not answer:
                raise Exception("Empty response from assistant.")

            if answer.startswith("```"):
                answer = answer.strip("` \n")
                if answer.lower().startswith("json"):
                    answer = answer[4:].strip()

            try:
                questions = json.loads(answer)
            except json.JSONDecodeError as e:
                raise Exception(f"JSON parsing error: {str(e)}")

            batch_unique = [q for q in questions if q["question"].strip().lower() not in existing_texts]
            existing_texts.update(q["question"].strip().lower() for q in batch_unique)
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
root = tk.Tk()
root.title("Soccer Trivia Generator v3")
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

tk.Button(root, text="Generate Trivia Questions", command=submit_request).pack(pady=20)

root.mainloop()
