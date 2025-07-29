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
from pathlib import Path
from google.cloud import firestore
from google.oauth2 import service_account

# === CONFIGURATION ===
API_KEY_PATH = "C:/The_GPK/Entry.txt"
ASSISTANT_ID = "asst_H7vkIlX7pFpBSCQ0U9kKCGfd"
# GPT-4 Turbo pricing (update if model changes)
INPUT_COST_PER_1K = 0.01   # $0.01 per 1K input tokens (GPT-4 Turbo)
OUTPUT_COST_PER_1K = 0.03  # $0.03 per 1K output tokens (GPT-4 Turbo)
OUTPUT_DIR = "C:/PhotoCull/TriviaOutput"
MASTER_FILE = os.path.join(OUTPUT_DIR, "master_trivia.json")
ERROR_LOG = os.path.join(OUTPUT_DIR, "trivia_error_log.txt")
FIRESTORE_KEY_PATH = "C:/Users/aq_pu/Desktop/soccer-trivia-app/firestore-import/serviceAccount.json"
FIRESTORE_COLLECTION = "triviaQuestions"

# Universal soccer categories and subcategories
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
    "Club Competitions – UEFA Europa League",
    "Club Competitions – UEFA Conference League", 
    "Club Competitions – Domestic Cups",
    "Club Competitions – Club World Cup"
]

# Subcategories that should only generate "default" difficulty
DEFAULT_ONLY_SUBCATEGORIES = {
    "CONCACAF", "CAF", "AFC", "OFC", "MLS", "Rest of World",
    "2000s", "1990s", "1980s", "1970s or Earlier"
}

# All other subcategories generate "easy" and "hard" only
EASY_HARD_SUBCATEGORIES = {
    "World Cup", "UEFA", "CONMEBOL", "Premier League", "La Liga", 
    "Serie A", "Bundesliga", "Ligue 1", "Transfer Fees", "Transfer Facts",
    "Market Value", "Career Paths", "2020s", "2010s", "UEFA Champions League",
    "UEFA Europa League", "UEFA Conference League", "Domestic Cups", "Club World Cup"
}

# === API KEY ===
try:
    with open(API_KEY_PATH, "r") as f:
        api_key = f.read().strip()
    client = openai.OpenAI(api_key=api_key)
except Exception as e:
    print(f"❌ Error loading API key: {e}")
    client = None

# === FIRESTORE ===
try:
    credentials = service_account.Credentials.from_service_account_file(FIRESTORE_KEY_PATH)
    db = firestore.Client(credentials=credentials)
except Exception as e:
    print(f"❌ Error initializing Firestore: {e}")
    db = None

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

def get_difficulty_options(subcategory):
    """Get available difficulty options based on subcategory"""
    if subcategory in DEFAULT_ONLY_SUBCATEGORIES:
        return ["default"]
    elif subcategory in EASY_HARD_SUBCATEGORIES:
        return ["easy", "hard"]
    else:
        # Fallback for any unspecified subcategories
        return ["easy", "hard", "default"]

