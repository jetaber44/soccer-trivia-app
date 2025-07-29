import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Check for required packages
try:
    from openai import OpenAI
except ImportError:
    messagebox.showerror("Missing Package", "Please install openai: pip install openai")
    exit()

try:
    from google.cloud import firestore
    from google.oauth2 import service_account
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    print("Warning: Google Cloud Firestore not available. Install with: pip install google-cloud-firestore")

# === CONFIGURATION ===
API_KEY_PATH = "C:/The_GPK/Entry.txt"
SERVICE_ACCOUNT_PATH = "C:/Users/aq_pu/Desktop/soccer-trivia-app/firestore-import/serviceAccount.json"

MODEL = "gpt-4"  # Updated to current model
COST_PER_1K_INPUT_TOKENS = 0.03   # GPT-4 pricing as of 2024
COST_PER_1K_OUTPUT_TOKENS = 0.06

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

Your job is to create high-quality, accurate multiple-choice trivia questions based on your soccer knowledge.

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

Guidelines:
- Questions should be factual and verifiable
- Include the correct answer among the 4 options
- Make incorrect options plausible but clearly wrong
- Vary difficulty appropriately
- Only use valid categories and subcategories provided
- If unsure of an answer, skip that question

Focus on factual correctness above all else.
"""

VERIFICATION_PROMPT = """
You are verifying a soccer trivia question and answer for factual accuracy.

Analyze the question and answer provided. Consider:
- Is the factual claim accurate?
- Is the answer among the options?
- Are the options reasonable?

ONLY output "PASS" if the answer is factually accurate and verifiable. 
Otherwise, output "FAIL" followed by a brief explanation of what's wrong.
"""

class QuizlazaGenerator:
    def __init__(self):
        self.client = None
        self.db = None
        self.setup_openai_client()
        self.setup_firestore_client()
        self.setup_ui()
        
    def setup_openai_client(self) -> bool:
        """Initialize OpenAI client with API key from hardcoded path"""
        try:
            if not os.path.exists(API_KEY_PATH):
                messagebox.showerror("File Error", f"API key file not found: {API_KEY_PATH}")
                return False
                
            with open(API_KEY_PATH, 'r', encoding='utf-8') as f:
                api_key = f.read().strip()
                
            if not api_key:
                messagebox.showerror("File Error", "API key file is empty")
                return False
                
            self.client = OpenAI(api_key=api_key)
            # Test the connection
            self.client.models.list()
            return True
        except Exception as e:
            messagebox.showerror("OpenAI Error", f"Failed to initialize OpenAI client: {str(e)}")
            return False
            
    def setup_firestore_client(self) -> bool:
        """Initialize Firestore client with hardcoded path"""
        if not FIRESTORE_AVAILABLE:
            print("Warning: Google Cloud Firestore not installed. Questions will be saved locally only.")
            return False
            
        try:
            if not os.path.exists(SERVICE_ACCOUNT_PATH):
                print(f"Warning: Service account file not found: {SERVICE_ACCOUNT_PATH}")
                return False
                
            credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH)
            self.db = firestore.Client(credentials=credentials)
            return True
        except Exception as e:
            print(f"Warning: Failed to initialize Firestore: {str(e)}")
            return False

    def generate_questions(self, category: str, subcategory: str, count: int) -> Tuple[List[Dict], Dict, str]:
        """Generate questions using OpenAI API"""
        if not self.client:
            raise Exception("OpenAI client not initialized")
            
        prompt = f"Generate {count} soccer trivia questions for category '{category}' and subcategory '{subcategory}'. Return only valid JSON array."
        
        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            questions = json.loads(content)
            if not isinstance(questions, list):
                raise ValueError("Response is not a JSON array")
                
            return questions, usage, content
            
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise Exception(f"API call failed: {str(e)}")

    def verify_question(self, question_obj: Dict) -> Tuple[bool, str]:
        """Verify a single question for accuracy"""
        if not self.client:
            return False, "OpenAI client not initialized"
            
        q_text = question_obj.get("question", "")
        a_text = question_obj.get("answer", "")
        options = question_obj.get("options", [])
        
        verify_prompt = f"""Question: {q_text}
