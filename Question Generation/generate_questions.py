import tkinter as tk
from tkinter import ttk, messagebox
import openai
import json
from google.cloud import firestore
from google.oauth2 import service_account
from datetime import datetime

# === CONFIGURATION ===
with open("C:/The_GPK/Entry.txt", "r") as f:
    openai.api_key = f.read().strip()

service_account_path = "C:/Users/aq_pu/Desktop/quizlazo/soccer-trivia-app/firestore-import/serviceAccount.json"
credentials = service_account.Credentials.from_service_account_file(service_account_path)
db = firestore.Client(credentials=credentials)

MODEL = "gpt-4o"
COST_PER_1K_TOKENS = 0.005

CATEGORY_STRUCTURE = {
    "International": ["World Cup", "UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"],
    "Leagues": ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1", "MLS", "Rest of World"],
    "Club Competitions": [
        "UEFA Champions League", "UEFA Europa League", "UEFA Conference League",
        "Domestic Cups", "Club World Cup", "Continental Rest of World"
    ],
    "Transfers": ["Transfer Fees", "Market Value", "Career Paths"],
    "Time Periods": ["2020s", "2010s", "2000s", "1990s", "1980s", "1970s or Earlier"]
}

SYSTEM_PROMPT = """
You are a professional soccer trivia question generator working for a competitive app called Quizlazo.

Your job is to create high-quality, accurate multiple-choice trivia questions based on your soccer knowledge. You do not need to rely on external facts provided by the user. However, every question must be factually correct and clearly worded.

Output must be a JSON array of question objects in this structure:

[
  {
    "question": "...",
    "answer": "...",
    "options": ["...", "...", "...", "..."],
    "category": "...",
    "subcategories": ["..."],
    "difficulty": "default",
    "source": "..."
  }
]

Only use valid categories and subcategories. Skip any questions you're unsure about.
"""

def generate_questions(category, subcategory, count):
    prompt = f"Generate {count} soccer trivia questions for category '{category}' and subcategory '{subcategory}'. Return only valid JSON."
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    content = response.choices[0].message["content"]
    usage = response.usage
    try:
        questions = json.loads(content)
        return questions, usage, content
    except Exception as e:
        return [], usage, content

def upload_to_firestore(questions):
    collection_ref = db.collection("triviaQuestions")
    for q in questions:
        doc_data = {
            "question": q["question"],
            "answer": q["answer"],
            "options": q["options"],
            "category": q["category"],
            "subcategories": q["subcategories"],
            "difficulty": "default",
            "source": q["source"],
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        collection_ref.add(doc_data)

def run_generation():
    category = category_var.get()
    subcategory = subcategory_var.get()
    count = int(count_var.get())
    if not category or not subcategory:
        messagebox.showerror("Missing Fields", "Please select both category and subcategory.")
        return

    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, f"📤 Generating {count} questions for '{subcategory}'...\n")
    root.update()

    questions, usage, raw = generate_questions(category, subcategory, count)

    if questions:
        upload_to_firestore(questions)
        output_text.insert(tk.END, f"✅ Uploaded {len(questions)} questions to Firestore.\n")
    else:
        output_text.insert(tk.END, "⚠️ No questions generated.\n")
        output_text.insert(tk.END, "\n--- Raw Output ---\n" + raw)

    if usage:
        prompt_tokens = usage["prompt_tokens"]
        completion_tokens = usage["completion_tokens"]
        total_tokens = usage["total_tokens"]
        cost = total_tokens * COST_PER_1K_TOKENS / 1000
        output_text.insert(tk.END, f"\n📊 Token Usage:\n")
        output_text.insert(tk.END, f"Prompt:     {prompt_tokens}\n")
        output_text.insert(tk.END, f"Completion: {completion_tokens}\n")
        output_text.insert(tk.END, f"Total:      {total_tokens}\n")
        output_text.insert(tk.END, f"💰 Cost:     ${cost:.4f}\n")

def update_subcategories(*args):
    selected = category_var.get()
    subcats = CATEGORY_STRUCTURE.get(selected, [])
    subcategory_dropdown["values"] = subcats
    if subcats:
        subcategory_var.set(subcats[0])
    else:
        subcategory_var.set("")

# === UI SETUP ===
root = tk.Tk()
root.title("Quizlazo Question Generator")
root.geometry("600x500")

tk.Label(root, text="Category:").pack(pady=(10, 0))
category_var = tk.StringVar()
category_dropdown = ttk.Combobox(root, textvariable=category_var, state="readonly")
category_dropdown["values"] = list(CATEGORY_STRUCTURE.keys())
category_dropdown.pack()
category_dropdown.bind("<<ComboboxSelected>>", update_subcategories)

tk.Label(root, text="Subcategory:").pack(pady=(10, 0))
subcategory_var = tk.StringVar()
subcategory_dropdown = ttk.Combobox(root, textvariable=subcategory_var, state="readonly")
subcategory_dropdown.pack()

tk.Label(root, text="Number of Questions:").pack(pady=(10, 0))
count_var = tk.StringVar(value="10")
count_dropdown = ttk.Combobox(root, textvariable=count_var, state="readonly")
count_dropdown["values"] = [str(i) for i in range(5, 55, 5)]
count_dropdown.pack()

tk.Button(root, text="Generate Questions", command=run_generation, bg="#4CAF50", fg="white", padx=10, pady=5).pack(pady=20)

output_text = tk.Text(root, height=15, wrap="word")
output_text.pack(fill="both", expand=True, padx=10, pady=10)

root.mainloop()