def auto_detect_fact_dump():
    """Try to automatically detect and load any fact dump file"""
    global fact_list, loaded_facts_info
    
    # Look for any fact dump files in common locations
    possible_patterns = [
        "extracted_facts/*_fact_dump.json",
        "extracted_facts/fact_dump.json", 
        "*_fact_dump.json",
        "fact_dump.json"
    ]
    
    found_files = []
    for pattern in possible_patterns:
        found_files.extend(Path(".").glob(pattern))
    
    # Also check absolute paths
    absolute_paths = [
        Path("C:/Users/aq_pu/Desktop/soccer-trivia-app/Question Generation/extracted_facts").glob("*_fact_dump.json")
    ]
    
    for path_gen in absolute_paths:
        found_files.extend(path_gen)
    
    if not found_files:
        return False
    
    # Use the most recently modified file
    fact_dump_path = max(found_files, key=lambda p: p.stat().st_mtime)
    
    try:
        with open(fact_dump_path, "r", encoding="utf-8") as f:
            fact_dump_data = json.load(f)
        
        # Handle both single article and multiple articles format
        if isinstance(fact_dump_data, dict):
            fact_dump_data = [fact_dump_data]
        
        # Convert fact dump format to the expected format
        fact_list = []
        source_articles = []
        
        for article_data in fact_dump_data:
            article_title = article_data.get('article_title', 'Unknown Article')
            article_source = article_data.get('source', '')
            facts = article_data.get('facts', [])
            
            for fact_item in facts:
                fact_list.append({
                    'fact': fact_item['text'],
                    'source': f"{article_title} (Wikipedia)",
                    'article_url': article_source,
                    'fact_id': fact_item.get('id', '')
                })
            
            source_articles.append(article_title)
        
        loaded_facts_info = {
            'total_facts': len(fact_list),
            'articles': len(source_articles),
            'source_articles': source_articles[:5],  # Show first 5 articles
            'file_name': fact_dump_path.name
        }
        
        print(f"✅ Auto-loaded {len(fact_list)} facts from {fact_dump_path.name}")
        return True
        
    except Exception as e:
        print(f"❌ Error auto-loading fact dump: {e}")
        return False

def load_custom_fact_file():
    """Load a custom fact file via file dialog"""
    global fact_list, loaded_facts_info
    
    file_path = filedialog.askopenfilename(
        title="Select Fact File",
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
    )
    
    if not file_path:
        return False
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Try to detect format and convert
        if isinstance(data, list):
            # Check if it's already in the right format
            if data and isinstance(data[0], dict) and 'fact' in data[0]:
                fact_list = data
            else:
                # Convert simple list to fact format
                fact_list = [{'fact': str(item), 'source': 'Custom File'} for item in data]
        elif isinstance(data, dict):
            # Handle fact dump format
            if 'facts' in data:
                facts = data['facts']
                fact_list = [{'fact': f['text'], 'source': data.get('article_title', 'Custom')} for f in facts]
            else:
                # Convert dict values to facts
                fact_list = [{'fact': str(value), 'source': 'Custom File'} for value in data.values()]
        else:
            raise ValueError("Unsupported file format")
        
        loaded_facts_info = {
            'total_facts': len(fact_list),
            'source_file': os.path.basename(file_path)
        }
        
        print(f"✅ Loaded {len(fact_list)} facts from custom file")
        return True
        
    except Exception as e:
        messagebox.showerror("Load Error", f"Could not load facts: {str(e)}")
        return False

def generate_prompt_from_facts(facts_batch, num_questions, category, subcategory, difficulty):
    """Generate prompt using selected facts"""
    prompt = f"You are a soccer trivia expert. Using ONLY the verified facts below, create {num_questions} multiple-choice trivia questions.\n\n"
    prompt += "VERIFIED FACTS:\n"
    
    for i, fact_item in enumerate(facts_batch, 1):
        fact_text = fact_item.get('fact', fact_item.get('text', str(fact_item)))
        source = fact_item.get('source', 'Unknown')
        prompt += f"{i}. {fact_text} (Source: {source})\n"
    
    prompt += f"\nREQUIREMENTS:\n"
    prompt += f"- Create exactly {num_questions} questions\n"
    prompt += f"- Category: {category}\n"
    prompt += f"- Subcategory: {subcategory}\n"
    prompt += f"- Difficulty: {difficulty}\n"
    prompt += f"- Each question must be based on the facts above\n"
    prompt += f"- Do not invent or hallucinate any information\n"
    prompt += f"- Provide 4 multiple choice options for each question\n"
    prompt += f"- Make incorrect options plausible but clearly wrong\n\n"
    
    prompt += "OUTPUT FORMAT (JSON):\n"
    prompt += """[
  {
    "question": "What year was MLS founded?",
    "answer": "1993",
    "options": ["1993", "1994", "1995", "1996"],
    "category": "Leagues",
    "subcategories": ["MLS"],
    "source": "Major League Soccer (Wikipedia)"
  }
]"""
    
    return prompt