Answer: {a_text}
Options: {', '.join(options)}

Is this question factually accurate and is the answer correct?"""

        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": VERIFICATION_PROMPT},
                    {"role": "user", "content": verify_prompt}
                ],
                temperature=0
            )
            
            content = response.choices[0].message.content.strip()
            return content.startswith("PASS"), content
            
        except Exception as e:
            return False, f"Verification failed: {str(e)}"

    def upload_to_firestore(self, questions: List[Dict]) -> bool:
        """Upload questions to Firestore"""
        if not self.db:
            return False
            
        try:
            collection_ref = self.db.collection("triviaQuestions")
            batch = self.db.batch()
            
            for q in questions:
                doc_ref = collection_ref.document()
                doc_data = {
                    "question": q["question"],
                    "answer": q["answer"],
                    "options": q["options"],
                    "category": q["category"],
                    "subcategories": q["subcategories"],
                    "difficulty": "default",
                    "source": q.get("source", "Generated"),
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }
                batch.set(doc_ref, doc_data)
            
            batch.commit()
            return True
            
        except Exception as e:
            messagebox.showerror("Upload Error", f"Failed to upload to Firestore: {str(e)}")
            return False

    def save_questions_locally(self, questions: List[Dict], filename: str = None) -> bool:
        """Save questions to local JSON file"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"quizlazo_questions_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(questions, f, indent=2, ensure_ascii=False)
            return True
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save locally: {str(e)}")
            return False

    def browse_api_key_file(self):
        """Browse for API key file - disabled since using hardcoded path"""
        messagebox.showinfo("Hardcoded Path", f"Using hardcoded API key path: {API_KEY_PATH}")

    def browse_service_account_file(self):
        """Browse for service account JSON file - disabled since using hardcoded path"""
        messagebox.showinfo("Hardcoded Path", f"Using hardcoded service account path: {SERVICE_ACCOUNT_PATH}")

    def load_api_key_from_file(self, filepath: str) -> Optional[str]:
        """Load API key from file - not used with hardcoded paths"""
        pass

    def run_generation(self):
        """Main generation process - runs in separate thread"""
        def generation_thread():
            try:
                # Validate inputs
                category = self.category_var.get()
                subcategory = self.subcategory_var.get()
                total_needed = int(self.count_var.get())
                
                if not category or not subcategory:
                    messagebox.showerror("Missing Fields", "Please select both category and subcategory.")
                    return

                # Check if clients are initialized
                if not self.client:
                    messagebox.showerror("OpenAI Error", "OpenAI client not initialized. Check your API key file.")
                    return

                # Clear output and start generation
                self.output_text.delete("1.0", tk.END)
                self.log_output(f"🎯 Target: {total_needed} verified questions for '{subcategory}'...")
                self.generate_button.config(state="disabled")

                final_questions = []
                total_input_tokens = 0
                total_output_tokens = 0
                
                max_attempts = total_needed * 3  # Prevent infinite loops
                attempts = 0

                while len(final_questions) < total_needed and attempts < max_attempts:
                    needed = total_needed - len(final_questions)
                    batch_size = min(5, needed)

                    self.log_output(f"\n🌀 Generating batch of {batch_size}...")
                    
                    try:
                        batch, usage, raw = self.generate_questions(category, subcategory, batch_size)
                        total_input_tokens += usage["prompt_tokens"]
                        total_output_tokens += usage["completion_tokens"]
                        
                        if not batch:
                            self.log_output("⚠️ No questions generated in this batch")
                            attempts += batch_size
                            continue

                        for q in batch:
                            if len(final_questions) >= total_needed:
                                break
                                
                            # Validate question structure
                            required_fields = ["question", "answer", "options", "category"]
                            if not all(field in q for field in required_fields):
                                self.log_output(f"❌ SKIP: Invalid question structure")
                                attempts += 1
                                continue
                            
                            # Verify question
                            passed, feedback = self.verify_question(q)
                            if passed:
                                final_questions.append(q)
                                self.log_output(f"✅ PASS: {q['question'][:60]}...")
                            else:
                                self.log_output(f"❌ FAIL: {q['question'][:60]}... — {feedback}")
                            
                            attempts += 1
                            
                    except Exception as e:
                        self.log_output(f"❌ Error generating batch: {str(e)}")
                        attempts += batch_size

                # Save results
                if final_questions:
                    # Save locally
                    if self.save_questions_locally(final_questions):
                        self.log_output(f"\n💾 Saved {len(final_questions)} questions locally")
                    
                    # Upload to Firestore if available
                    if self.db and self.upload_to_firestore(final_questions):
                        self.log_output(f"☁️ Uploaded {len(final_questions)} questions to Firestore")

                    # Calculate costs
                    input_cost = total_input_tokens * COST_PER_1K_INPUT_TOKENS / 1000
                    output_cost = total_output_tokens * COST_PER_1K_OUTPUT_TOKENS / 1000
                    total_cost = input_cost + output_cost
                    
                    self.log_output(f"\n📊 Generation Complete!")
                    self.log_output(f"✅ Successfully generated: {len(final_questions)} questions")
                    self.log_output(f"📈 Input tokens: {total_input_tokens}")
                    self.log_output(f"📈 Output tokens: {total_output_tokens}")
                    self.log_output(f"💰 Total cost: ${total_cost:.4f}")
                else:
                    self.log_output(f"\n❌ No questions were successfully generated")

            except Exception as e:
                self.log_output(f"\n❌ Generation failed: {str(e)}")
            finally:
                self.generate_button.config(state="normal")

        # Run in separate thread to prevent UI freezing
        thread = threading.Thread(target=generation_thread)
        thread.daemon = True
        thread.start()

    def log_output(self, message: str):
        """Thread-safe logging to output text widget"""
        def update_ui():
            self.output_text.insert(tk.END, message + "\n")
            self.output_text.see(tk.END)
            self.root.update_idletasks()
        
        self.root.after(0, update_ui)

    def update_subcategories(self, *args):
        """Update subcategory dropdown based on selected category"""
        selected = self.category_var.get()
        subcats = CATEGORY_STRUCTURE.get(selected, [])
        self.subcategory_dropdown["values"] = subcats
        if subcats:
            self.subcategory_var.set(subcats[0])
        else:
            self.subcategory_var.set("")

    def setup_ui(self):
        """Setup the user interface"""
        self.root = tk.Tk()
        self.root.title("Quizlazo Question Generator v2.0")
        self.root.geometry("700x650")
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Display hardcoded paths
        ttk.Label(config_frame, text=f"API Key Path: {API_KEY_PATH}").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Label(config_frame, text=f"Service Account Path: {SERVICE_ACCOUNT_PATH}").grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        # Generation parameters
        params_frame = ttk.LabelFrame(main_frame, text="Generation Parameters", padding="10")
        params_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Category
        ttk.Label(params_frame, text="Category:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.category_var = tk.StringVar()
        self.category_dropdown = ttk.Combobox(params_frame, textvariable=self.category_var, state="readonly", width=40)
        self.category_dropdown["values"] = list(CATEGORY_STRUCTURE.keys())
        self.category_dropdown.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.category_dropdown.bind("<<ComboboxSelected>>", self.update_subcategories)
        
        # Subcategory
        ttk.Label(params_frame, text="Subcategory:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.subcategory_var = tk.StringVar()
        self.subcategory_dropdown = ttk.Combobox(params_frame, textvariable=self.subcategory_var, state="readonly", width=40)
        self.subcategory_dropdown.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Count
        ttk.Label(params_frame, text="Number of Questions:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.count_var = tk.StringVar(value="10")
        count_dropdown = ttk.Combobox(params_frame, textvariable=self.count_var, state="readonly", width=20)
        count_dropdown["values"] = [str(i) for i in range(5, 55, 5)]
        count_dropdown.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
        
        # Generate button
        self.generate_button = ttk.Button(main_frame, text="Generate Questions", command=self.run_generation)
        self.generate_button.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Output text
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.output_text = tk.Text(output_frame, height=15, wrap="word")
        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scrollbar.set)
        
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # Changed from 3 to 2
        config_frame.columnconfigure(0, weight=1)
        params_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = QuizlazaGenerator()
    app.run()