def update_fact_display():
    """Update the fact display label"""
    if not fact_list:
        fact_display_label.config(text="No facts loaded")
        return
    
    info = loaded_facts_info
    display_text = f"📊 {info['total_facts']} facts loaded"
    
    if 'articles' in info:
        display_text += f" from {info['articles']} articles"
        if 'file_name' in info:
            display_text += f" ({info['file_name']})"
        if info['source_articles']:
            articles_preview = ", ".join(info['source_articles'])
            if len(info['source_articles']) == 5:
                articles_preview += "..."
            display_text += f"\n📑 Articles: {articles_preview}"
    elif 'source_file' in info:
        display_text += f" from {info['source_file']}"
    
    fact_display_label.config(text=display_text)

def update_difficulty_options():
    """Update difficulty options based on selected subcategory"""
    try:
        selected_combo = category_box.get()
        if " – " not in selected_combo:
            return
            
        _, subcategory = [s.strip() for s in selected_combo.split(" – ")]
        difficulty_options = get_difficulty_options(subcategory)
        
        difficulty_box["values"] = difficulty_options
        if difficulty_options:
            difficulty_box.current(0)
        
        # Update the info label
        if subcategory in DEFAULT_ONLY_SUBCATEGORIES:
            difficulty_info_label.config(text="ℹ️ This subcategory only generates 'default' difficulty", fg="#666666")
        else:
            difficulty_info_label.config(text="ℹ️ This subcategory generates 'easy' and 'hard' difficulty", fg="#666666")
            
    except Exception as e:
        print(f"❌ Error updating difficulty options: {e}")

# === MAIN LOGIC ===
def submit_request():
    if not client:
        messagebox.showerror("Error", "OpenAI client not initialized. Check your API key.")
        return
    
    selected_combo = category_box.get()
    difficulty = difficulty_box.get()
    
    try:
        num_total = int(count_entry.get())
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid number of questions.")
        return

    if " – " not in selected_combo:
        messagebox.showerror("Input Error", "Please select a valid category-subcategory combination.")
        return
        
    category, subcategory = [s.strip() for s in selected_combo.split(" – ")]
    
    # Check if we're using facts
    if fact_mode_var.get():
        if not fact_list:
            messagebox.showerror("No Facts", "Please load facts first or disable fact mode.")
            return
        
        if len(fact_list) < num_total:
            response = messagebox.askyesno(
                "Insufficient Facts", 
                f"You requested {num_total} questions but only have {len(fact_list)} facts.\n"
                f"Generate {len(fact_list)} questions instead?"
            )
            if not response:
                return
            num_total = len(fact_list)
    
    batch_size = 20
    num_batches = (num_total + batch_size - 1) // batch_size

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            master_questions = json.load(f)
    else:
        master_questions = []

    existing_concepts = set(q.get("concept_tag") for q in master_questions if q.get("concept_tag"))

    # Check Firestore for existing questions
    if db:
        try:
            existing_firestore_questions = db.collection(FIRESTORE_COLLECTION).stream()
            for doc in existing_firestore_questions:
                q = doc.to_dict()
                concept = extract_concept_tag(q.get("question", ""))
                if concept:
                    existing_concepts.add(concept)
        except Exception as e:
            print(f"⚠️ Warning: Could not check Firestore for duplicates: {e}")

    all_unique_questions = []
    total_cost = 0

    for i in range(num_batches):
        this_batch_size = min(batch_size, num_total - i * batch_size)
        
        if fact_mode_var.get() and fact_list:
            # Use facts from the loaded list
            start_idx = i * batch_size
            end_idx = min(start_idx + this_batch_size, len(fact_list))
            facts_batch = fact_list[start_idx:end_idx]
            
            if not facts_batch:
                print("ℹ️ No more facts available for this batch")
                break
                
            user_prompt = generate_prompt_from_facts(facts_batch, len(facts_batch), category, subcategory, difficulty)
        else:
            # Use traditional prompt (your original logic)
            user_prompt = f"Generate {this_batch_size} {difficulty} soccer trivia questions for {category} - {subcategory}."

        try:
            print(f"\n🔄 Generating batch {i+1}/{num_batches} ({this_batch_size} questions)...")
            start = time.time()
            
            thread = client.beta.threads.create()
            client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_prompt)
            run = client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=ASSISTANT_ID)
            
            end = time.time()

            if run.status != "completed":
                raise Exception(f"Batch {i+1} failed: Run did not complete (status: {run.status})")

            response = client.beta.threads.messages.list(thread_id=thread.id)
            answer = response.data[0].content[0].text.value.strip()

            if not answer:
                raise Exception("Empty response from assistant.")

            answer = clean_json_response(answer)
            
            try:
                questions = json.loads(answer)
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                print(f"Raw response: {answer[:200]}...")
                continue

            batch_unique = []

            for q in questions:
                if not all(key in q for key in ["question", "answer", "options"]):
                    print(f"⚠️ Skipping incomplete question: {q}")
                    continue
                    
                options = q["options"]
                answer = q["answer"]

                if answer not in options:
                    print(f"⚠️ Skipping question — answer not in options: {q['question'][:50]}...")
                    continue

                random.shuffle(options)
                q["options"] = options
                q["answer"] = answer

                concept = extract_concept_tag(q["question"])
                if concept not in existing_concepts:
                    q["concept_tag"] = concept
                    q["category"] = category
                    q["subcategories"] = [subcategory]
                    q["difficulty"] = difficulty
                    
                    batch_unique.append(q)
                    existing_concepts.add(concept)

                    # Upload to Firestore
                    if db:
                        try:
                            print(f"📤 Uploading to Firestore: {q['question'][:60]}...")
                            db.collection(FIRESTORE_COLLECTION).add({
                                "question": q["question"],
                                "answer": q["answer"],
                                "options": q["options"],
                                "category": category,
                                "subcategories": [subcategory],
                                "difficulty": difficulty,
                                "source": q.get("source", "Generated"),
                                "createdAt": firestore.SERVER_TIMESTAMP,
                                "updatedAt": firestore.SERVER_TIMESTAMP
                            })
                            print("✅ Upload successful")
                        except Exception as firestore_error:
                            print(f"❌ Firestore upload failed: {firestore_error}")
                else:
                    print(f"🔄 Skipping duplicate question: {q['question'][:50]}...")

            all_unique_questions.extend(batch_unique)

            # Calculate costs
            if hasattr(run, 'usage'):
                usage = run.usage
                input_cost = (usage.prompt_tokens / 1000) * INPUT_COST_PER_1K
                output_cost = (usage.completion_tokens / 1000) * OUTPUT_COST_PER_1K
                batch_cost = input_cost + output_cost
                total_cost += batch_cost

                print("=" * 50)
                print(f"📊 Batch {i+1} Results:")
                print(f"Questions generated: {len(questions)}")
                print(f"Unique questions: {len(batch_unique)}")
                print(f"Input tokens: {usage.prompt_tokens:,}")
                print(f"Output tokens: {usage.completion_tokens:,}")
                print(f"Total tokens: {usage.prompt_tokens + usage.completion_tokens:,}")
                print(f"Input cost: ${input_cost:.4f}")
                print(f"Output cost: ${output_cost:.4f}")
                print(f"Batch cost: ${batch_cost:.4f}")
                print(f"Time: {end - start:.2f} seconds")
                print("=" * 50)

            time.sleep(1)  # Rate limiting

        except Exception as e:
            error_msg = f"Batch {i+1} error: {str(e)}"
            print("❌", error_msg)
            log_error(error_msg)

    # Save results
    if all_unique_questions:
        filepath = save_questions(category, subcategory, difficulty, all_unique_questions)
        master_questions.extend(all_unique_questions)
        with open(MASTER_FILE, "w", encoding="utf-8") as f:
            json.dump(master_questions, f, indent=2, ensure_ascii=False)
        
        result_msg = f"✅ Generated {len(all_unique_questions)} unique questions\n"
        result_msg += f"💰 Total cost: ${total_cost:.4f}\n"
        result_msg += f"📁 Saved to: {os.path.basename(filepath)}"
        
        messagebox.showinfo("Success", result_msg)
    else:
        messagebox.showwarning("No Questions", "No new trivia questions were generated.")

# === GUI ===
fact_list = []
loaded_facts_info = {}

root = tk.Tk()
root.title("Universal Soccer Trivia Generator")
root.geometry("600x550")

# Category selection
tk.Label(root, text="Select Category + Subcategory:", font=("Arial", 10, "bold")).pack(pady=(10, 5))
category_box = ttk.Combobox(root, values=CATEGORY_SUBCATEGORY_OPTIONS, width=50)
category_box.pack(pady=5)
category_box.current(0)

# Difficulty selection
tk.Label(root, text="Select Difficulty:", font=("Arial", 10, "bold")).pack(pady=(10, 5))
difficulty_box = ttk.Combobox(root, width=20)
difficulty_box.pack(pady=5)

# Difficulty info label
difficulty_info_label = tk.Label(root, text="", font=("Arial", 9), fg="#666666")
difficulty_info_label.pack(pady=(2, 5))

# Question count
tk.Label(root, text="Number of Questions:", font=("Arial", 10, "bold")).pack(pady=(10, 5))
count_entry = tk.Entry(root, width=10, font=("Arial", 12))
count_entry.pack(pady=5)
count_entry.insert(0, "25")

# Fact mode section
fact_frame = tk.LabelFrame(root, text="Fact-Based Generation", font=("Arial", 10, "bold"), padx=10, pady=10)
fact_frame.pack(pady=20, padx=20, fill="x")

fact_mode_var = tk.BooleanVar()
fact_mode_checkbox = tk.Checkbutton(
    fact_frame, 
    text="Generate questions from extracted facts", 
    variable=fact_mode_var,
    font=("Arial", 10)
)
fact_mode_checkbox.pack(anchor="w")

# Fact loading buttons
button_frame = tk.Frame(fact_frame)
button_frame.pack(pady=10, fill="x")

def load_any_facts():
    if auto_detect_fact_dump():
        update_fact_display()
        fact_mode_var.set(True)  # Auto-enable fact mode
        messagebox.showinfo("Success", f"Auto-loaded {len(fact_list)} facts!")

def load_custom_facts():
    if load_custom_fact_file():
        update_fact_display()
        fact_mode_var.set(True)  # Auto-enable fact mode

tk.Button(
    button_frame, 
    text="🏆 Auto-Load Facts", 
    command=load_any_facts,
    bg="#28a745", 
    fg="white", 
    font=("Arial", 10, "bold")
).pack(side="left", padx=(0, 10))

tk.Button(
    button_frame, 
    text="📁 Load Custom Facts", 
    command=load_custom_facts,
    bg="#6c757d", 
    fg="white", 
    font=("Arial", 10)
).pack(side="left")

# Fact display
fact_display_label = tk.Label(
    fact_frame, 
    text="No facts loaded", 
    font=("Arial", 9), 
    fg="#666666",
    justify="left"
)
fact_display_label.pack(pady=(10, 0), anchor="w")

# Generate button
tk.Button(
    root, 
    text="🚀 Generate Trivia Questions", 
    command=submit_request,
    bg="#007bff", 
    fg="white", 
    font=("Arial", 12, "bold"),
    height=2
).pack(pady=30)

# Status bar
status_label = tk.Label(root, text="Ready to generate questions", relief="sunken", anchor="w")
status_label.pack(side="bottom", fill="x")

# Bind the category change event after widgets are created
category_box.bind("<<ComboboxSelected>>", lambda e: update_difficulty_options())

# Initialize difficulty options
update_difficulty_options()

# Try to auto-load any fact dump on startup
if auto_detect_fact_dump():
    update_fact_display()
    print("✅ Auto-loaded fact dump on startup")

root.mainloop()